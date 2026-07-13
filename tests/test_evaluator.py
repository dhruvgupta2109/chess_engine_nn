import chess
import numpy as np
import torch

from chess_engine_nn.evaluator import MaterialEvaluator, PositionEvaluator, TorchPositionEvaluator
from chess_engine_nn.model import ModelConfig, NnueValueNetwork


def test_material_evaluator_uses_side_to_move_perspective() -> None:
    evaluator = MaterialEvaluator()
    white_to_move = chess.Board("7k/8/8/8/8/8/Q7/K7 w - - 0 1")
    black_to_move = chess.Board("7k/8/8/8/8/8/Q7/K7 b - - 0 1")

    assert evaluator.evaluate(white_to_move) == 900
    assert evaluator.evaluate(black_to_move) == -900


def test_material_evaluator_is_protocol_compatible_and_batches() -> None:
    evaluator = MaterialEvaluator()
    assert isinstance(evaluator, PositionEvaluator)
    scores = evaluator.evaluate_batch([chess.Board(), chess.Board()])
    assert np.array_equal(scores, np.array([0, 0], dtype=np.int32))
    assert scores.dtype == np.int32


def test_torch_single_position_fast_path_matches_batch_exactly() -> None:
    torch.manual_seed(20260713)
    model = NnueValueNetwork(ModelConfig(accumulator_dim=16, hidden_dim=8, target_cap_cp=1_000))
    evaluator = TorchPositionEvaluator(model)
    boards = [
        chess.Board(),
        chess.Board("7k/8/8/8/8/8/Q7/K7 w - - 0 1"),
        chess.Board("7k/8/8/8/8/8/Q7/K7 b - - 0 1"),
    ]

    singles = np.asarray([evaluator.evaluate(board) for board in boards], dtype=np.int32)

    assert np.array_equal(singles, evaluator.evaluate_batch(boards))
    assert all(not parameter.requires_grad for parameter in evaluator.model.parameters())
