import json
from pathlib import Path

import chess

from chess_engine_nn.evaluator import MaterialEvaluator
from chess_engine_nn.search import SearchEngine
from chess_engine_nn.time_control import SearchLimits


def test_maintained_tactical_suite() -> None:
    path = Path(__file__).parent / "positions" / "search_tactics.json"
    for case in json.loads(path.read_text()):
        board = chess.Board(case["fen"])
        result = SearchEngine(MaterialEvaluator(), hash_mb=1).search(
            board, SearchLimits(depth=case["depth"])
        )
        assert result.best_move == chess.Move.from_uci(case["best_move"]), case["id"]
