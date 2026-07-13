"""Asynchronous Universal Chess Interface adapter for the neural engine."""

from __future__ import annotations

import argparse
import sys
import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

import chess

from chess_engine_nn import __version__
from chess_engine_nn.errors import UCIProtocolError
from chess_engine_nn.evaluator import PositionEvaluator, load_evaluator
from chess_engine_nn.reproducibility import seed_everything
from chess_engine_nn.search import SearchEngine, SearchResult
from chess_engine_nn.time_control import SearchLimits

ENGINE_NAME = "Chess Engine NN"
ENGINE_AUTHOR = "Deepak Gupta"
MIN_HASH_MB = 1
MAX_HASH_MB = 1_048_576
MAX_SEED = 2_147_483_647

EvaluatorLoader = Callable[[Path], PositionEvaluator]


class UCIEngine:
    """Own UCI state and one cooperative background search worker.

    Supplying ``evaluator`` is an explicit test/development seam. The production
    module entry point starts unready unless ``--model`` loads successfully.
    """

    def __init__(
        self,
        *,
        evaluator: PositionEvaluator | None = None,
        model_path: Path | None = None,
        hash_mb: int = 64,
        threads: int = 1,
        seed: int = 20260713,
        max_quiescence_depth: int = 8,
        aspiration_window_cp: int = 50,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
        evaluator_loader: EvaluatorLoader = load_evaluator,
    ) -> None:
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr
        self._evaluator_loader = evaluator_loader
        self._write_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._stop_event: threading.Event | None = None
        self._search_id = 0
        self._quitting = False

        self.hash_mb = self._validate_hash(hash_mb)
        self.threads = self._validate_threads(threads)
        self.seed = self._validate_seed(seed)
        self.max_quiescence_depth = max_quiescence_depth
        self.aspiration_window_cp = aspiration_window_cp
        self.model_path: Path | None = None
        self.evaluator = evaluator
        self.engine = self._new_search_engine(evaluator) if evaluator is not None else None
        self.board = chess.Board()
        seed_everything(self.seed)

        if model_path is not None:
            self._replace_model(model_path)

    @property
    def ready(self) -> bool:
        """Whether a validated evaluator is available for search."""
        return self.engine is not None

    @property
    def searching(self) -> bool:
        """Whether the single search worker is still active."""
        with self._state_lock:
            return self._worker is not None and self._worker.is_alive()

    def run(self) -> int:
        """Read commands until ``quit`` or EOF, keeping search asynchronous."""
        try:
            for line in self.stdin:
                if not self.handle_command(line):
                    break
        finally:
            self.shutdown()
        return 0

    def handle_command(self, line: str) -> bool:
        """Handle one command; malformed input is diagnosed only on stderr."""
        command = line.strip()
        if not command:
            return True
        name, _, arguments = command.partition(" ")
        try:
            if name == "uci":
                self._handle_uci()
            elif name == "isready":
                self._handle_isready()
            elif name == "ucinewgame":
                self._handle_new_game()
            elif name == "position":
                self._handle_position(arguments)
            elif name == "go":
                self._handle_go(arguments)
            elif name == "stop":
                self.stop()
            elif name == "setoption":
                self._handle_setoption(arguments)
            elif name == "quit":
                self.shutdown()
                return False
            else:
                raise UCIProtocolError(f"unknown command: {name}")
        except (UCIProtocolError, ValueError, OSError) as error:
            self._diagnostic(str(error))
        return True

    def wait_for_search(self, timeout: float | None = None) -> bool:
        """Wait for the current worker, returning false if it remains alive."""
        with self._state_lock:
            worker = self._worker
        if worker is None or worker is threading.current_thread():
            return True
        worker.join(timeout)
        return not worker.is_alive()

    def stop(self) -> None:
        """Request cooperative cancellation without blocking command input."""
        with self._state_lock:
            stop_event = self._stop_event
        if stop_event is not None:
            stop_event.set()

    def shutdown(self) -> None:
        """Cancel and join the worker so no thread outlives the adapter."""
        self._quitting = True
        self.stop()
        self.wait_for_search()

    def _handle_uci(self) -> None:
        self._send(f"id name {ENGINE_NAME} {__version__}")
        self._send(f"id author {ENGINE_AUTHOR}")
        default_model = f" default {self.model_path}" if self.model_path else " default"
        self._send(f"option name ModelPath type string{default_model}")
        self._send(
            f"option name Hash type spin default {self.hash_mb} min {MIN_HASH_MB} max {MAX_HASH_MB}"
        )
        self._send("option name Threads type spin default 1 min 1 max 1")
        self._send(f"option name Seed type spin default {self.seed} min 0 max {MAX_SEED}")
        self._send("uciok")

    def _handle_isready(self) -> None:
        if self.ready:
            self._send("readyok")
        else:
            self._diagnostic("engine is not ready: set ModelPath to a validated inference model")

    def _handle_new_game(self) -> None:
        self._stop_and_wait()
        if self.engine is not None:
            self.engine.table.clear()
            self.engine.killers.clear()
            self.engine.history.clear()
            self.engine.generation = 0

    def _handle_position(self, arguments: str) -> None:
        tokens = arguments.split()
        if not tokens:
            raise UCIProtocolError("position requires 'startpos' or 'fen'")
        index = 0
        if tokens[0] == "startpos":
            candidate = chess.Board()
            index = 1
        elif tokens[0] == "fen":
            if len(tokens) < 7:
                raise UCIProtocolError("position fen requires all six FEN fields")
            try:
                candidate = chess.Board(" ".join(tokens[1:7]))
            except ValueError as error:
                raise UCIProtocolError(f"invalid position FEN: {error}") from error
            index = 7
        else:
            raise UCIProtocolError("position requires 'startpos' or 'fen'")

        if index < len(tokens):
            if tokens[index] != "moves":
                raise UCIProtocolError(f"unexpected position token: {tokens[index]}")
            for move_text in tokens[index + 1 :]:
                try:
                    candidate.push_uci(move_text)
                except ValueError as error:
                    message = f"invalid or illegal position move {move_text}: {error}"
                    raise UCIProtocolError(message) from error
        self._stop_and_wait()
        self.board = candidate

    def _handle_go(self, arguments: str) -> None:
        if self.engine is None:
            raise UCIProtocolError("cannot search before a validated ModelPath is loaded")
        limits = self._parse_go(arguments.split())
        self._stop_and_wait()
        board = self.board.copy(stack=True)
        stop_event = threading.Event()
        with self._state_lock:
            self._search_id += 1
            search_id = self._search_id
            self._stop_event = stop_event
            worker = threading.Thread(
                target=self._search_worker,
                args=(search_id, board, limits, stop_event),
                name="chess-engine-nn-search",
                daemon=False,
            )
            self._worker = worker
        worker.start()

    def _search_worker(
        self,
        search_id: int,
        board: chess.Board,
        limits: SearchLimits,
        stop_event: threading.Event,
    ) -> None:
        engine = self.engine
        if engine is None:
            return
        try:
            result = engine.search(
                board,
                limits,
                observer=lambda report: self._send_info(search_id, report),
                stop_event=stop_event,
            )
            if self._is_current_search(search_id):
                if result.best_move is not None:
                    move = result.best_move.uci()
                else:
                    legal = sorted(board.legal_moves, key=lambda candidate: candidate.uci())
                    move = legal[0].uci() if legal else "0000"
                self._send(f"bestmove {move}")
        except Exception as error:  # Keep unexpected failures away from protocol stdout.
            self._diagnostic(f"search failed: {type(error).__name__}: {error}")
            if self._is_current_search(search_id):
                legal = sorted(board.legal_moves, key=lambda move: move.uci())
                if legal:
                    self._send(f"bestmove {legal[0].uci()}")
                else:
                    self._send("bestmove 0000")
        finally:
            with self._state_lock:
                if self._search_id == search_id:
                    self._stop_event = None

    def _send_info(self, search_id: int, result: SearchResult) -> None:
        if not self._is_current_search(search_id):
            return
        if result.mate_in is not None:
            score = f"score mate {result.mate_in}"
        else:
            score = f"score cp {result.score_cp or 0}"
        pv = " ".join(move.uci() for move in result.principal_variation)
        message = (
            f"info depth {result.depth} seldepth {result.seldepth} {score} "
            f"nodes {result.nodes} nps {result.nps} time {result.elapsed_ms}"
        )
        if pv:
            message += f" pv {pv}"
        self._send(message)

    def _handle_setoption(self, arguments: str) -> None:
        tokens = arguments.split()
        if not tokens or tokens[0] != "name":
            raise UCIProtocolError("setoption requires 'name <option> [value <value>]'")
        try:
            value_index = tokens.index("value", 1)
        except ValueError:
            name = " ".join(tokens[1:])
            value = ""
        else:
            name = " ".join(tokens[1:value_index])
            value = " ".join(tokens[value_index + 1 :])
        if not name:
            raise UCIProtocolError("setoption option name cannot be empty")
        normalized = name.casefold()
        if normalized == "modelpath":
            if not value:
                raise UCIProtocolError("ModelPath requires a non-empty value")
            self._replace_model(Path(value).expanduser())
        elif normalized == "hash":
            new_hash = self._validate_hash(self._parse_integer("Hash", value))
            self._stop_and_wait()
            self.hash_mb = new_hash
            if self.evaluator is not None:
                self.engine = self._new_search_engine(self.evaluator)
        elif normalized == "threads":
            self.threads = self._validate_threads(self._parse_integer("Threads", value))
        elif normalized == "seed":
            new_seed = self._validate_seed(self._parse_integer("Seed", value))
            self._stop_and_wait()
            seed_everything(new_seed)
            self.seed = new_seed
            if self.engine is not None:
                self.engine.table.clear()
                self.engine.killers.clear()
                self.engine.history.clear()
        else:
            raise UCIProtocolError(f"unknown option: {name}")

    def _replace_model(self, path: Path) -> None:
        try:
            evaluator = self._evaluator_loader(path)
        except Exception as error:
            raise UCIProtocolError(f"failed to load ModelPath {path}: {error}") from error
        new_engine = self._new_search_engine(evaluator)
        self._stop_and_wait()
        self.evaluator = evaluator
        self.engine = new_engine
        self.model_path = path

    def _new_search_engine(self, evaluator: PositionEvaluator) -> SearchEngine:
        return SearchEngine(
            evaluator,
            hash_mb=self.hash_mb,
            max_quiescence_depth=self.max_quiescence_depth,
            aspiration_window_cp=self.aspiration_window_cp,
        )

    @staticmethod
    def _parse_go(tokens: Sequence[str]) -> SearchLimits:
        fields = {
            "depth": "depth",
            "nodes": "nodes",
            "movetime": "move_time_ms",
            "wtime": "white_time_ms",
            "btime": "black_time_ms",
            "winc": "white_increment_ms",
            "binc": "black_increment_ms",
            "movestogo": "moves_to_go",
        }
        values: dict[str, int] = {}
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if token == "infinite":
                index += 1
                continue
            field = fields.get(token)
            if field is None:
                raise UCIProtocolError(f"unsupported go token: {token}")
            if field in values:
                raise UCIProtocolError(f"duplicate go field: {token}")
            if index + 1 >= len(tokens):
                raise UCIProtocolError(f"go {token} requires an integer value")
            try:
                values[field] = int(tokens[index + 1])
            except ValueError as error:
                raise UCIProtocolError(f"go {token} requires an integer value") from error
            index += 2
        limits = SearchLimits(**values)
        try:
            limits.validate()
        except ValueError as error:
            raise UCIProtocolError(f"invalid go limits: {error}") from error
        return limits

    def _stop_and_wait(self) -> None:
        self.stop()
        self.wait_for_search()

    def _is_current_search(self, search_id: int) -> bool:
        with self._state_lock:
            return self._search_id == search_id and not self._quitting

    @staticmethod
    def _parse_integer(name: str, value: str) -> int:
        if not value:
            raise UCIProtocolError(f"{name} requires a value")
        try:
            return int(value)
        except ValueError as error:
            raise UCIProtocolError(f"{name} requires an integer value") from error

    @staticmethod
    def _validate_hash(value: int) -> int:
        if not MIN_HASH_MB <= value <= MAX_HASH_MB:
            raise UCIProtocolError(
                f"Hash must be between {MIN_HASH_MB} and {MAX_HASH_MB} MiB"
            )
        return value

    @staticmethod
    def _validate_threads(value: int) -> int:
        if value != 1:
            raise UCIProtocolError("Threads must be 1 in engine v1")
        return value

    @staticmethod
    def _validate_seed(value: int) -> int:
        if not 0 <= value <= MAX_SEED:
            raise UCIProtocolError(f"Seed must be between 0 and {MAX_SEED}")
        return value

    def _send(self, message: str) -> None:
        with self._write_lock:
            print(message, file=self.stdout, flush=True)

    def _diagnostic(self, message: str) -> None:
        print(f"uci error: {message}", file=self.stderr, flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the neural chess engine over UCI")
    parser.add_argument("--model", type=Path, help="validated inference-only model artifact")
    parser.add_argument("--hash", type=int, default=64, dest="hash_mb", help="hash size in MiB")
    parser.add_argument("--threads", type=int, default=1, help="must be 1 in engine v1")
    parser.add_argument("--seed", type=int, default=20260713)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        adapter = UCIEngine(
            model_path=args.model,
            hash_mb=args.hash_mb,
            threads=args.threads,
            seed=args.seed,
        )
    except (UCIProtocolError, ValueError, OSError) as error:
        print(f"uci error: {error}", file=sys.stderr)
        return 2
    return adapter.run()


if __name__ == "__main__":
    raise SystemExit(main())
