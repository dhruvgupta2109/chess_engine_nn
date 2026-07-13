"""Position-evaluation interfaces and the Phase 1 material baseline."""

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

import chess
import numpy as np
import torch

PIECE_VALUES_CP = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


@runtime_checkable
class PositionEvaluator(Protocol):
    """Position evaluator returning centipawns from side-to-move perspective."""

    def evaluate(self, board: chess.Board) -> int:
        """Evaluate one non-terminal board from its side-to-move perspective."""
        ...

    def evaluate_batch(self, boards: Sequence[chess.Board]) -> np.ndarray:
        """Evaluate boards into a signed int32 centipawn array."""
        ...


class MaterialEvaluator:
    """Deterministic baseline used to validate the final evaluator boundary."""

    def evaluate(self, board: chess.Board) -> int:
        """Return material balance in centipawns for the side to move."""
        white_score = 0
        black_score = 0
        for piece_type, value in PIECE_VALUES_CP.items():
            white_score += len(board.pieces(piece_type, chess.WHITE)) * value
            black_score += len(board.pieces(piece_type, chess.BLACK)) * value
        score = white_score - black_score
        return score if board.turn == chess.WHITE else -score

    def evaluate_batch(self, boards: Sequence[chess.Board]) -> np.ndarray:
        """Return material evaluations as a signed int32 array."""
        return np.asarray([self.evaluate(board) for board in boards], dtype=np.int32)


class TorchPositionEvaluator:
    """Inference evaluator backed by a validated PyTorch value network."""

    def __init__(self, model, *, device: str = "cpu") -> None:
        from chess_engine_nn.model import NnueValueNetwork

        if not isinstance(model, NnueValueNetwork):
            raise TypeError("TorchPositionEvaluator requires NnueValueNetwork")
        self.device = torch.device(device)
        self.model = model.to(self.device).eval().requires_grad_(False)
        from chess_engine_nn.encoding import FeatureEncoder

        self.encoder = FeatureEncoder()

    def evaluate(self, board: chess.Board) -> int:
        features = torch.from_numpy(self.encoder.encode_dense(board)).to(self.device)
        with torch.inference_mode():
            score = self.model.to_centipawns(self.model(features))
        return int(score.item())

    def evaluate_batch(self, boards: Sequence[chess.Board]) -> np.ndarray:
        if not boards:
            return np.asarray([], dtype=np.int32)
        features = torch.from_numpy(self.encoder.encode_batch(boards)).to(self.device)
        with torch.no_grad():
            scores = self.model.to_centipawns(self.model(features)).cpu().to(torch.int32).numpy()
        return scores


def load_evaluator(path: Path, *, device: str = "cpu") -> TorchPositionEvaluator:
    """Load and validate an inference-only model artifact."""
    from chess_engine_nn.artifacts import INFERENCE_ARTIFACT_VERSION, state_dict_sha256
    from chess_engine_nn.errors import ModelArtifactError
    from chess_engine_nn.model import ModelConfig, NnueValueNetwork

    try:
        payload = torch.load(path, map_location="cpu", weights_only=False)
    except (OSError, RuntimeError, ValueError) as error:
        raise ModelArtifactError(f"Unable to load model artifact {path}: {error}") from error
    if payload.get("artifact_type") != "inference_model":
        raise ModelArtifactError(f"Not an inference model: {path}")
    if payload.get("artifact_version") != INFERENCE_ARTIFACT_VERSION:
        raise ModelArtifactError(f"Unsupported artifact version: {payload.get('artifact_version')}")
    try:
        config = ModelConfig.from_dict(payload["model_config"])
        state = payload["model_state"]
        if state_dict_sha256(state) != payload["weights_sha256"]:
            raise ModelArtifactError("Model weight checksum does not match")
        model = NnueValueNetwork(config)
        model.load_state_dict(state)
    except (KeyError, TypeError, ValueError, RuntimeError) as error:
        if isinstance(error, ModelArtifactError):
            raise
        raise ModelArtifactError(f"Invalid model artifact metadata or weights: {error}") from error
    evaluator = TorchPositionEvaluator(model, device=device)
    for golden in payload.get("golden_positions", []):
        actual = evaluator.evaluate(chess.Board(golden["fen"]))
        if actual != golden["score_cp"]:
            raise ModelArtifactError(
                f"Golden inference mismatch: expected {golden['score_cp']}, received {actual}"
            )
    return evaluator
