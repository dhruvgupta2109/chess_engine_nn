"""Versioned NNUE-style PyTorch value network."""

from dataclasses import asdict, dataclass

import torch
from torch import nn

from chess_engine_nn.encoding import FEATURE_COUNT, FEATURE_SCHEMA_VERSION

MODEL_ARCHITECTURE_NAME = "nnue-mlp"
MODEL_ARCHITECTURE_VERSION = 1


@dataclass(frozen=True)
class ModelConfig:
    """Shape and score conversion contract saved with every artifact."""

    input_dim: int = FEATURE_COUNT
    accumulator_dim: int = 256
    hidden_dim: int = 32
    target_cap_cp: int = 10_000
    architecture_name: str = MODEL_ARCHITECTURE_NAME
    architecture_version: int = MODEL_ARCHITECTURE_VERSION
    feature_schema_version: int = FEATURE_SCHEMA_VERSION

    def validate(self) -> None:
        if self.input_dim != FEATURE_COUNT:
            raise ValueError(f"Model input_dim must be {FEATURE_COUNT}")
        if self.accumulator_dim <= 0 or self.hidden_dim <= 0 or self.target_cap_cp <= 0:
            raise ValueError("Model dimensions and target cap must be positive")
        if self.architecture_name != MODEL_ARCHITECTURE_NAME:
            raise ValueError(f"Unsupported architecture: {self.architecture_name}")
        if self.architecture_version != MODEL_ARCHITECTURE_VERSION:
            raise ValueError(f"Unsupported architecture version: {self.architecture_version}")
        if self.feature_schema_version != FEATURE_SCHEMA_VERSION:
            raise ValueError(f"Unsupported feature schema: {self.feature_schema_version}")

    def to_dict(self) -> dict[str, int | str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "ModelConfig":
        config = cls(**value)  # type: ignore[arg-type]
        config.validate()
        return config


class ClippedReLU(nn.Module):
    """NNUE-style clipped rectifier with output in [0, 1]."""

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return torch.clamp(inputs, min=0.0, max=1.0)


class NnueValueNetwork(nn.Module):
    """Compact scalar value model returning normalized values in [-1, 1]."""

    def __init__(self, config: ModelConfig | None = None) -> None:
        super().__init__()
        self.config = config or ModelConfig()
        self.config.validate()
        self.accumulator = nn.Linear(self.config.input_dim, self.config.accumulator_dim)
        self.hidden = nn.Linear(self.config.accumulator_dim, self.config.hidden_dim)
        self.output = nn.Linear(self.config.hidden_dim, 1)
        self.activation = ClippedReLU()

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        accumulated = self.activation(self.accumulator(inputs))
        hidden = self.activation(self.hidden(accumulated))
        return torch.tanh(self.output(hidden)).squeeze(-1)

    def to_centipawns(self, normalized: torch.Tensor) -> torch.Tensor:
        """Convert normalized outputs to clamped centipawn values."""
        return torch.round(normalized * self.config.target_cap_cp).clamp(
            -self.config.target_cap_cp, self.config.target_cap_cp
        )
