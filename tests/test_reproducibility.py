import os
import random

import numpy as np
import pytest

from chess_engine_nn.reproducibility import seed_everything


def test_seed_everything_repeats_python_and_numpy_sequences() -> None:
    state = seed_everything(42)
    first = (random.random(), np.random.random())
    seed_everything(42)
    second = (random.random(), np.random.random())
    assert first == second
    assert state.seed == 42
    assert state.python_hash_seed == "42"
    assert os.environ["PYTHONHASHSEED"] == "42"


def test_negative_seed_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        seed_everything(-1)
