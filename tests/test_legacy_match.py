import chess

from chess_engine_nn.evaluator import MaterialEvaluator
from tools.run_legacy_match import (
    _candidate_score,
    legacy_board_from_python,
    load_openings,
    play_game,
    python_move_from_legacy,
)


def test_python_position_translates_to_legacy_piece_and_rule_state(tmp_path) -> None:
    board = chess.Board("r3k2r/8/8/3pP3/8/8/8/R3K2R w Kq d6 0 1")
    legacy = legacy_board_from_python(board)

    assert legacy.state[7][0] == 4
    assert legacy.state[0][4] == -6
    assert legacy.state[2][3] == -7
    assert not legacy.white_king_moved
    assert not legacy.white_rook_h_moved
    assert legacy.white_rook_a_moved
    assert not legacy.black_king_moved
    assert not legacy.black_rook_a_moved
    assert legacy.black_rook_h_moved


def test_legacy_move_conversion_handles_normal_castling_and_promotion() -> None:
    assert python_move_from_legacy((6, 4, 4, 4, None)) == chess.Move.from_uci("e2e4")
    assert python_move_from_legacy((7, 4, 7, 6, None)) == chess.Move.from_uci("e1g1")
    assert python_move_from_legacy((1, 0, 0, 0, 5)) == chess.Move.from_uci("a7a8q")


def test_candidate_scoring_is_color_relative() -> None:
    assert _candidate_score("1-0", chess.WHITE) == 1.0
    assert _candidate_score("1-0", chess.BLACK) == 0.0
    assert _candidate_score("0-1", chess.BLACK) == 1.0
    assert _candidate_score("1/2-1/2", chess.WHITE) == 0.5


def test_opening_loader_rejects_terminal_epd(tmp_path) -> None:
    path = tmp_path / "terminal.epd"
    path.write_text('7k/6Q1/6K1/8/8/8/8/8 b - - id "mate";\n')
    try:
        load_openings(path)
    except ValueError as error:
        assert "terminal" in str(error)
    else:
        raise AssertionError("terminal opening was accepted")


def test_short_game_uses_both_engines_and_ends_at_ply_cap() -> None:
    record, game = play_game(
        chess.Board(),
        opening_id="initial",
        cycle=1,
        game_number=1,
        candidate_color=chess.WHITE,
        evaluator=MaterialEvaluator(),
        model_weights_sha256="test-weights",
        max_plies=2,
        depth=1,
    )

    assert record.result == "1/2-1/2"
    assert record.termination == "ply_cap"
    assert record.plies == 2
    assert record.illegal_move is None
    assert record.candidate_nodes > 0
    assert game.headers["Result"] == "1/2-1/2"
