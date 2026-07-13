import math

import numpy as np
import pytest

from chess_engine_nn.training.metrics import calculate_metrics


def test_metrics_include_errors_sign_and_buckets() -> None:
    metrics = calculate_metrics(
        np.array([0, 200, -250, 500, -1000]),
        np.array([0, 100, -300, 400, -900]),
        draw_band_cp=50,
        outcomes=np.array([0, 1, -1, 1, -1]),
    )
    assert metrics.count == 5
    assert metrics.mae_cp == 70
    assert metrics.rmse_cp == pytest.approx(math.sqrt(6500))
    assert metrics.sign_accuracy == 1.0
    assert metrics.outcome_accuracy == 1.0
    assert set(metrics.bucket_mae_cp) == {
        "drawish_0_100",
        "small_101_300",
        "medium_301_900",
    }


def test_metrics_reject_non_finite_or_empty_input() -> None:
    with pytest.raises(ValueError):
        calculate_metrics(np.array([]), np.array([]))
    with pytest.raises(ValueError):
        calculate_metrics(np.array([np.nan]), np.array([0]))
