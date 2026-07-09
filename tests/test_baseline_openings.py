from pathlib import Path

import chess


def test_baseline_opening_set_is_valid_and_unique() -> None:
    path = Path(__file__).parent / "positions" / "baseline_openings.epd"
    positions: set[str] = set()
    identifiers: set[str] = set()
    for line in path.read_text().splitlines():
        board = chess.Board()
        operations = board.set_epd(line)
        assert board.is_valid()
        assert not board.is_game_over()
        assert operations["id"] not in identifiers
        positions.add(board.fen(en_passant="fen"))
        identifiers.add(operations["id"])
    assert len(positions) == 8
    assert len(identifiers) == 8
