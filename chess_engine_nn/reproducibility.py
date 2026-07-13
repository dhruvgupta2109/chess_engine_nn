"""Deterministic seed handling shared by commands and experiments."""

import os
import random
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SeedState:
    """Resolved seed values applied to available random-number generators."""

    seed: int
    python_hash_seed: str
    torch_seeded: bool


def seed_everything(seed: int) -> SeedState:
    """Seed Python, NumPy, and PyTorch when the optional dependency is installed."""
    if seed < 0:
        raise ValueError("seed must be non-negative")
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed % (2**32))
    torch_seeded = False
    try:
        import torch
    except ImportError:
        pass
    else:
        torch.manual_seed(seed)
        torch_seeded = True
    return SeedState(seed=seed, python_hash_seed=str(seed), torch_seeded=torch_seeded)
