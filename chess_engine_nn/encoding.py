"""Versioned chess-position feature encoding shared by training and inference."""

from collections.abc import Sequence

import chess
import numpy as np

from chess_engine_nn.errors import EncodingError

FEATURE_SCHEMA_VERSION = 1
PIECE_FEATURE_COUNT = 12 * 64
SIDE_TO_MOVE_INDEX = PIECE_FEATURE_COUNT
CASTLING_OFFSET = SIDE_TO_MOVE_INDEX + 1
EN_PASSANT_OFFSET = CASTLING_OFFSET + 4
FEATURE_COUNT = EN_PASSANT_OFFSET + 8


class FeatureEncoder:
    """Encode a board relative to its side to move using feature schema v1.

    Piece planes 0..5 contain the friendly pawn through king. Planes 6..11
    contain the enemy pawn through king. Black-to-move squares are vertically
    mirrored, making the friendly army advance toward increasing canonical
    ranks in either perspective.
    """

    schema_version = FEATURE_SCHEMA_VERSION
    feature_count = FEATURE_COUNT

    def active_indices(self, board: chess.Board) -> np.ndarray:
        """Return sorted, unique active indices for ``board`` as int64 values."""
        if not isinstance(board, chess.Board):
            raise EncodingError("FeatureEncoder expects a python-chess Board")

        perspective = board.turn
        indices: list[int] = []
        for square, piece in board.piece_map().items():
            relation = 0 if piece.color == perspective else 6
            plane = relation + piece.piece_type - 1
            canonical_square = square if perspective == chess.WHITE else chess.square_mirror(square)
            indices.append(plane * 64 + canonical_square)

        # Preserve original side to move even though the piece representation is canonical.
        if board.turn == chess.BLACK:
            indices.append(SIDE_TO_MOVE_INDEX)

        friendly = perspective
        enemy = not perspective
        castling = (
            board.has_kingside_castling_rights(friendly),
            board.has_queenside_castling_rights(friendly),
            board.has_kingside_castling_rights(enemy),
            board.has_queenside_castling_rights(enemy),
        )
        indices.extend(CASTLING_OFFSET + offset for offset, active in enumerate(castling) if active)

        if board.has_legal_en_passant() and board.ep_square is not None:
            indices.append(EN_PASSANT_OFFSET + chess.square_file(board.ep_square))

        encoded = np.asarray(sorted(indices), dtype=np.int64)
        if encoded.size and (encoded[0] < 0 or encoded[-1] >= FEATURE_COUNT):
            raise EncodingError("Encoder produced an out-of-range feature index")
        if encoded.size != np.unique(encoded).size:
            raise EncodingError("Encoder produced duplicate feature indices")
        return encoded

    def encode_dense(self, board: chess.Board) -> np.ndarray:
        """Return one dense float32 feature vector equivalent to sparse indices."""
        result = np.zeros(FEATURE_COUNT, dtype=np.float32)
        result[self.active_indices(board)] = 1.0
        return result

    def encode_batch(self, boards: Sequence[chess.Board]) -> np.ndarray:
        """Return a dense float32 array with shape ``(len(boards), 781)``."""
        result = np.zeros((len(boards), FEATURE_COUNT), dtype=np.float32)
        for row, board in enumerate(boards):
            result[row, self.active_indices(board)] = 1.0
        return result
