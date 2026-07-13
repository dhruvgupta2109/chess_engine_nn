import io
import time
from pathlib import Path

import chess
import numpy as np

from chess_engine_nn.evaluator import MaterialEvaluator
from chess_engine_nn.transposition import BoundType, TranspositionEntry
from chess_engine_nn.uci import UCIEngine


class SlowMaterialEvaluator(MaterialEvaluator):
    def __init__(self, delay: float = 0.003) -> None:
        self.delay = delay

    def evaluate(self, board: chess.Board) -> int:
        time.sleep(self.delay)
        return super().evaluate(board)

    def evaluate_batch(self, boards) -> np.ndarray:
        return np.asarray([self.evaluate(board) for board in boards], dtype=np.int32)


def adapter(*, evaluator=None, evaluator_loader=None):
    stdout = io.StringIO()
    stderr = io.StringIO()
    arguments = {
        "evaluator": evaluator,
        "stdout": stdout,
        "stderr": stderr,
        "hash_mb": 1,
    }
    if evaluator_loader is not None:
        arguments["evaluator_loader"] = evaluator_loader
    return UCIEngine(**arguments), stdout, stderr


def test_uci_handshake_and_readiness_require_an_evaluator() -> None:
    engine, stdout, stderr = adapter()
    engine.handle_command("uci")
    engine.handle_command("isready")
    lines = stdout.getvalue().splitlines()
    assert lines[0].startswith("id name Chess Engine NN")
    assert "option name ModelPath type string default" in lines
    assert "option name Hash type spin default 1 min 1 max 1048576" in lines
    assert "option name Threads type spin default 1 min 1 max 1" in lines
    assert lines[-1] == "uciok"
    assert "readyok" not in lines
    assert "not ready" in stderr.getvalue()


def test_run_processes_a_protocol_transcript_until_quit() -> None:
    stdin = io.StringIO("uci\nisready\nposition startpos moves e2e4\nquit\n")
    stdout = io.StringIO()
    stderr = io.StringIO()
    engine = UCIEngine(
        evaluator=MaterialEvaluator(),
        hash_mb=1,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )
    assert engine.run() == 0
    lines = stdout.getvalue().splitlines()
    assert "uciok" in lines
    assert lines[-1] == "readyok"
    assert engine.board.peek() == chess.Move.from_uci("e2e4")
    assert stderr.getvalue() == ""


def test_position_and_depth_search_emit_standard_info_and_legal_bestmove() -> None:
    engine, stdout, stderr = adapter(evaluator=MaterialEvaluator())
    engine.handle_command("position startpos moves e2e4 e7e5")
    expected = engine.board.copy(stack=True)
    engine.handle_command("go depth 1")
    assert engine.wait_for_search(2)

    lines = stdout.getvalue().splitlines()
    info = next(line for line in lines if line.startswith("info "))
    for field in ("depth", "seldepth", "score cp", "nodes", "nps", "time", "pv"):
        assert field in info
    bestmove = next(line.split()[1] for line in lines if line.startswith("bestmove "))
    assert chess.Move.from_uci(bestmove) in expected.legal_moves
    assert stderr.getvalue() == ""


def test_go_parser_supports_all_required_clock_and_direct_limits() -> None:
    limits = UCIEngine._parse_go(
        "depth 4 nodes 500 movetime 100 wtime 30000 btime 20000 "
        "winc 1000 binc 500 movestogo 12".split()
    )
    assert limits.depth == 4
    assert limits.nodes == 500
    assert limits.move_time_ms == 100
    assert limits.white_time_ms == 30_000
    assert limits.black_time_ms == 20_000
    assert limits.white_increment_ms == 1_000
    assert limits.black_increment_ms == 500
    assert limits.moves_to_go == 12


def test_stop_is_responsive_and_still_returns_a_legal_move() -> None:
    engine, stdout, stderr = adapter(evaluator=SlowMaterialEvaluator())
    board = engine.board.copy()
    engine.handle_command("go depth 20")
    started = time.monotonic()
    engine.handle_command("stop")
    engine.handle_command("stop")
    assert engine.wait_for_search(1)
    engine.handle_command("stop")
    assert time.monotonic() - started < 0.25
    bestmove = [line for line in stdout.getvalue().splitlines() if line.startswith("bestmove ")]
    assert len(bestmove) == 1
    assert chess.Move.from_uci(bestmove[0].split()[1]) in board.legal_moves
    assert stderr.getvalue() == ""


