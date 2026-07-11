import chess
import numpy as np

from chess_engine_nn.evaluator import MaterialEvaluator, PositionEvaluator


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
