import json
from pathlib import Path

import chess
import numpy as np
import pytest

from chess_engine_nn.encoding import (
    CASTLING_OFFSET,
    EN_PASSANT_OFFSET,
    FEATURE_COUNT,
    SIDE_TO_MOVE_INDEX,
    FeatureEncoder,
)


def test_starting_position_has_expected_shape_and_state_features() -> None:
    encoder = FeatureEncoder()
    indices = encoder.active_indices(chess.Board())

    assert FEATURE_COUNT == 781
    assert len(indices) == 36  # 32 pieces plus four castling rights
    assert SIDE_TO_MOVE_INDEX not in indices
    assert set(range(CASTLING_OFFSET, CASTLING_OFFSET + 4)).issubset(indices)
    assert not set(range(EN_PASSANT_OFFSET, FEATURE_COUNT)).intersection(indices)
    assert np.array_equal(indices, np.unique(indices))


def test_color_and_turn_canonicalization_preserves_piece_planes() -> None:
    encoder = FeatureEncoder()
    white = chess.Board("8/8/8/8/8/8/P7/K6k w - - 0 1")
    black = chess.Board("k6K/p7/8/8/8/8/8/8 b - - 0 1")

    white_indices = encoder.active_indices(white)
    black_indices = encoder.active_indices(black)

    assert np.array_equal(white_indices, black_indices[black_indices != SIDE_TO_MOVE_INDEX])
    assert SIDE_TO_MOVE_INDEX in black_indices


def test_castling_rights_are_relative_to_side_to_move() -> None:
    encoder = FeatureEncoder()
    board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R b Kq - 0 1")
    indices = set(encoder.active_indices(board))

    assert CASTLING_OFFSET + 1 in indices  # friendly (black) queenside
    assert CASTLING_OFFSET + 2 in indices  # enemy (white) kingside
    assert CASTLING_OFFSET not in indices
    assert CASTLING_OFFSET + 3 not in indices


def test_en_passant_feature_requires_a_legal_capture() -> None:
    encoder = FeatureEncoder()
    legal = chess.Board("8/8/8/3pP3/8/8/8/K6k w - d6 0 1")
    phantom = chess.Board("8/8/8/3p4/8/8/8/K6k w - d6 0 1")

    assert EN_PASSANT_OFFSET + chess.FILE_NAMES.index("d") in encoder.active_indices(legal)
    assert not set(range(EN_PASSANT_OFFSET, FEATURE_COUNT)).intersection(
        encoder.active_indices(phantom)
    )


def test_promoted_piece_uses_its_current_piece_plane() -> None:
    encoder = FeatureEncoder()
    board = chess.Board("Q7/8/8/8/8/8/8/K6k w - - 0 1")
    queen_a8 = (chess.QUEEN - 1) * 64 + chess.A8

    assert queen_a8 in encoder.active_indices(board)


def test_dense_batch_matches_sparse_indices() -> None:
    encoder = FeatureEncoder()
    boards = [chess.Board(), chess.Board("8/8/8/8/8/8/P7/K6k w - - 0 1")]
    batch = encoder.encode_batch(boards)

    assert batch.shape == (2, FEATURE_COUNT)
    assert batch.dtype == np.float32
    for row, board in enumerate(boards):
        assert np.array_equal(np.flatnonzero(batch[row]), encoder.active_indices(board))


def test_invalid_board_type_is_rejected() -> None:
    with pytest.raises(Exception, match="python-chess Board"):
        FeatureEncoder().active_indices(object())  # type: ignore[arg-type]


def test_feature_schema_v1_matches_golden_fixtures() -> None:
    path = Path(__file__).parent / "positions" / "encoding_v1_golden.json"
    fixtures = json.loads(path.read_text())
    encoder = FeatureEncoder()
    for fixture in fixtures:
        actual = encoder.active_indices(chess.Board(fixture["fen"])).tolist()
        assert actual == fixture["active_indices"], fixture["name"]
