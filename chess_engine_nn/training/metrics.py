"""Centipawn prediction metrics used for validation and model reports."""

import math
from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class EvaluationMetrics:
    count: int
    mae_cp: float
    rmse_cp: float
    sign_accuracy: float
    outcome_accuracy: float
    bucket_mae_cp: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def calculate_metrics(
    predictions_cp: np.ndarray,
    targets_cp: np.ndarray,
    *,
    draw_band_cp: int = 50,
    outcomes: np.ndarray | None = None,
) -> EvaluationMetrics:
    """Calculate errors, decisive sign accuracy, and target-magnitude buckets."""
    predictions = np.asarray(predictions_cp, dtype=np.float64).reshape(-1)
    targets = np.asarray(targets_cp, dtype=np.float64).reshape(-1)
    if predictions.shape != targets.shape or predictions.size == 0:
        raise ValueError("Predictions and targets must have the same non-empty shape")
    if not np.isfinite(predictions).all() or not np.isfinite(targets).all():
        raise ValueError("Metrics require finite values")
    errors = np.abs(predictions - targets)
    decisive = np.abs(targets) > draw_band_cp
    sign_accuracy = (
        float(np.mean(np.sign(predictions[decisive]) == np.sign(targets[decisive])))
        if decisive.any()
        else math.nan
    )
    outcome_accuracy = math.nan
    if outcomes is not None:
        outcome_values = np.asarray(outcomes, dtype=np.int8).reshape(-1)
        if outcome_values.shape != targets.shape:
            raise ValueError("Outcomes must have the same shape as predictions")
        decided = outcome_values != 0
        if decided.any():
            outcome_accuracy = float(
                np.mean(np.sign(predictions[decided]) == outcome_values[decided])
            )
    buckets = {
        "drawish_0_100": np.abs(targets) <= 100,
        "small_101_300": (np.abs(targets) > 100) & (np.abs(targets) <= 300),
        "medium_301_900": (np.abs(targets) > 300) & (np.abs(targets) <= 900),
        "large_901_plus": np.abs(targets) > 900,
    }
    bucket_mae = {
        name: float(np.mean(errors[mask])) for name, mask in buckets.items() if mask.any()
    }
    return EvaluationMetrics(
        count=int(targets.size),
        mae_cp=float(np.mean(errors)),
        rmse_cp=float(np.sqrt(np.mean(np.square(predictions - targets)))),
        sign_accuracy=sign_accuracy,
        outcome_accuracy=outcome_accuracy,
        bucket_mae_cp=bucket_mae,
    )
