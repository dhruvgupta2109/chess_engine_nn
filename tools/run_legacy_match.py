"""Run the frozen balanced-color match against the untouched legacy engine."""

import argparse
import contextlib
import hashlib
import io
import json
import os
import platform
import random
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import chess
import chess.pgn
import numpy as np
import torch

from chess_engine_nn.errors import ChessEngineError
from chess_engine_nn.evaluator import load_evaluator
from chess_engine_nn.reproducibility import seed_everything
from chess_engine_nn.search import SearchEngine
from chess_engine_nn.time_control import SearchLimits

LEGACY_ROOT = Path(__file__).resolve().parents[2]
if str(LEGACY_ROOT) not in sys.path:
    sys.path.insert(0, str(LEGACY_ROOT))

from board import Board as LegacyBoard  # noqa: E402
from search import Search as LegacySearch  # noqa: E402

MATCH_SCHEMA_VERSION = 1
DEFAULT_SEED = 20260713
DEFAULT_CYCLES = 13
DEFAULT_MAX_PLIES = 150
DEFAULT_DEPTH = 2


@dataclass(frozen=True)
class GameRecord:
    game_number: int
    cycle: int
    opening_id: str
    candidate_color: str
    result: str
    candidate_score: float
    termination: str
    plies: int
    candidate_nodes: int
    candidate_time_ms: int
    legacy_time_ms: int
    legacy_diagnostics_suppressed: int
    illegal_move: str | None
    final_fen: str


def legacy_board_from_python(board: chess.Board) -> LegacyBoard:
    """Translate a python-chess position and rule state into the legacy board."""
    legacy = LegacyBoard()
    legacy.state = [[0 for _ in range(8)] for _ in range(8)]
    for square, piece in board.piece_map().items():
        row = 7 - chess.square_rank(square)
        column = chess.square_file(square)
        legacy.state[row][column] = piece.piece_type if piece.color else -piece.piece_type
    if board.ep_square is not None:
        row = 7 - chess.square_rank(board.ep_square)
        column = chess.square_file(board.ep_square)
        legacy.state[row][column] = -7 if board.turn == chess.WHITE else 7

    white_kingside = board.has_kingside_castling_rights(chess.WHITE)
    white_queenside = board.has_queenside_castling_rights(chess.WHITE)
    black_kingside = board.has_kingside_castling_rights(chess.BLACK)
    black_queenside = board.has_queenside_castling_rights(chess.BLACK)
    legacy.white_king_moved = not (white_kingside or white_queenside)
    legacy.black_king_moved = not (black_kingside or black_queenside)
    legacy.white_rook_a_moved = not white_queenside
    legacy.white_rook_h_moved = not white_kingside
    legacy.black_rook_a_moved = not black_queenside
    legacy.black_rook_h_moved = not black_kingside
    return legacy


def python_move_from_legacy(move: tuple[int, int, int, int, int | None]) -> chess.Move:
    """Convert a legacy row/column move tuple to a python-chess move."""
    from_row, from_column, to_row, to_column, promotion = move
    from_square = chess.square(from_column, 7 - from_row)
    to_square = chess.square(to_column, 7 - to_row)
    return chess.Move(from_square, to_square, promotion=promotion)


def legacy_move(
    board: chess.Board,
    search: LegacySearch,
    *,
    depth: int,
) -> tuple[chess.Move | None, int, int]:
    """Search one legacy move while suppressing its per-move stdout diagnostics."""
    translated = legacy_board_from_python(board)
    diagnostics = io.StringIO()
    started = time.perf_counter_ns()
    with contextlib.redirect_stdout(diagnostics):
        _, move = search.minmax(translated, 1 if board.turn else -1, depth)
    elapsed_ms = round((time.perf_counter_ns() - started) / 1_000_000)
    converted = python_move_from_legacy(move) if move is not None else None
    return converted, elapsed_ms, len(diagnostics.getvalue().splitlines())


def load_openings(path: Path, *, limit: int | None = None) -> list[tuple[str, chess.Board]]:
    openings = []
    with path.open() as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                board, operations = chess.Board.from_epd(line)
            except ValueError as error:
                raise ValueError(f"Invalid opening EPD at {path}:{line_number}: {error}") from error
            opening_id = str(operations.get("id", f"opening-{line_number}"))
            if board.is_game_over(claim_draw=True):
                raise ValueError(f"Opening is terminal: {opening_id}")
            openings.append((opening_id, board))
            if limit is not None and len(openings) >= limit:
                break
    if not openings:
        raise ValueError(f"No openings found in {path}")
    return openings


