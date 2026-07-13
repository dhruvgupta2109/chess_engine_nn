import pytest

from chess_engine_nn.time_control import SearchLimits, allocated_time_ms


def test_direct_and_clock_time_allocation() -> None:
    assert allocated_time_ms(SearchLimits(move_time_ms=200), white_to_move=True) == 200
    clock = SearchLimits(white_time_ms=30_000, black_time_ms=10_000, white_increment_ms=1_000)
    white = allocated_time_ms(clock, white_to_move=True)
    black = allocated_time_ms(clock, white_to_move=False)
    assert white is not None and black is not None
    assert white > black
    assert white < 30_000


def test_invalid_limits_are_rejected() -> None:
    with pytest.raises(ValueError):
        SearchLimits(depth=0).validate()
    with pytest.raises(ValueError):
        allocated_time_ms(SearchLimits(white_time_ms=-1), white_to_move=True)
