"""Streaming PGN parsing and deterministic position sampling."""

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import chess
import chess.pgn


@dataclass(frozen=True)
class CandidatePosition:
    fen: str
    game_id: str
    ply: int
    result: str


@dataclass
class PgnStats:
    games_read: int = 0
    games_with_errors: int = 0
    positions_considered: int = 0
    positions_sampled: int = 0
    terminal_skipped: int = 0


def stable_game_id(game: chess.pgn.Game) -> str:
    """Hash normalized headers and mainline UCI movetext."""
    headers = {key: game.headers.get(key, "") for key in sorted(game.headers)}
    moves = [move.uci() for move in game.mainline_moves()]
    canonical = json.dumps(
        {"headers": headers, "moves": moves}, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def stream_sampled_positions(
    path: Path,
    *,
    every_n_plies: int = 4,
    min_ply: int = 8,
    max_positions_per_game: int = 32,
    stats: PgnStats | None = None,
) -> Iterator[CandidatePosition]:
    """Yield sampled, valid, non-terminal positions without loading the corpus."""
    if every_n_plies <= 0:
        raise ValueError("every_n_plies must be positive")
    if min_ply < 0 or max_positions_per_game <= 0:
        raise ValueError("min_ply must be non-negative and max positions positive")

    counters = stats if stats is not None else PgnStats()
    with path.open(encoding="utf-8", errors="replace") as pgn_file:
        while True:
            game = chess.pgn.read_game(pgn_file)
            if game is None:
                break
            counters.games_read += 1
            if game.errors:
                counters.games_with_errors += 1
                continue

            game_id = stable_game_id(game)
            result = game.headers.get("Result", "*")
            board = game.board()
            sampled = 0
            for ply, move in enumerate(game.mainline_moves(), start=1):
                if move not in board.legal_moves:
                    counters.games_with_errors += 1
                    break
                board.push(move)
                if ply < min_ply or (ply - min_ply) % every_n_plies != 0:
                    continue
                counters.positions_considered += 1
                if board.is_game_over(claim_draw=True):
                    counters.terminal_skipped += 1
                    continue
                yield CandidatePosition(
                    fen=board.fen(en_passant="fen"), game_id=game_id, ply=ply, result=result
                )
                counters.positions_sampled += 1
                sampled += 1
                if sampled >= max_positions_per_game:
                    break
