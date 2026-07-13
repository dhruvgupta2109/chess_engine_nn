"""Reproducible Phase 6 CPU component profiles and search ablations."""

import argparse
import json
import platform
import statistics
import sys
import time
from collections.abc import Callable
from pathlib import Path

import chess
import numpy as np
import torch

from chess_engine_nn.artifacts import state_dict_sha256
from chess_engine_nn.encoding import FeatureEncoder
from chess_engine_nn.evaluator import MaterialEvaluator, TorchPositionEvaluator
from chess_engine_nn.model import ModelConfig, NnueValueNetwork
from chess_engine_nn.reproducibility import seed_everything
from chess_engine_nn.search import INFINITY, SearchEngine
from chess_engine_nn.time_control import SearchLimits
from chess_engine_nn.transposition import TranspositionEntry, TranspositionTable, position_hash

BENCHMARK_SCHEMA_VERSION = 1
SEED = 20260713
MIDDLEGAME_FEN = "r1bq1rk1/pp2bppp/2n1pn2/2pp4/3P4/2PB1N2/PPQ2PPP/R1B1R1K1 w - - 2 11"
TACTICAL_FEN = "7k/8/8/8/8/8/q7/R6K w - - 0 1"


class LexicalMoveOrderingSearch(SearchEngine):
    """Ablation which removes all search-informed move ordering."""

    def _ordered_moves(self, board, moves, table_move, ply):
        return sorted(moves, key=lambda move: move.uci())


class NullTranspositionTable:
    """Ablation implementing the table interface without retaining entries."""

    def probe(self, key: int) -> None:
        return None

    def store(self, entry: TranspositionEntry) -> None:
        return None

    def clear(self) -> None:
        return None


def _rate(operation: Callable[[], object], *, iterations: int, repeats: int) -> int:
    for _ in range(min(iterations, 200)):
        operation()
    rates = []
    for _ in range(repeats):
        started = time.perf_counter_ns()
        for _ in range(iterations):
            operation()
        elapsed_ns = time.perf_counter_ns() - started
        rates.append(iterations * 1_000_000_000 / elapsed_ns)
    return round(statistics.median(rates))


def _search(
    evaluator,
    board: chess.Board,
    *,
    depth: int,
    variant: str = "baseline",
) -> dict[str, object]:
    search_type = LexicalMoveOrderingSearch if variant == "lexical_ordering" else SearchEngine
    engine = search_type(
        evaluator,
        hash_mb=16,
        max_quiescence_depth=0 if variant == "no_quiescence_extension" else 6,
        aspiration_window_cp=INFINITY if variant == "full_window" else 50,
    )
    if variant == "no_transposition_table":
        engine.table = NullTranspositionTable()  # type: ignore[assignment]
    started = time.perf_counter_ns()
    result = engine.search(board, SearchLimits(depth=depth))
    elapsed_ns = time.perf_counter_ns() - started
    return {
        "variant": variant,
        "depth": result.depth,
        "nodes": result.nodes,
        "elapsed_ms": round(elapsed_ns / 1_000_000, 3),
        "nps": round(result.nodes * 1_000_000_000 / max(1, elapsed_ns)),
        "transposition_hits": result.transposition_hits,
        "best_move": result.best_move.uci() if result.best_move else None,
        "score_cp": result.score_cp,
        "mate_in": result.mate_in,
    }


def _tactical_control() -> dict[str, object]:
    cases_path = Path(__file__).parents[1] / "tests" / "positions" / "search_tactics.json"
    cases = json.loads(cases_path.read_text())
    passed = []
    for case in cases:
        board = chess.Board(case["fen"])
        result = SearchEngine(MaterialEvaluator(), hash_mb=1).search(
            board, SearchLimits(depth=case["depth"])
        )
        if result.best_move == chess.Move.from_uci(case["best_move"]):
            passed.append(case["id"])
    return {"passed": len(passed), "total": len(cases), "case_ids": passed}


def benchmark(*, micro_iterations: int, repeats: int, search_depth: int) -> dict[str, object]:
    seed_everything(SEED)
    config = ModelConfig()
    model = NnueValueNetwork(config)
    evaluator = TorchPositionEvaluator(model)
    encoder = FeatureEncoder()
    board = chess.Board(MIDDLEGAME_FEN)
    move = next(iter(board.legal_moves))
    table = TranspositionTable(16)
    key = position_hash(board)

    def push_pop() -> None:
        board.push(move)
        board.pop()

    microbenchmarks = {
        "active_feature_encodings_per_second": _rate(
            lambda: encoder.active_indices(board),
            iterations=micro_iterations,
            repeats=repeats,
        ),
        "dense_feature_encodings_per_second": _rate(
            lambda: encoder.encode_dense(board),
            iterations=micro_iterations,
            repeats=repeats,
        ),
        "neural_evaluations_per_second": _rate(
            lambda: evaluator.evaluate(board),
            iterations=micro_iterations,
            repeats=repeats,
        ),
        "legal_move_lists_per_second": _rate(
            lambda: list(board.legal_moves),
            iterations=micro_iterations,
            repeats=repeats,
        ),
        "push_pop_pairs_per_second": _rate(
            push_pop,
            iterations=micro_iterations,
            repeats=repeats,
        ),
        "position_hashes_per_second": _rate(
            lambda: position_hash(board),
            iterations=micro_iterations,
            repeats=repeats,
        ),
        "transposition_probes_per_second": _rate(
            lambda: table.probe(key),
            iterations=micro_iterations,
            repeats=repeats,
        ),
    }

    positions = {
        "start": chess.Board(),
        "middlegame": chess.Board(MIDDLEGAME_FEN),
        "tactical": chess.Board(TACTICAL_FEN),
    }
    searches = {
        name: _search(evaluator, candidate, depth=search_depth)
        for name, candidate in positions.items()
    }
    ablations = [
        _search(evaluator, chess.Board(MIDDLEGAME_FEN), depth=search_depth, variant=variant)
        for variant in (
            "baseline",
            "lexical_ordering",
            "no_transposition_table",
            "no_quiescence_extension",
            "full_window",
        )
    ]
    return {
        "benchmark_schema_version": BENCHMARK_SCHEMA_VERSION,
        "command": (
            "python3 tools/benchmark_phase6.py "
            f"--micro-iterations {micro_iterations} --repeats {repeats} "
            f"--search-depth {search_depth}"
        ),
        "environment": {
            "python": platform.python_version(),
            "python_chess": chess.__version__,
            "numpy": np.__version__,
            "torch": torch.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor() or "unknown",
            "torch_threads": torch.get_num_threads(),
        },
        "model": {
            "description": "untrained deterministic production-shaped architecture",
            "config": config.to_dict(),
            "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
            "weights_sha256": state_dict_sha256(model.state_dict()),
            "seed": SEED,
        },
        "microbenchmarks": microbenchmarks,
        "searches": searches,
        "middlegame_ablations": ablations,
        "tactical_control": _tactical_control(),
        "interpretation_limits": [
            "Untrained weights make this a mechanics/performance benchmark, not strength evidence.",
            "Timing varies with system load; compare medians on the same hardware and versions.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--micro-iterations", type=int, default=2_000)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--search-depth", type=int, default=3)
    parser.add_argument("--output", type=Path, help="optional JSON report path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.micro_iterations <= 0 or args.repeats <= 0 or args.search_depth <= 0:
        print("benchmark counts and depth must be positive", file=sys.stderr)
        return 2
    report = benchmark(
        micro_iterations=args.micro_iterations,
        repeats=args.repeats,
        search_depth=args.search_depth,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(rendered)
        temporary.replace(args.output)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
