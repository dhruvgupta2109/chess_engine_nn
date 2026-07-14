"""FastAPI application exposing the local authoritative chess game service."""

from __future__ import annotations

import asyncio
import hashlib
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from chess_engine_nn.evaluator import PositionEvaluator, load_evaluator
from chess_engine_nn.web_api.game_service import GameActionError, GameService, HumanSide


class NewGameRequest(BaseModel):
    human_side: HumanSide = "white"
    think_time_ms: int = 1000


class MoveRequest(BaseModel):
    move: str


class EventBroker:
    """Bridge search-thread events into per-client asyncio queues."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._clients: set[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = set()

    def publish(self, event: dict[str, Any]) -> None:
        with self._lock:
            clients = tuple(self._clients)
        for loop, queue in clients:
            loop.call_soon_threadsafe(self._put_latest, queue, event)

    async def subscribe(self) -> AsyncIterator[asyncio.Queue]:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue(maxsize=32)
        client = (loop, queue)
        with self._lock:
            self._clients.add(client)
        try:
            yield queue
        finally:
            with self._lock:
                self._clients.discard(client)

    @staticmethod
    def _put_latest(queue: asyncio.Queue, event: dict[str, Any]) -> None:
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        queue.put_nowait(event)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_app(
    *,
    model_path: Path | None = None,
    evaluator: PositionEvaluator | None = None,
    service: GameService | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    """Create an app with a validated model or an explicitly injected test evaluator."""
    broker = EventBroker()
    if service is None:
        if evaluator is None:
            if model_path is None:
                raise ValueError("model_path or evaluator is required")
            evaluator = load_evaluator(model_path)
        identity: dict[str, Any] = {"ready": True, "name": "injected-evaluator"}
        if model_path is not None:
            identity = {
                "ready": True,
                "name": model_path.name,
                "path": str(model_path),
                "sha256": _file_sha256(model_path),
            }
        service = GameService(evaluator, event_sink=broker.publish, model_identity=identity)
    else:
        service.set_event_sink(broker.publish)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        service.close()

    app = FastAPI(title="Chess Engine NN Web API", version="1", lifespan=lifespan)
    app.state.game_service = service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )

    def run_action(action):
        try:
            return action()
        except GameActionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/api/v1/status")
    def status() -> dict[str, Any]:
        return {"ok": True, "api_version": 1, "model": service.model_identity}

    @app.get("/api/v1/games/current")
    def current_game() -> dict[str, Any]:
        return service.state()

    @app.post("/api/v1/games")
    def new_game(request: NewGameRequest) -> dict[str, Any]:
        return run_action(lambda: service.new_game(request.human_side, request.think_time_ms))

    @app.post("/api/v1/games/current/moves")
    def move(request: MoveRequest) -> dict[str, Any]:
        return run_action(lambda: service.submit_move(request.move))

    @app.post("/api/v1/games/current/undo")
    def undo() -> dict[str, Any]:
        return run_action(service.undo_turn)

    @app.post("/api/v1/games/current/resign")
    def resign() -> dict[str, Any]:
        return run_action(service.resign)

    @app.delete("/api/v1/games/current")
    def discard() -> dict[str, Any]:
        return service.discard()

    @app.websocket("/api/v1/events")
    async def events(websocket: WebSocket) -> None:
        await websocket.accept()
        subscription = broker.subscribe()
        queue = await anext(subscription)
        try:
            await websocket.send_json({"type": "game.state", "payload": service.state()})
            while True:
                await websocket.send_json(await queue.get())
        except WebSocketDisconnect:
            pass
        finally:
            await subscription.aclose()

    resolved_static_dir = static_dir or Path(__file__).with_name("static")
    if (resolved_static_dir / "index.html").is_file():
        app.mount("/", StaticFiles(directory=resolved_static_dir, html=True), name="website")

    return app
