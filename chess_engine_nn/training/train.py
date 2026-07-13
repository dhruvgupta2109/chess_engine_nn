"""Deterministic CPU-first model training and resumable checkpoints."""

import platform
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import chess
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from chess_engine_nn import __version__
from chess_engine_nn.config import TrainingConfig
from chess_engine_nn.data.records import DatasetError, file_sha256
from chess_engine_nn.errors import ModelArtifactError
from chess_engine_nn.model import ModelConfig, NnueValueNetwork
from chess_engine_nn.reproducibility import seed_everything
from chess_engine_nn.training.dataset import JsonlPositionDataset
from chess_engine_nn.training.metrics import EvaluationMetrics, calculate_metrics

CHECKPOINT_VERSION = 1


@dataclass(frozen=True)
class EpochReport:
    epoch: int
    training_loss: float
    validation_loss: float
    metrics: dict[str, object]


@dataclass(frozen=True)
class TrainingResult:
    best_checkpoint: Path
    last_checkpoint: Path
    best_epoch: int
    epochs_completed: int
    best_validation_loss: float
    history: tuple[EpochReport, ...]


def resolve_device(requested: str) -> torch.device:
    if requested == "mps":
        if not torch.backends.mps.is_available():
            raise ModelArtifactError("MPS was requested but is not available")
        return torch.device("mps")
    if requested != "cpu":
        raise ModelArtifactError(f"Unsupported training device: {requested}")
    return torch.device("cpu")


def _source_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _training_metadata(dataset_dir: Path, seed: int) -> dict[str, object]:
    manifest_path = dataset_dir / "manifest.json"
    return {
        "project_version": __version__,
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "source_commit": _source_commit(),
        "dataset_manifest_sha256": file_sha256(manifest_path),
        "seed": seed,
    }


def atomic_torch_save(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, temporary)
    try:
        loaded = torch.load(temporary, map_location="cpu", weights_only=False)
    except Exception as error:
        temporary.unlink(missing_ok=True)
        raise ModelArtifactError(f"Unable to validate saved artifact {path}: {error}") from error
    if loaded.get("artifact_type") != payload.get("artifact_type"):
        temporary.unlink(missing_ok=True)
        raise ModelArtifactError(f"Artifact validation failed: {path}")
    temporary.replace(path)


def load_checkpoint(path: Path) -> dict[str, Any]:
    try:
        payload = torch.load(path, map_location="cpu", weights_only=False)
    except (OSError, RuntimeError, ValueError) as error:
        raise ModelArtifactError(f"Unable to load checkpoint {path}: {error}") from error
    if payload.get("artifact_type") != "training_checkpoint":
        raise ModelArtifactError(f"Not a training checkpoint: {path}")
    if payload.get("checkpoint_version") != CHECKPOINT_VERSION:
        version = payload.get("checkpoint_version")
        raise ModelArtifactError(f"Unsupported checkpoint version: {version}")
    try:
        ModelConfig.from_dict(payload["model_config"])
    except (KeyError, TypeError, ValueError) as error:
        raise ModelArtifactError(f"Invalid checkpoint model metadata: {error}") from error
    return payload


def evaluate_dataset(
    model: NnueValueNetwork,
    dataset: JsonlPositionDataset,
    *,
    batch_size: int,
    device: torch.device,
    huber_delta: float,
    draw_band_cp: int,
) -> tuple[float, EvaluationMetrics]:
    if len(dataset) == 0:
        raise DatasetError(f"Dataset split is empty: {dataset.split}")
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    loss_function = nn.HuberLoss(delta=huber_delta, reduction="sum")
    total_loss = 0.0
    predictions: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for features, target in loader:
            features = features.to(device)
            target = target.to(device)
            output = model(features)
            total_loss += float(loss_function(output, target).item())
            predictions.append(model.to_centipawns(output).cpu().numpy())
            targets.append(torch.round(target * model.config.target_cap_cp).cpu().numpy())
    outcomes: list[int] = []
    for index in range(len(dataset)):
        record = dataset.record_at(index)
        white_outcome = 1 if record.result == "1-0" else -1 if record.result == "0-1" else 0
        board = chess.Board(record.fen)
        outcomes.append(white_outcome if board.turn else -white_outcome)
    metrics = calculate_metrics(
        np.concatenate(predictions),
        np.concatenate(targets),
        draw_band_cp=draw_band_cp,
        outcomes=np.asarray(outcomes),
    )
    return total_loss / len(dataset), metrics


