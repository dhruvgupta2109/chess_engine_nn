"""Position-evaluation interfaces and the Phase 1 material baseline."""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

import chess
import numpy as np

PIECE_VALUES_CP = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


@runtime_checkable
class PositionEvaluator(Protocol):
    """Position evaluator returning centipawns from side-to-move perspective."""

    def evaluate(self, board: chess.Board) -> int:
        """Evaluate one non-terminal board from its side-to-move perspective."""
        ...

    def evaluate_batch(self, boards: Sequence[chess.Board]) -> np.ndarray:
        """Evaluate boards into a signed int32 centipawn array."""
        ...


class MaterialEvaluator:
    """Deterministic baseline used to validate the final evaluator boundary."""

    def evaluate(self, board: chess.Board) -> int:
        """Return material balance in centipawns for the side to move."""
        white_score = 0
        black_score = 0
        for piece_type, value in PIECE_VALUES_CP.items():
            white_score += len(board.pieces(piece_type, chess.WHITE)) * value
            black_score += len(board.pieces(piece_type, chess.BLACK)) * value
        score = white_score - black_score
        return score if board.turn == chess.WHITE else -score

    def evaluate_batch(self, boards: Sequence[chess.Board]) -> np.ndarray:
        """Return material evaluations as a signed int32 array."""
        return np.asarray([self.evaluate(board) for board in boards], dtype=np.int32)