def test_quit_cancels_and_joins_an_active_worker() -> None:
    engine, stdout, stderr = adapter(evaluator=SlowMaterialEvaluator())
    engine.handle_command("go depth 20")
    started = time.monotonic()
    assert engine.handle_command("quit") is False
    assert time.monotonic() - started < 0.25
    assert not engine.searching
    assert "bestmove 0000" not in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_movetime_uses_search_time_control() -> None:
    engine, stdout, stderr = adapter(evaluator=SlowMaterialEvaluator())
    started = time.monotonic()
    engine.handle_command("go movetime 30")
    assert engine.wait_for_search(1)
    elapsed = time.monotonic() - started
    assert 0.015 <= elapsed <= 0.08
    assert "bestmove " in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_failed_model_reload_retains_previous_valid_evaluator() -> None:
    original = MaterialEvaluator()
    replacement = SlowMaterialEvaluator(delay=0)

    def loader(path: Path):
        if path.name == "valid.pt":
            return replacement
        raise OSError("corrupt artifact")

    engine, stdout, stderr = adapter(evaluator=original, evaluator_loader=loader)
    old_search = engine.engine
    engine.handle_command("setoption name ModelPath value corrupt.pt")
    assert engine.evaluator is original
    assert engine.engine is old_search
    assert engine.ready
    engine.handle_command("setoption name ModelPath value valid.pt")
    assert engine.evaluator is replacement
    assert engine.model_path == Path("valid.pt")
    engine.handle_command("isready")
    assert stdout.getvalue().splitlines() == ["readyok"]
    assert "corrupt artifact" in stderr.getvalue()


def test_new_game_clears_transposition_and_ordering_state() -> None:
    engine, _, _ = adapter(evaluator=MaterialEvaluator())
    assert engine.engine is not None
    engine.engine.table.store(
        TranspositionEntry(1, 1, 10, BoundType.EXACT, chess.Move.from_uci("e2e4"), 1)
    )
    engine.engine.killers[0] = [chess.Move.from_uci("e2e4")]
    engine.engine.history[(chess.WHITE, chess.E2, chess.E4)] = 1
    engine.engine.generation = 3
    engine.handle_command("ucinewgame")
    assert len(engine.engine.table) == 0
    assert engine.engine.killers == {}
    assert engine.engine.history == {}
    assert engine.engine.generation == 0


def test_options_are_validated_and_hash_rebuilds_state() -> None:
    engine, stdout, stderr = adapter(evaluator=MaterialEvaluator())
    old_search = engine.engine
    engine.handle_command("setoption name Hash value 2")
    assert engine.hash_mb == 2
    assert engine.engine is not old_search
    engine.handle_command("setoption name Threads value 2")
    assert engine.threads == 1
    engine.handle_command("setoption name Seed value 17")
    assert engine.seed == 17
    engine.handle_command("isready")
    assert stdout.getvalue().splitlines() == ["readyok"]
    assert "Threads must be 1" in stderr.getvalue()


def test_malformed_commands_preserve_position_and_stdout_purity() -> None:
    engine, stdout, stderr = adapter(evaluator=MaterialEvaluator())
    original = engine.board.fen()
    for command in (
        "nonsense",
        "position fen invalid",
        "position startpos moves e2e5",
        "go depth nope",
        "go mystery 1",
        "setoption name Unknown value 1",
    ):
        engine.handle_command(command)
    assert engine.board.fen() == original
    assert stdout.getvalue() == ""
    assert stderr.getvalue().count("uci error:") == 6


def test_terminal_position_is_the_only_source_of_bestmove_0000() -> None:
    engine, stdout, _ = adapter(evaluator=MaterialEvaluator())
    engine.handle_command("position fen 7k/7Q/7K/8/8/8/8/8 b - - 0 1")
    engine.handle_command("go depth 1")
    assert engine.wait_for_search(1)
    assert stdout.getvalue().splitlines()[-1] == "bestmove 0000"

    draw_engine, draw_stdout, _ = adapter(evaluator=MaterialEvaluator())
    draw_engine.handle_command("position fen 8/8/8/8/8/1k6/8/K7 w - - 100 1")
    draw_engine.handle_command("go depth 1")
    assert draw_engine.wait_for_search(1)
    move = draw_stdout.getvalue().splitlines()[-1].split()[1]
    assert move != "0000"
    assert chess.Move.from_uci(move) in draw_engine.board.legal_moves
