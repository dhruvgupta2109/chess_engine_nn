import pytest

from chess_engine_nn.data.split import assign_game_split, validate_split_ratios
from chess_engine_nn.errors import ConfigurationError


def test_game_split_is_stable_and_seeded() -> None:
    assert assign_game_split("game-a", seed=7) == assign_game_split("game-a", seed=7)
    assert {assign_game_split(f"game-{index}", seed=7) for index in range(100)} == {
        "train",
        "validation",
        "test",
    }


@pytest.mark.parametrize("ratios", [(89, 5, 5), (-1, 96, 5), (0, 50, 50)])
def test_invalid_ratios_are_rejected(ratios: tuple[int, int, int]) -> None:
    with pytest.raises(ConfigurationError):
        validate_split_ratios(*ratios)
