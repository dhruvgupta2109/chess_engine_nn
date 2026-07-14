"""Authoritative game lifecycle and cancellable neural search for the web UI."""

from __future__ import annotations

import random
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

import chess

from chess_engine_nn.evaluator import PositionEvaluator
from chess_engine_nn.search import SearchEngine, SearchResult
from chess_engine_nn.time_control import SearchLimits

HumanSide = Literal["white", "black", "random"]
EventSink = Callable[[dict[str, Any]], None]
SearchFactory = Callable[[], SearchEngine]

_MATERIAL_POINTS = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
}
_CAPTURE_ORDER = {
    chess.PAWN: 0,
    chess.BISHOP: 1,
    chess.KNIGHT: 2,
    chess.ROOK: 3,
    chess.QUEEN: 4,
}


class GameActionError(ValueError):
    """Raised when a requested web-game action is invalid for the current state."""


@dataclass(frozen=True)
class WebSearchConfig:
    hash_mb: int = 64
    max_quiescence_depth: int = 8
    aspiration_window_cp: int = 50


class GameService:
    """Own one local game and keep all rule decisions on the Python side."""

    def __init__(
        self,
        evaluator: PositionEvaluator,
        *,
        seed: int = 20260713,
        search_config: WebSearchConfig | None = None,
        event_sink: EventSink | None = None,
        search_factory: SearchFactory | None = None,
        model_identity: dict[str, Any] | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._rng = random.Random(seed)
        self._event_sink = event_sink
        resolved_search_config = search_config or WebSearchConfig()
        self._search_factory = search_factory or (
            lambda: SearchEngine(
                evaluator,
                hash_mb=resolved_search_config.hash_mb,
                max_quiescence_depth=resolved_search_config.max_quiescence_depth,
                aspiration_window_cp=resolved_search_config.aspiration_window_cp,
            )
        )
        self.model_identity = model_identity or {"ready": True, "name": "injected-evaluator"}
        self._board = chess.Board()
        self._human_color = chess.WHITE
        self._think_time_ms = 1000
        self._generation = 0
        self._game_number = 0
        self._worker: threading.Thread | None = None
        self._stop_event: threading.Event | None = None
        self._search_info: dict[str, Any] | None = None
        self._resigned_result: str | None = None
        self._resigned_by: str | None = None
        self._started = False

    def set_event_sink(self, sink: EventSink | None) -> None:
        """Replace the process-local event sink used by WebSocket clients."""
        with self._lock:
            self._event_sink = sink

    def new_game(self, human_side: HumanSide, think_time_ms: int) -> dict[str, Any]:
        """Cancel any search and create a fresh standard-position game."""
        if human_side not in ("white", "black", "random"):
            raise GameActionError("human_side must be white, black, or random")
        if think_time_ms not in (250, 1000, 3000):
            raise GameActionError("think_time_ms must be one of 250, 1000, or 3000")
        self._invalidate_search()
        with self._lock:
            selected = self._rng.choice((chess.WHITE, chess.BLACK)) if human_side == "random" else (
                human_side == "white"
            )
            self._board = chess.Board()
            self._human_color = selected
            self._think_time_ms = think_time_ms
            self._game_number += 1
            self._search_info = None
            self._resigned_result = None
            self._resigned_by = None
            self._started = True
            state = self._state_locked()
        self._emit("game.state", state)
        if selected == chess.BLACK:
            self._start_engine_search()
        return self.state()

    def state(self) -> dict[str, Any]:
        """Return a serializable snapshot of the authoritative position."""
        with self._lock:
            return self._state_locked()

    def submit_move(self, move_uci: str) -> dict[str, Any]:
        """Validate and apply one human move, then start the engine reply."""
        with self._lock:
            self._require_started()
            if self._game_result_locked() is not None:
                raise GameActionError("the game is already over")
            if self._worker is not None or self._board.turn != self._human_color:
                raise GameActionError("it is not the human player's turn")
            try:
                move = chess.Move.from_uci(move_uci)
            except ValueError as error:
                raise GameActionError(f"invalid UCI move: {move_uci}") from error
            if move not in self._board.legal_moves:
                raise GameActionError(f"illegal move: {move_uci}")
            self._board.push(move)
            self._search_info = None
            state = self._state_locked()
            game_over = self._game_result_locked() is not None
        self._emit("game.state", state)
        if game_over:
            self._emit("game.over", state)
        else:
            self._start_engine_search()
        return self.state()

    def undo_turn(self) -> dict[str, Any]:
        """Undo enough plies to return control to the human."""
        self._invalidate_search()
        with self._lock:
            self._require_started()
            if not self._board.move_stack:
                raise GameActionError("there are no moves to undo")
            if self._human_color == chess.BLACK and len(self._board.move_stack) == 1:
                raise GameActionError("make a move before undoing a turn")
            self._resigned_result = None
            self._resigned_by = None
            self._search_info = None
            self._board.pop()
            if self._board.turn != self._human_color and self._board.move_stack:
                self._board.pop()
            state = self._state_locked()
        self._emit("game.state", state)
        return state

    def resign(self) -> dict[str, Any]:
        """End the game as a resignation by the human player."""
        self._invalidate_search()
        with self._lock:
            self._require_started()
            if self._game_result_locked() is not None:
                raise GameActionError("the game is already over")
            self._resigned_result = "0-1" if self._human_color == chess.WHITE else "1-0"
            self._resigned_by = "white" if self._human_color == chess.WHITE else "black"
            state = self._state_locked()
        self._emit("game.over", state)
        return state

    def discard(self) -> dict[str, Any]:
        """Cancel search and clear the current game without creating another."""
        self._invalidate_search()
        with self._lock:
            self._board = chess.Board()
            self._search_info = None
            self._resigned_result = None
            self._resigned_by = None
            self._started = False
            state = self._state_locked()
        self._emit("game.state", state)
        return state

    def close(self) -> None:
        """Cancel and join the current search worker."""
        self._invalidate_search()

    def _start_engine_search(self) -> None:
        with self._lock:
            if (
                not self._started
                or self._game_result_locked() is not None
                or self._board.turn == self._human_color
                or self._worker is not None
            ):
                return
            generation = self._generation
            board = self._board.copy(stack=True)
            stop_event = threading.Event()
            self._stop_event = stop_event
            worker = threading.Thread(
                target=self._run_search,
                args=(generation, board, stop_event),
                name=f"web-search-{generation}",
                daemon=True,
            )
            self._worker = worker
            state = self._state_locked()
        self._emit("search.started", state)
        worker.start()

    def _run_search(
        self,
        generation: int,
        board: chess.Board,
        stop_event: threading.Event,
    ) -> None:
        engine = self._search_factory()

        def observe(result: SearchResult) -> None:
            info = self._search_result_dict(result)
            with self._lock:
                if generation != self._generation or stop_event.is_set():
                    return
                self._search_info = info
                payload = self._state_locked()
            self._emit("search.iteration", payload)

        try:
            result = engine.search(
                board,
                SearchLimits(move_time_ms=self._think_time_ms),
                observer=observe,
                stop_event=stop_event,
            )
            with self._lock:
                if generation != self._generation or stop_event.is_set():
                    return
                move = result.best_move
                if move is None or move not in self._board.legal_moves:
                    raise RuntimeError("search returned no legal move for a non-terminal game")
                self._board.push(move)
                self._search_info = self._search_result_dict(result)
                self._worker = None
                self._stop_event = None
                state = self._state_locked()
                game_over = self._game_result_locked() is not None
            self._emit("search.completed", state)
            if game_over:
                self._emit("game.over", state)
        except Exception as error:
            with self._lock:
                if generation != self._generation:
                    return
                self._worker = None
                self._stop_event = None
                state = self._state_locked()
            self._emit("error", {"message": str(error), "state": state})

    def _invalidate_search(self) -> None:
        with self._lock:
            self._generation += 1
            worker = self._worker
            stop_event = self._stop_event
            self._worker = None
            self._stop_event = None
        if stop_event is not None:
            stop_event.set()
        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=5)
            if worker.is_alive():
                raise RuntimeError("search worker did not stop within five seconds")

    def _state_locked(self) -> dict[str, Any]:
        result = self._game_result_locked()
        captures, material_advantage = self._capture_summary_locked()
        if not self._started:
            phase = "not_started"
        elif result is not None:
            phase = "game_over"
        elif self._worker is not None or self._board.turn != self._human_color:
            phase = "engine_thinking"
        else:
            phase = "human_turn"
        check_square = self._board.king(self._board.turn) if self._board.is_check() else None
        return {
            "game_number": self._game_number,
            "generation": self._generation,
            "started": self._started,
            "phase": phase,
            "fen": self._board.fen(),
            "turn": "white" if self._board.turn == chess.WHITE else "black",
            "human_color": "white" if self._human_color == chess.WHITE else "black",
            "engine_color": "black" if self._human_color == chess.WHITE else "white",
            "think_time_ms": self._think_time_ms,
            "legal_moves": [move.uci() for move in self._board.legal_moves],
            "moves": self._san_history_locked(),
            "captures": captures,
            "material_advantage": material_advantage,
            "last_move": self._board.peek().uci() if self._board.move_stack else None,
            "check_square": chess.square_name(check_square) if check_square is not None else None,
            "result": result[0] if result else None,
            "termination": result[1] if result else None,
            "search": self._search_info,
        }

    def _san_history_locked(self) -> list[str]:
        replay = self._board.root()
        san_moves = []
        for move in self._board.move_stack:
            san_moves.append(replay.san(move))
            replay.push(move)
        return san_moves

    def _capture_summary_locked(self) -> tuple[dict[str, list[str]], dict[str, int]]:
        captures: dict[str, list[str]] = {"white": [], "black": []}
        replay = self._board.root()
        for move in self._board.move_stack:
            captured = replay.piece_at(move.to_square)
            if replay.is_en_passant(move):
                captured_square = (
                    move.to_square - 8
                    if replay.turn == chess.WHITE
                    else move.to_square + 8
                )
                captured = replay.piece_at(captured_square)
            if captured is not None:
                capturer = "white" if replay.turn == chess.WHITE else "black"
                captures[capturer].append(captured.symbol())
            replay.push(move)

        for pieces in captures.values():
            pieces.sort(
                key=lambda symbol: _CAPTURE_ORDER[chess.Piece.from_symbol(symbol).piece_type]
            )

        material = {
            "white": sum(
                len(self._board.pieces(piece_type, chess.WHITE)) * points
                for piece_type, points in _MATERIAL_POINTS.items()
            ),
            "black": sum(
                len(self._board.pieces(piece_type, chess.BLACK)) * points
                for piece_type, points in _MATERIAL_POINTS.items()
            ),
        }
        difference = material["white"] - material["black"]
        advantage = {"white": max(0, difference), "black": max(0, -difference)}
        return captures, advantage

    def _game_result_locked(self) -> tuple[str, str] | None:
        if self._resigned_result is not None:
            return self._resigned_result, f"{self._resigned_by}_resigned"
        outcome = self._board.outcome(claim_draw=True)
        if outcome is None:
            return None
        return outcome.result(), outcome.termination.name.lower()

    def _require_started(self) -> None:
        if not self._started:
            raise GameActionError("start a game first")

    @staticmethod
    def _search_result_dict(result: SearchResult) -> dict[str, Any]:
        return {
            "depth": result.depth,
            "seldepth": result.seldepth,
            "score_cp": result.score_cp,
            "mate_in": result.mate_in,
            "nodes": result.nodes,
            "nps": result.nps,
            "elapsed_ms": result.elapsed_ms,
            "pv": [move.uci() for move in result.principal_variation],
            "completed": result.completed,
        }

    def _emit(self, event: str, payload: dict[str, Any]) -> None:
        with self._lock:
            sink = self._event_sink
        if sink is not None:
            sink({"type": event, "payload": payload})
