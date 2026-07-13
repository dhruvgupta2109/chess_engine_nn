import chess

from chess_engine_nn.transposition import (
    BoundType,
    TranspositionEntry,
    TranspositionTable,
    position_hash,
)


def test_position_hash_includes_fifty_move_state() -> None:
    first = chess.Board()
    second = chess.Board(chess.STARTING_BOARD_FEN + " w KQkq - 12 7")
    assert position_hash(first) != position_hash(second)


def test_depth_preferred_replacement_and_capacity() -> None:
    table = TranspositionTable(1)
    table.capacity = 2
    shallow = TranspositionEntry(1, 1, 10, BoundType.EXACT, chess.Move.from_uci("e2e4"), 1)
    table.store(shallow)
    table.store(TranspositionEntry(1, 0, 20, BoundType.LOWER, None, 1))
    assert table.probe(1) == shallow
    deep = TranspositionEntry(1, 3, 30, BoundType.EXACT, None, 1)
    table.store(deep)
    assert table.probe(1) == deep
    table.store(TranspositionEntry(2, 1, 0, BoundType.UPPER, None, 1))
    table.store(TranspositionEntry(3, 2, 0, BoundType.EXACT, None, 2))
    assert len(table) == 2
    assert table.probe(1) is not None
    assert table.probe(2) is None
    assert table.probe(3) is not None


def test_clear_removes_entries() -> None:
    table = TranspositionTable(1)
    table.store(TranspositionEntry(1, 1, 0, BoundType.EXACT, None, 1))
    table.clear()
    assert len(table) == 0
