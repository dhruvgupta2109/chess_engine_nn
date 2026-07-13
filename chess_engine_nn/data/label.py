"""Stockfish teacher adapter with explicit limits and score normalization."""

import re
from dataclasses import dataclass
from pathlib import Path

import chess
import chess.engine

from chess_engine_nn.data.records import TeacherSettings
from chess_engine_nn.errors import ChessEngineError, ConfigurationError


class TeacherError(ChessEngineError):
    """Raised when the external teacher cannot start or label a position."""


@dataclass(frozen=True)
class LabelResult:
    score_cp: int
    mate_in: int | None


def make_limit(
    *, depth: int | None, nodes: int | None, time_ms: int | None
) -> tuple[str, int, chess.engine.Limit]:
    selected = [("depth", depth), ("nodes", nodes), ("time", time_ms)]
    selected = [(name, value) for name, value in selected if value is not None]
    if len(selected) != 1:
        raise ConfigurationError(
            "Stockfish labeling requires exactly one of depth, nodes, or time_ms"
        )
    name, value = selected[0]
    assert value is not None
    if value <= 0:
        raise ConfigurationError(f"Stockfish {name} limit must be positive")
    if name == "depth":
        return name, value, chess.engine.Limit(depth=value)
    if name == "nodes":
        return name, value, chess.engine.Limit(nodes=value)
    return name, value, chess.engine.Limit(time=value / 1000)


class StockfishTeacher:
    """Context-managed, single-process Stockfish position labeler."""

    def __init__(
        self,
        executable: Path,
        *,
        depth: int | None = None,
        nodes: int | None = None,
        time_ms: int | None = None,
        hash_mb: int = 64,
        threads: int = 1,
        mate_score_cp: int = 10_000,
    ) -> None:
        self.executable = executable
        self.limit_type, self.limit_value, self.limit = make_limit(
            depth=depth, nodes=nodes, time_ms=time_ms
        )
        if hash_mb <= 0 or threads <= 0 or mate_score_cp <= 0:
            raise ConfigurationError("Teacher hash, threads, and mate score must be positive")
        self.hash_mb = hash_mb
        self.threads = threads
        self.mate_score_cp = mate_score_cp
        self.engine: chess.engine.SimpleEngine | None = None
        self.settings: TeacherSettings | None = None

    def __enter__(self) -> "StockfishTeacher":
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(str(self.executable))
            self.engine.configure({"Hash": self.hash_mb, "Threads": self.threads})
        except (OSError, chess.engine.EngineError) as error:
            message = f"Unable to start Stockfish at {self.executable}: {error}"
            raise TeacherError(message) from error
        name = self.engine.id.get("name", "Stockfish")
        version_match = re.search(r"\b(\d+(?:\.\d+)*)\b", name)
        self.settings = TeacherSettings(
            name=name,
            version=version_match.group(1) if version_match else "unknown",
            limit_type=self.limit_type,  # type: ignore[arg-type]
            limit_value=self.limit_value,
            hash_mb=self.hash_mb,
            threads=self.threads,
        )
        return self

    def __exit__(self, *_: object) -> None:
        if self.engine is not None:
            self.engine.quit()
            self.engine = None

    def label(self, board: chess.Board) -> LabelResult:
        if self.engine is None:
            raise TeacherError("StockfishTeacher must be used as a context manager")
        try:
            info = self.engine.analyse(board, self.limit)
            pov_score = info["score"].pov(board.turn)
        except (chess.engine.EngineError, chess.engine.EngineTerminatedError, KeyError) as error:
            raise TeacherError(f"Stockfish failed to label {board.fen()}: {error}") from error
        mate_in = pov_score.mate()
        score_cp = pov_score.score(mate_score=self.mate_score_cp)
        if score_cp is None:
            raise TeacherError(f"Stockfish returned no finite score for {board.fen()}")
        score_cp = max(-self.mate_score_cp, min(self.mate_score_cp, score_cp))
        return LabelResult(score_cp=score_cp, mate_in=mate_in)
