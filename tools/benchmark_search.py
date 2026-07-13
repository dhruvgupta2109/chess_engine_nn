"""Measure Phase 4 neural evaluation throughput and search NPS."""

import json
import time

import chess

from chess_engine_nn.evaluator import TorchPositionEvaluator
from chess_engine_nn.model import NnueValueNetwork
from chess_engine_nn.reproducibility import seed_everything
from chess_engine_nn.search import SearchEngine
from chess_engine_nn.time_control import SearchLimits


def main() -> int:
    seed_everything(20260713)
    evaluator = TorchPositionEvaluator(NnueValueNetwork())
    board = chess.Board()
    samples = 1_000
    started = time.perf_counter()
    for _ in range(samples):
        evaluator.evaluate(board)
    evaluation_seconds = time.perf_counter() - started

    engine = SearchEngine(evaluator, hash_mb=16, max_quiescence_depth=6)
    result = engine.search(board, SearchLimits(depth=2))
    print(
        json.dumps(
            {
                "evaluator_positions": samples,
                "evaluator_positions_per_second": round(samples / evaluation_seconds),
                "search_depth": result.depth,
                "search_nodes": result.nodes,
                "search_elapsed_ms": result.elapsed_ms,
                "search_nps": result.nps,
                "best_move": result.best_move.uci() if result.best_move else None,
                "model": "untrained deterministic architecture baseline",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