def _candidate_score(result: str, candidate_color: chess.Color) -> float:
    if result == "1/2-1/2":
        return 0.5
    candidate_won = (result == "1-0") == (candidate_color == chess.WHITE)
    return 1.0 if candidate_won else 0.0


def play_game(
    opening: chess.Board,
    *,
    opening_id: str,
    cycle: int,
    game_number: int,
    candidate_color: chess.Color,
    evaluator,
    model_weights_sha256: str,
    max_plies: int,
    depth: int,
) -> tuple[GameRecord, chess.pgn.Game]:
    board = opening.copy(stack=True)
    candidate = SearchEngine(evaluator, hash_mb=64, max_quiescence_depth=8)
    legacy = LegacySearch()
    game = chess.pgn.Game()
    game.setup(opening)
    game.headers["Event"] = "Neural candidate vs imported legacy depth-2"
    game.headers["Round"] = str(game_number)
    game.headers["White"] = "NeuralCandidate" if candidate_color else "LegacyEngine"
    game.headers["Black"] = "LegacyEngine" if candidate_color else "NeuralCandidate"
    game.headers["Opening"] = opening_id
    game.headers["ModelWeightSHA256"] = model_weights_sha256
    node = game
    candidate_nodes = 0
    candidate_time_ms = 0
    legacy_time_ms = 0
    diagnostics_suppressed = 0
    illegal_move = None
    forced_result = None
    termination = "ply_cap"

    for _ in range(max_plies):
        outcome = board.outcome(claim_draw=True)
        if outcome is not None:
            forced_result = outcome.result()
            termination = outcome.termination.name.lower()
            break
        if board.turn == candidate_color:
            searched = candidate.search(board, SearchLimits(depth=depth))
            move = searched.best_move
            candidate_nodes += searched.nodes
            candidate_time_ms += searched.elapsed_ms
            if move not in board.legal_moves:
                illegal_move = move.uci() if move else "none"
                forced_result = "0-1" if candidate_color else "1-0"
                termination = "candidate_illegal_forfeit"
                break
        else:
            move, elapsed_ms, diagnostic_lines = legacy_move(board, legacy, depth=depth)
            legacy_time_ms += elapsed_ms
            diagnostics_suppressed += diagnostic_lines
            if move not in board.legal_moves:
                illegal_move = move.uci() if move else "none"
                forced_result = "1-0" if candidate_color else "0-1"
                termination = "legacy_illegal_forfeit"
                break
        board.push(move)
        node = node.add_variation(move)
    else:
        forced_result = "1/2-1/2"

    if forced_result is None:
        outcome = board.outcome(claim_draw=True)
        forced_result = outcome.result() if outcome else "1/2-1/2"
    game.headers["Result"] = forced_result
    game.headers["Termination"] = termination
    record = GameRecord(
        game_number=game_number,
        cycle=cycle,
        opening_id=opening_id,
        candidate_color="white" if candidate_color else "black",
        result=forced_result,
        candidate_score=_candidate_score(forced_result, candidate_color),
        termination=termination,
        plies=len(board.move_stack) - len(opening.move_stack),
        candidate_nodes=candidate_nodes,
        candidate_time_ms=candidate_time_ms,
        legacy_time_ms=legacy_time_ms,
        legacy_diagnostics_suppressed=diagnostics_suppressed,
        illegal_move=illegal_move,
        final_fen=board.fen(),
    )
    return record, game


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_match(
    model_path: Path,
    openings_path: Path,
    output_dir: Path,
    *,
    cycles: int = DEFAULT_CYCLES,
    opening_limit: int | None = None,
    max_plies: int = DEFAULT_MAX_PLIES,
    depth: int = DEFAULT_DEPTH,
    seed: int = DEFAULT_SEED,
) -> dict[str, object]:
    if cycles <= 0 or max_plies <= 0 or depth <= 0:
        raise ValueError("Match cycles, max plies, and depth must be positive")
    seed_everything(seed)
    evaluator = load_evaluator(model_path)
    artifact = torch.load(model_path, map_location="cpu", weights_only=False)
    weights_sha256 = artifact["weights_sha256"]
    openings = load_openings(openings_path, limit=opening_limit)
    schedule = []
    rng = random.Random(seed)
    for cycle in range(1, cycles + 1):
        ordered = list(openings)
        rng.shuffle(ordered)
        for opening_id, board in ordered:
            schedule.append((cycle, opening_id, board, chess.WHITE))
            schedule.append((cycle, opening_id, board, chess.BLACK))

    output_dir.mkdir(parents=True, exist_ok=True)
    pgn_path = output_dir / "games.pgn"
    pgn_temporary = output_dir / ".games.pgn.tmp"
    records = []
    started = time.perf_counter()
    with pgn_temporary.open("w") as pgn_output:
        for game_number, (cycle, opening_id, board, color) in enumerate(schedule, start=1):
            record, game = play_game(
                board,
                opening_id=opening_id,
                cycle=cycle,
                game_number=game_number,
                candidate_color=color,
                evaluator=evaluator,
                model_weights_sha256=weights_sha256,
                max_plies=max_plies,
                depth=depth,
            )
            records.append(record)
            print(game, file=pgn_output, end="\n\n")
            print(
                f"game {game_number}/{len(schedule)} {record.result} "
                f"candidate={record.candidate_color} {record.termination}",
                file=sys.stderr,
                flush=True,
            )
    os.replace(pgn_temporary, pgn_path)

    wins = sum(record.candidate_score == 1.0 for record in records)
    draws = sum(record.candidate_score == 0.5 for record in records)
    losses = sum(record.candidate_score == 0.0 for record in records)
    score = sum(record.candidate_score for record in records)
    elapsed = time.perf_counter() - started
    summary: dict[str, object] = {
        "match_schema_version": MATCH_SCHEMA_VERSION,
        "complete": True,
        "games": len(records),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "score": score,
        "score_percentage": 100 * score / len(records),
        "passed_above_50_percent": score / len(records) > 0.5,
        "candidate_white_games": sum(record.candidate_color == "white" for record in records),
        "candidate_black_games": sum(record.candidate_color == "black" for record in records),
        "legacy_forfeits": sum(
            record.termination == "legacy_illegal_forfeit" for record in records
        ),
        "candidate_forfeits": sum(
            record.termination == "candidate_illegal_forfeit" for record in records
        ),
        "ply_cap_draws": sum(record.termination == "ply_cap" for record in records),
        "elapsed_seconds": elapsed,
        "seed": seed,
        "cycles": cycles,
        "openings": len(openings),
        "depth": depth,
        "max_plies": max_plies,
        "model_path": str(model_path),
        "model_file_sha256": file_sha256(model_path),
        "model_weights_sha256": weights_sha256,
        "openings_path": str(openings_path),
        "openings_sha256": file_sha256(openings_path),
        "pgn_path": str(pgn_path),
        "pgn_sha256": file_sha256(pgn_path),
        "environment": {
            "python": platform.python_version(),
            "python_chess": chess.__version__,
            "numpy": np.__version__,
            "torch": torch.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "records": [asdict(record) for record in records],
    }
    report_path = output_dir / "summary.json"
    temporary = output_dir / ".summary.json.tmp"
    temporary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, report_path)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument(
        "--openings",
        type=Path,
        default=Path("tests/positions/baseline_openings.epd"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycles", type=int, default=DEFAULT_CYCLES)
    parser.add_argument("--opening-limit", type=int)
    parser.add_argument("--max-plies", type=int, default=DEFAULT_MAX_PLIES)
    parser.add_argument("--depth", type=int, default=DEFAULT_DEPTH)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = run_match(
            args.model,
            args.openings,
            args.output,
            cycles=args.cycles,
            opening_limit=args.opening_limit,
            max_plies=args.max_plies,
            depth=args.depth,
            seed=args.seed,
        )
    except (OSError, ValueError, KeyError, RuntimeError, ChessEngineError) as error:
        print(f"match error: {error}", file=sys.stderr)
        return 2
    concise = {key: value for key, value in summary.items() if key != "records"}
    print(json.dumps(concise, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
