import threading
import time

import chess

from chess_engine_nn.evaluator import MaterialEvaluator
from chess_engine_nn.search import (
    MATE_SCORE,
    SearchEngine,
    score_from_transposition,
    score_to_transposition,
)
from chess_engine_nn.time_control import SearchLimits


class CountingEvaluator(MaterialEvaluator):
    def __init__(self, delay: float = 0.0) -> None:
        self.calls = 0
        self.delay = delay

    def evaluate(self, board: chess.Board) -> int:
        self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        return super().evaluate(board)


def test_transposition_mate_scores_preserve_root_distance() -> None:
    score = MATE_SCORE - 5
    stored = score_to_transposition(score, 3)
    assert score_from_transposition(stored, 3) == score
    assert score_from_transposition(stored, 1) == score + 2


def test_terminal_mate_stalemate_and_fifty_move_draw() -> None:
    engine = SearchEngine(MaterialEvaluator(), hash_mb=1)
    mate = chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
    stalemate = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    fifty = chess.Board("7k/8/8/8/8/8/Q7/K7 w - - 100 51")
    mate_result = engine.search(mate, SearchLimits(depth=2))
    assert mate_result.best_move is None
    assert mate_result.mate_in == 0
    assert engine.search(stalemate, SearchLimits(depth=2)).score_cp == 0
    assert engine.search(fifty, SearchLimits(depth=2)).score_cp == 0


def test_threefold_history_is_scored_as_draw_and_preserved() -> None:
    board = chess.Board()
    for move in ("g1f3", "g8f6", "f3g1", "f6g8") * 2:
        board.push_uci(move)
    before = list(board.move_stack)
    result = SearchEngine(MaterialEvaluator(), hash_mb=1).search(board, SearchLimits(depth=2))
    assert result.score_cp == 0
    assert result.best_move is None
    assert board.move_stack == before


def test_search_returns_legal_move_and_preserves_board_history() -> None:
    board = chess.Board()
    board.push_uci("e2e4")
    before_fen = board.fen()
    before_stack = list(board.move_stack)
    result = SearchEngine(MaterialEvaluator(), hash_mb=1).search(board, SearchLimits(depth=2))
    assert result.best_move in board.legal_moves
    assert result.depth == 2
    assert result.completed
    assert board.fen() == before_fen
    assert board.move_stack == before_stack


def test_search_finds_mate_in_one() -> None:
    board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1")
    result = SearchEngine(MaterialEvaluator(), hash_mb=1).search(board, SearchLimits(depth=2))
    assert result.best_move is not None
    board.push(result.best_move)
    assert board.is_checkmate()
    assert result.mate_in == 1


def test_capture_and_quiescence_use_evaluator() -> None:
    board = chess.Board("7k/8/8/8/8/8/q7/R6K w - - 0 1")
    evaluator = CountingEvaluator()
    result = SearchEngine(evaluator, hash_mb=1).search(board, SearchLimits(depth=1))
    assert result.best_move == chess.Move.from_uci("a1a2")
    assert evaluator.calls > 0
    assert result.seldepth >= 1


def test_node_and_external_stop_return_deterministic_fallback() -> None:
    board = chess.Board()
    engine = SearchEngine(MaterialEvaluator(), hash_mb=1)
    by_nodes = engine.search(board, SearchLimits(nodes=1))
    assert by_nodes.best_move in board.legal_moves
    assert not by_nodes.completed
    assert by_nodes.nodes <= 1

    stop = threading.Event()
    stop.set()
    externally = engine.search(board, SearchLimits(depth=5), stop_event=stop)
    assert externally.best_move == by_nodes.best_move
    assert not externally.completed


def test_time_limit_and_observer_report_completed_iterations() -> None:
    board = chess.Board()
    reports = []
    engine = SearchEngine(CountingEvaluator(delay=0.002), hash_mb=1)
    result = engine.search(board, SearchLimits(move_time_ms=30), observer=reports.append)
    assert result.best_move in board.legal_moves
    assert result.elapsed_ms <= 100
    assert [report.depth for report in reports] == sorted(report.depth for report in reports)
    assert all(report.completed for report in reports)
