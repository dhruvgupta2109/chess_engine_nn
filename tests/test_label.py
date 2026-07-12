import shutil
from pathlib import Path

import chess
import pytest

from chess_engine_nn.data.label import StockfishTeacher, TeacherError, make_limit
from chess_engine_nn.errors import ConfigurationError


def test_exactly_one_teacher_limit_is_required() -> None:
    with pytest.raises(ConfigurationError, match="exactly one"):
        make_limit(depth=None, nodes=None, time_ms=None)
    with pytest.raises(ConfigurationError, match="exactly one"):
        make_limit(depth=1, nodes=10, time_ms=None)
    name, value, limit = make_limit(depth=2, nodes=None, time_ms=None)
    assert (name, value, limit.depth) == ("depth", 2, 2)


def test_missing_teacher_executable_is_actionable(tmp_path: Path) -> None:
    with pytest.raises(TeacherError, match="Unable to start Stockfish"):
        with StockfishTeacher(tmp_path / "missing", depth=1):
            pass


def test_mate_score_is_clipped_and_distance_retained() -> None:
    class FakeEngine:
        def analyse(self, board, limit):
            return {"score": chess.engine.PovScore(chess.engine.Mate(3), board.turn)}

    teacher = StockfishTeacher(Path("unused"), depth=1, mate_score_cp=9_000)
    teacher.engine = FakeEngine()  # type: ignore[assignment]
    result = teacher.label(chess.Board())
    assert result.score_cp == 8_997  # cap minus mate distance preserves urgency
    assert result.mate_in == 3


@pytest.mark.stockfish
def test_real_stockfish_labels_both_turn_perspectives() -> None:
    executable = shutil.which("stockfish")
    if executable is None:
        pytest.skip("Stockfish is not installed")
    white = chess.Board("7k/8/8/8/8/8/Q7/K7 w - - 0 1")
    black = chess.Board("7k/8/8/8/8/8/Q7/K7 b - - 0 1")
    with StockfishTeacher(Path(executable), depth=2, hash_mb=16) as teacher:
        assert teacher.settings is not None
        assert "Stockfish" in teacher.settings.name
        assert teacher.label(white).score_cp > 0
        assert teacher.label(black).score_cp < 0