def train_model(
    dataset_dir: Path,
    output_dir: Path,
    config: TrainingConfig,
    *,
    seed: int,
    resume: Path | None = None,
) -> TrainingResult:
    """Train deterministically, writing atomic ``last.pt`` and ``best.pt`` files."""
    seed_everything(seed)
    device = resolve_device(config.device)
    model_config = ModelConfig(
        accumulator_dim=config.accumulator_dim,
        hidden_dim=config.hidden_dim,
        target_cap_cp=config.target_cap_cp,
    )
    train_data = JsonlPositionDataset(dataset_dir, "train", target_cap_cp=config.target_cap_cp)
    validation_data = JsonlPositionDataset(
        dataset_dir, "validation", target_cap_cp=config.target_cap_cp
    )
    if len(train_data) == 0 or len(validation_data) == 0:
        raise DatasetError("Training and validation splits must both contain records")

    model = NnueValueNetwork(model_config).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    start_epoch = 1
    best_loss = float("inf")
    best_epoch = 0
    stale_epochs = 0
    history: list[EpochReport] = []
    metadata = _training_metadata(dataset_dir, seed)

    if resume is not None:
        checkpoint = load_checkpoint(resume)
        if checkpoint["model_config"] != model_config.to_dict():
            raise ModelArtifactError("Resume model configuration does not match")
        previous_config = dict(checkpoint["training_config"])
        current_config = asdict(config)
        previous_config.pop("epochs")
        current_epochs = current_config.pop("epochs")
        if previous_config != current_config or current_epochs < checkpoint["epoch"]:
            raise ModelArtifactError("Resume training configuration does not match")
        if checkpoint["metadata"]["dataset_manifest_sha256"] != metadata[
            "dataset_manifest_sha256"
        ]:
            raise ModelArtifactError("Resume dataset manifest does not match")
        if checkpoint["metadata"]["seed"] != seed:
            raise ModelArtifactError("Resume seed does not match")
        model.load_state_dict(checkpoint["model_state"])
        optimizer.load_state_dict(checkpoint["optimizer_state"])
        for optimizer_state in optimizer.state.values():
            for key, value in optimizer_state.items():
                if isinstance(value, torch.Tensor):
                    optimizer_state[key] = value.to(device)
        start_epoch = checkpoint["epoch"] + 1
        best_loss = checkpoint["best_validation_loss"]
        best_epoch = checkpoint["best_epoch"]
        stale_epochs = checkpoint["stale_epochs"]
        history = [EpochReport(**report) for report in checkpoint["history"]]

    loss_function = nn.HuberLoss(delta=config.huber_delta)
    best_path = output_dir / "best.pt"
    last_path = output_dir / "last.pt"
    for epoch in range(start_epoch, config.epochs + 1):
        generator = torch.Generator().manual_seed(seed + epoch)
        loader = DataLoader(
            train_data,
            batch_size=config.batch_size,
            shuffle=True,
            generator=generator,
            num_workers=config.num_workers,
        )
        model.train()
        total_training_loss = 0.0
        for features, target in loader:
            features = features.to(device)
            target = target.to(device)
            optimizer.zero_grad(set_to_none=True)
            output = model(features)
            loss = loss_function(output, target)
            loss.backward()
            optimizer.step()
            total_training_loss += float(loss.item()) * len(features)
        training_loss = total_training_loss / len(train_data)
        validation_loss, metrics = evaluate_dataset(
            model,
            validation_data,
            batch_size=config.batch_size,
            device=device,
            huber_delta=config.huber_delta,
            draw_band_cp=config.draw_band_cp,
        )
        report = EpochReport(epoch, training_loss, validation_loss, metrics.to_dict())
        history.append(report)
        improved = validation_loss < best_loss
        if improved:
            best_loss = validation_loss
            best_epoch = epoch
            stale_epochs = 0
        else:
            stale_epochs += 1

        payload = {
            "artifact_type": "training_checkpoint",
            "checkpoint_version": CHECKPOINT_VERSION,
            "model_config": model_config.to_dict(),
            "training_config": asdict(config),
            "model_state": model.state_dict(),
            "optimizer_state": optimizer.state_dict(),
            "epoch": epoch,
            "best_epoch": best_epoch,
            "best_validation_loss": best_loss,
            "stale_epochs": stale_epochs,
            "history": [asdict(item) for item in history],
            "metadata": metadata,
        }
        atomic_torch_save(payload, last_path)
        if improved:
            atomic_torch_save(payload, best_path)
        if config.patience and stale_epochs >= config.patience:
            break

    if not best_path.exists() or not last_path.exists():
        raise ModelArtifactError("Training finished without valid best and last checkpoints")
    return TrainingResult(
        best_checkpoint=best_path,
        last_checkpoint=last_path,
        best_epoch=best_epoch,
        epochs_completed=history[-1].epoch,
        best_validation_loss=best_loss,
        history=tuple(history),
    )
