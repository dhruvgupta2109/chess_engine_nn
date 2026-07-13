"""Headless developer CLI for the engine foundations."""

import argparse
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

import chess
import numpy

from chess_engine_nn import __version__
from chess_engine_nn.config import AppConfig, load_config
from chess_engine_nn.data.generate import generate_dataset
from chess_engine_nn.data.label import StockfishTeacher
from chess_engine_nn.encoding import FEATURE_COUNT, FEATURE_SCHEMA_VERSION
from chess_engine_nn.errors import ChessEngineError
from chess_engine_nn.reproducibility import seed_everything


def _path_report(path: Path) -> dict[str, object]:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return {
        "path": str(path),
        "exists": path.exists(),
        "writable": candidate.exists() and os.access(candidate, os.W_OK),
    }


def _doctor_report(config: AppConfig) -> dict[str, object]:
    seed_state = seed_everything(config.runtime.seed)
    configured_stockfish = config.paths.stockfish_path
    stockfish = (
        str(configured_stockfish)
        if configured_stockfish is not None and configured_stockfish.is_file()
        else shutil.which("stockfish")
    )
    torch_spec = importlib.util.find_spec("torch")
    return {
        "ok": True,
        "package_version": __version__,
        "python": sys.version.split()[0],
        "python_chess": chess.__version__,
        "numpy": numpy.__version__,
        "torch_available": torch_spec is not None,
        "stockfish": stockfish,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_count": FEATURE_COUNT,
        "data_dir": str(config.paths.data_dir),
        "artifacts_dir": str(config.paths.artifacts_dir),
        "directories": {
            "data": _path_report(config.paths.data_dir),
            "artifacts": _path_report(config.paths.artifacts_dir),
        },
        "runtime": {
            "seed": config.runtime.seed,
            "hash_mb": config.runtime.hash_mb,
            "threads": config.runtime.threads,
            "model_path": str(config.runtime.model_path) if config.runtime.model_path else None,
        },
        "seed_state": {
            "seed": seed_state.seed,
            "python_hash_seed": seed_state.python_hash_seed,
            "torch_seeded": seed_state.torch_seeded,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chess-engine-nn", description=__doc__)
    parser.add_argument("--config", type=Path, help="TOML configuration file")
    subparsers = parser.add_subparsers(dest="command", required=True)
    doctor = subparsers.add_parser("doctor", help="validate the local foundation environment")
    doctor.add_argument("--json", action="store_true", help="emit one JSON result")
    generate = subparsers.add_parser("generate-data", help="label sampled PGN positions")
    generate.add_argument("--pgn", type=Path, nargs="+", required=True, help="input PGN files")
    generate.add_argument("--output", type=Path, help="dataset run directory")
    generate.add_argument("--json", action="store_true", help="emit one JSON result")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == "doctor":
            report = _doctor_report(config)
            if args.json:
                print(json.dumps(report, sort_keys=True))
            else:
                print("Neural chess engine foundation: OK")
                print(f"Python: {report['python']}")
                print(f"python-chess: {report['python_chess']}")
                print(f"NumPy: {report['numpy']}")
                print(f"PyTorch available: {report['torch_available']}")
                print(f"Stockfish: {report['stockfish'] or 'not found (optional in Phase 1)'}")
                print(f"Feature schema: v{FEATURE_SCHEMA_VERSION} ({FEATURE_COUNT} features)")
            return 0
        if args.command == "generate-data":
            configured = config.stockfish.executable or config.paths.stockfish_path
            found = shutil.which("stockfish")
            executable = configured or (Path(found) if found else None)
            if executable is None or not executable.is_file():
                raise ChessEngineError(
                    "Stockfish was not found; set stockfish.executable or add it to PATH"
                )
            output = args.output or config.paths.data_dir / "processed" / config.data.run_name
            with StockfishTeacher(
                executable,
                depth=config.stockfish.depth,
                nodes=config.stockfish.nodes,
                time_ms=config.stockfish.time_ms,
                hash_mb=config.stockfish.hash_mb,
                threads=config.stockfish.threads,
                mate_score_cp=config.stockfish.mate_score_cp,
            ) as teacher:
                manifest = generate_dataset(
                    args.pgn,
                    output,
                    teacher,
                    seed=config.runtime.seed,
                    train_ratio=config.data.train_ratio,
                    validation_ratio=config.data.validation_ratio,
                    test_ratio=config.data.test_ratio,
                    every_n_plies=config.data.every_n_plies,
                    min_ply=config.data.min_ply,
                    max_positions_per_game=config.data.max_positions_per_game,
                )
            result = {
                "ok": True,
                "manifest": str(output / "manifest.json"),
                "run_id": manifest.run_id,
                "complete": manifest.complete,
                "counts": manifest.counts,
                "shards": len(manifest.shards),
            }
            if args.json:
                print(json.dumps(result, sort_keys=True))
            else:
                print(f"Dataset generation complete: {result['manifest']}")
                total = sum(
                    manifest.counts.get(key, 0) for key in ("train", "validation", "test")
                )
                print(f"Records: {total}")
                print(f"Shards: {len(manifest.shards)}")
            return 0
    except ChessEngineError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
