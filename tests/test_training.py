
import chess
import numpy as np
import torch

from chess_engine_nn.config import TrainingConfig
from chess_engine_nn.evaluator import MaterialEvaluator
from chess_engine_nn.model import ModelConfig, NnueValueNetwork
from chess_engine_nn.training.dataset import JsonlPositionDataset
from chess_engine_nn.training.train import evaluate_dataset, load_checkpoint, train_model


def smoke_config(epochs: int) -> TrainingConfig:
    return TrainingConfig(
        accumulator_dim=16,
        hidden_dim=8,
        target_cap_cp=1_000,
        batch_size=6,
        learning_rate=0.01,
        epochs=epochs,
        patience=0,
        checkpoint_every=1,
        huber_delta=0.1,
        draw_band_cp=25,
        device="cpu",
    )


def test_cpu_training_writes_checkpoints_and_improves(training_dataset, tmp_path) -> None:
    result = train_model(training_dataset, tmp_path / "run", smoke_config(4), seed=11)
    assert result.best_checkpoint.is_file()
    assert result.last_checkpoint.is_file()
    assert result.epochs_completed == 4
    assert result.best_validation_loss <= result.history[0].validation_loss
    checkpoint = load_checkpoint(result.best_checkpoint)
    assert checkpoint["optimizer_state"]
    assert checkpoint["metadata"]["dataset_manifest_sha256"]
    assert checkpoint["metadata"]["torch_version"] == torch.__version__


def test_resume_matches_uninterrupted_training(training_dataset, tmp_path) -> None:
    partial = train_model(training_dataset, tmp_path / "partial", smoke_config(2), seed=19)
    resumed = train_model(
        training_dataset,
        tmp_path / "partial",
        smoke_config(4),
        seed=19,
        resume=partial.last_checkpoint,
    )
    uninterrupted = train_model(
        training_dataset, tmp_path / "whole", smoke_config(4), seed=19
    )
    resumed_state = load_checkpoint(resumed.last_checkpoint)["model_state"]
    whole_state = load_checkpoint(uninterrupted.last_checkpoint)["model_state"]
    assert resumed.history == uninterrupted.history
    assert all(torch.equal(resumed_state[key], whole_state[key]) for key in resumed_state)


def test_neural_smoke_model_beats_material_on_fixture(training_dataset, tmp_path) -> None:
    result = train_model(training_dataset, tmp_path / "run", smoke_config(6), seed=23)
    checkpoint = load_checkpoint(result.best_checkpoint)
    model = NnueValueNetwork(ModelConfig.from_dict(checkpoint["model_config"]))
    model.load_state_dict(checkpoint["model_state"])
    dataset = JsonlPositionDataset(training_dataset, "validation", target_cap_cp=1_000)
    _, neural = evaluate_dataset(
        model,
        dataset,
        batch_size=6,
        device=torch.device("cpu"),
        huber_delta=0.1,
        draw_band_cp=25,
    )
    material = MaterialEvaluator()
    material_predictions = np.array(
        [
            material.evaluate(chess.Board(dataset.record_at(index).fen))
            for index in range(len(dataset))
        ]
    )
    targets = np.array([dataset.record_at(index).score_cp for index in range(len(dataset))])
    material_mae = float(np.mean(np.abs(material_predictions - targets)))
    assert neural.mae_cp < material_mae
