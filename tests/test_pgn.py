from pathlib import Path

import chess
import chess.pgn

from chess_engine_nn.data.pgn import PgnStats, stable_game_id, stream_sampled_positions

FIXTURE = Path(__file__).parent / "fixtures" / "games.pgn"


def test_streaming_sampling_is_deterministic_and_non_terminal() -> None:
    first_stats = PgnStats()
    first = list(
        stream_sampled_positions(
            FIXTURE, every_n_plies=2, min_ply=2, max_positions_per_game=3, stats=first_stats
        )
    )
    second = list(
        stream_sampled_positions(FIXTURE, every_n_plies=2, min_ply=2, max_positions_per_game=3)
    )
    assert first == second
    assert len(first) == 6
    assert first_stats.games_read == 2
    assert first_stats.games_with_errors == 0
    assert all(not chess.Board(candidate.fen).is_game_over() for candidate in first)
    assert len({candidate.game_id for candidate in first}) == 2


def test_stable_game_id_changes_with_movetext() -> None:
    with FIXTURE.open() as file:
        first = chess.pgn.read_game(file)
        second = chess.pgn.read_game(file)
    assert first is not None and second is not None
    assert stable_game_id(first) != stable_game_id(second)


def test_malformed_game_is_counted_and_skipped(tmp_path: Path) -> None:
    path = tmp_path / "bad.pgn"
    path.write_text(
        '[Event "Bad"]\n[Result "*"]\n\n'
        "1. e4 e5 2. Nf3 Nc6 3. Nxe5 Nxe5 4. Nxe5 *\n"
    )
    stats = PgnStats()
    assert list(stream_sampled_positions(path, min_ply=1, stats=stats)) == []
    assert stats.games_read == 1
    assert stats.games_with_errors == 1
