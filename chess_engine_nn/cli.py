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
from chess_engine_nn.evaluator import MaterialEvaluator, load_evaluator
from chess_engine_nn.model import ModelConfig, NnueValueNetwork
from chess_engine_nn.reproducibility import seed_everything
from chess_engine_nn.search import SearchEngine
from chess_engine_nn.time_control import SearchLimits
from chess_engine_nn.training.dataset import JsonlPositionDataset
from chess_engine_nn.training.export import export_checkpoint
from chess_engine_nn.training.train import (
    evaluate_dataset,
    load_checkpoint,
    resolve_device,
    train_model,
)


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
    train = subparsers.add_parser("train", help="train or resume the neural evaluator")
    train.add_argument("--dataset", type=Path, help="dataset run directory")
    train.add_argument("--output", type=Path, help="checkpoint output directory")
    train.add_argument("--resume", type=Path, help="last checkpoint to resume")
    train.add_argument("--json", action="store_true", help="emit one JSON result")
    evaluate = subparsers.add_parser("evaluate-model", help="evaluate a checkpoint split")
    evaluate.add_argument("--dataset", type=Path, help="dataset run directory")
    evaluate.add_argument("--checkpoint", type=Path, required=True)
    evaluate.add_argument("--split", choices=("validation", "test"), default="validation")
    evaluate.add_argument("--json", action="store_true", help="emit one JSON result")
    export = subparsers.add_parser("export", help="export an inference-only model")
    export.add_argument("--checkpoint", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--json", action="store_true", help="emit one JSON result")
    search = subparsers.add_parser(
        "search", help="search one FEN with neural or material evaluation"
    )
    search.add_argument("--fen", default=chess.STARTING_FEN)
    search.add_argument("--model", type=Path, help="inference-only model artifact")
    search.add_argument("--depth", type=int)
    search.add_argument("--nodes", type=int)
    search.add_argument("--movetime", type=int, help="move time in milliseconds")
    search.add_argument("--json", action="store_true", help="emit one JSON result")
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
        if args.command == "train":
            dataset = args.dataset or config.paths.data_dir / "processed" / config.data.run_name
            output = (
                args.output
                or config.paths.artifacts_dir / "checkpoints" / config.data.run_name
            )
            trained = train_model(
                dataset, output, config.training, seed=config.runtime.seed, resume=args.resume
            )
            result = {
                "ok": True,
                "best_checkpoint": str(trained.best_checkpoint),
                "last_checkpoint": str(trained.last_checkpoint),
                "best_epoch": trained.best_epoch,
                "epochs_completed": trained.epochs_completed,
                "best_validation_loss": trained.best_validation_loss,
            }
            if args.json:
                print(json.dumps(result, sort_keys=True))
            else:
                print(f"Training complete: {trained.epochs_completed} epochs")
                print(f"Best checkpoint: {trained.best_checkpoint}")
                print(f"Best validation loss: {trained.best_validation_loss:.6f}")
            return 0
        if args.command == "evaluate-model":
            dataset_dir = (
                args.dataset or config.paths.data_dir / "processed" / config.data.run_name
            )
            checkpoint = load_checkpoint(args.checkpoint)
            model_config = ModelConfig.from_dict(checkpoint["model_config"])
            model = NnueValueNetwork(model_config)
            model.load_state_dict(checkpoint["model_state"])
            device = resolve_device(config.training.device)
            model.to(device)
            dataset = JsonlPositionDataset(
                dataset_dir, args.split, target_cap_cp=model_config.target_cap_cp
            )
            loss, metrics = evaluate_dataset(
                model,
                dataset,
                batch_size=config.training.batch_size,
                device=device,
                huber_delta=config.training.huber_delta,
                draw_band_cp=config.training.draw_band_cp,
            )
            result = {"ok": True, "split": args.split, "loss": loss, **metrics.to_dict()}
            print(json.dumps(result, sort_keys=True) if args.json else json.dumps(result, indent=2))
            return 0
        if args.command == "export":
            exported = export_checkpoint(args.checkpoint, args.output)
            result = {"ok": True, "model": str(exported)}
            message = (
                json.dumps(result, sort_keys=True)
                if args.json
                else f"Exported model: {exported}"
            )
            print(message)
            return 0
        if args.command == "search":
            try:
                board = chess.Board(args.fen)
            except ValueError as error:
                raise ChessEngineError(f"Invalid search FEN: {error}") from error
            model_path = args.model or config.runtime.model_path
            evaluator = load_evaluator(model_path) if model_path else MaterialEvaluator()
            engine = SearchEngine(
                evaluator,
                hash_mb=config.runtime.hash_mb,
                max_quiescence_depth=config.search.max_quiescence_depth,
                aspiration_window_cp=config.search.aspiration_window_cp,
            )
            limits = SearchLimits(
                depth=args.depth
                if args.depth is not None
                else None
                if args.nodes is not None or args.movetime is not None
                else config.search.default_depth,
                nodes=args.nodes,
                move_time_ms=args.movetime,
            )
            searched = engine.search(board, limits)
            result = {
                "ok": True,
                "best_move": searched.best_move.uci() if searched.best_move else None,
                "score_cp": searched.score_cp,
                "mate_in": searched.mate_in,
                "depth": searched.depth,
                "seldepth": searched.seldepth,
                "nodes": searched.nodes,
                "nps": searched.nps,
                "elapsed_ms": searched.elapsed_ms,
                "completed": searched.completed,
                "transposition_hits": searched.transposition_hits,
                "pv": [move.uci() for move in searched.principal_variation],
            }
            print(json.dumps(result, sort_keys=True) if args.json else json.dumps(result, indent=2))
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
