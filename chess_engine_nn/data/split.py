"""Deterministic game-level dataset splitting."""

import hashlib

from chess_engine_nn.data.records import SplitName
from chess_engine_nn.errors import ConfigurationError


def validate_split_ratios(train: int, validation: int, test: int) -> None:
    if min(train, validation, test) < 0:
        raise ConfigurationError("Split ratios cannot be negative")
    if train + validation + test != 100:
        raise ConfigurationError("Split ratios must total 100")
    if train == 0:
        raise ConfigurationError("Training split cannot be empty")


def assign_game_split(
    game_id: str, *, seed: int, train: int = 90, validation: int = 5, test: int = 5
) -> SplitName:
    """Assign all positions from a stable game ID to one seeded split."""
    validate_split_ratios(train, validation, test)
    digest = hashlib.sha256(f"{seed}:{game_id}".encode()).digest()
    bucket = int.from_bytes(digest[:8], "big") % 100
    if bucket < train:
        return "train"
    if bucket < train + validation:
        return "validation"
    return "test"
