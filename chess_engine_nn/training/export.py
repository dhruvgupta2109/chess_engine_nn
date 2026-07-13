"""Inference-only artifact export and deterministic weight validation."""

from pathlib import Path
from typing import Any

import chess

from chess_engine_nn.artifacts import INFERENCE_ARTIFACT_VERSION, state_dict_sha256
from chess_engine_nn.model import ModelConfig, NnueValueNetwork
from chess_engine_nn.training.train import atomic_torch_save, load_checkpoint

GOLDEN_FENS = (
    chess.STARTING_FEN,
    "7k/8/8/8/8/8/Q7/K7 w - - 0 1",
    "7k/8/8/8/8/8/Q7/K7 b - - 0 1",
)


def export_checkpoint(checkpoint_path: Path, output_path: Path) -> Path:
    """Export a checkpoint without optimizer or training-progress state."""
    checkpoint = load_checkpoint(checkpoint_path)
    config = ModelConfig.from_dict(checkpoint["model_config"])
    model = NnueValueNetwork(config)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    from chess_engine_nn.evaluator import TorchPositionEvaluator

    evaluator = TorchPositionEvaluator(model)
    golden = [{"fen": fen, "score_cp": evaluator.evaluate(chess.Board(fen))} for fen in GOLDEN_FENS]
    state = {name: value.detach().cpu() for name, value in model.state_dict().items()}
    payload: dict[str, Any] = {
        "artifact_type": "inference_model",
        "artifact_version": INFERENCE_ARTIFACT_VERSION,
        "model_config": config.to_dict(),
        "model_state": state,
        "weights_sha256": state_dict_sha256(state),
        "golden_positions": golden,
        "training_metadata": checkpoint["metadata"],
        "validation_summary": {
            "best_epoch": checkpoint["best_epoch"],
            "best_validation_loss": checkpoint["best_validation_loss"],
            "metrics": checkpoint["history"][checkpoint["best_epoch"] - 1]["metrics"],
        },
    }
    atomic_torch_save(payload, output_path)

    from chess_engine_nn.evaluator import load_evaluator

    load_evaluator(output_path)
    return output_path
