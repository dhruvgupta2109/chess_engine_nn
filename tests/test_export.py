from pathlib import Path

import chess
import pytest
import torch

from chess_engine_nn.config import TrainingConfig
from chess_engine_nn.errors import ModelArtifactError
from chess_engine_nn.evaluator import load_evaluator
from chess_engine_nn.training.export import export_checkpoint
from chess_engine_nn.training.train import train_model


def config() -> TrainingConfig:
    return TrainingConfig(
        accumulator_dim=16,
        hidden_dim=8,
        target_cap_cp=1_000,
        batch_size=6,
        learning_rate=0.01,
        epochs=3,
        patience=0,
        checkpoint_every=1,
        huber_delta=0.1,
        draw_band_cp=25,
    )


def test_export_is_inference_only_and_round_trips(training_dataset, tmp_path: Path) -> None:
    trained = train_model(training_dataset, tmp_path / "checkpoints", config(), seed=31)
    model_path = export_checkpoint(trained.best_checkpoint, tmp_path / "models" / "nnue.pt")
    payload = torch.load(model_path, map_location="cpu", weights_only=False)
    assert payload["artifact_type"] == "inference_model"
    assert "optimizer_state" not in payload
    assert "history" not in payload
    evaluator = load_evaluator(model_path)
    boards = [chess.Board(), chess.Board("7k/8/8/8/8/8/Q7/K7 w - - 0 1")]
    scores = evaluator.evaluate_batch(boards)
    assert scores.shape == (2,)
    assert all(-1_000 <= int(score) <= 1_000 for score in scores)


def test_corrupt_weight_checksum_is_rejected(training_dataset, tmp_path: Path) -> None:
    trained = train_model(training_dataset, tmp_path / "checkpoints", config(), seed=37)
    model_path = export_checkpoint(trained.best_checkpoint, tmp_path / "model.pt")
    payload = torch.load(model_path, map_location="cpu", weights_only=False)
    first = next(iter(payload["model_state"].values()))
    first.view(-1)[0] += 1
    corrupt = tmp_path / "corrupt.pt"
    torch.save(payload, corrupt)
    with pytest.raises(ModelArtifactError, match="checksum"):
        load_evaluator(corrupt)
