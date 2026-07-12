import shutil
from pathlib import Path

import chess
import pytest

from chess_engine_nn.data.generate import generate_dataset
from chess_engine_nn.data.label import LabelResult
from chess_engine_nn.data.records import DatasetError, TeacherSettings, load_manifest

FIXTURE = Path(__file__).parent / "fixtures" / "games.pgn"


class FakeTeacher:
    settings = TeacherSettings("Fakefish 1", "1", "depth", 1, 16, 1)

    def __init__(self) -> None:
        self.calls = 0

    def label(self, board: chess.Board) -> LabelResult:
        self.calls += 1
        return LabelResult(score_cp=board.fullmove_number, mate_in=None)


class InterruptingTeacher(FakeTeacher):
    def label(self, board: chess.Board) -> LabelResult:
        if self.calls == 2:
            raise RuntimeError("simulated interruption")
        return super().label(board)


def generate(source: Path, output: Path, teacher: FakeTeacher):
    return generate_dataset(
        [source],
        output,
        teacher,
        seed=7,
        every_n_plies=2,
        min_ply=2,
        max_positions_per_game=3,
    )


def test_generation_writes_valid_manifest_and_resumes(tmp_path: Path) -> None:
    teacher = FakeTeacher()
    output = tmp_path / "dataset"
    manifest = generate(FIXTURE, output, teacher)

    assert manifest.complete
    assert sum(manifest.counts.get(split, 0) for split in ("train", "validation", "test")) == 6
    assert teacher.calls == 6
    assert sum(shard.records for shard in manifest.shards) == 6
    assert all((output / shard.path).is_file() for shard in manifest.shards)

    resumed = generate(FIXTURE, output, teacher)
    assert resumed.to_dict() == load_manifest(output / "manifest.json").to_dict()
    assert teacher.calls == 6
    assert len(resumed.shards) == len(manifest.shards)


def test_duplicate_positions_from_new_source_are_not_relabeled(tmp_path: Path) -> None:
    teacher = FakeTeacher()
    output = tmp_path / "dataset"
    generate(FIXTURE, output, teacher)
    copied = tmp_path / "same-games.pgn"
    shutil.copy(FIXTURE, copied)
    copied.write_text(copied.read_text() + "\n")  # different source hash, identical games

    manifest = generate_dataset(
        [copied],
        output,
        teacher,
        seed=7,
        every_n_plies=2,
        min_ply=2,
        max_positions_per_game=3,
    )
    assert teacher.calls == 6
    assert manifest.counts["duplicates_skipped"] == 6
    assert len(manifest.completed_sources) == 2


def test_corrupt_completed_shard_is_rejected(tmp_path: Path) -> None:
    teacher = FakeTeacher()
    output = tmp_path / "dataset"
    manifest = generate(FIXTURE, output, teacher)
    (output / manifest.shards[0].path).write_text("corrupt\n")
    with pytest.raises(DatasetError, match="missing or corrupt"):
        generate(FIXTURE, output, teacher)


def test_changed_resume_configuration_is_rejected(tmp_path: Path) -> None:
    teacher = FakeTeacher()
    output = tmp_path / "dataset"
    generate(FIXTURE, output, teacher)
    with pytest.raises(DatasetError, match="sampling configuration"):
        generate_dataset(
            [FIXTURE], output, teacher, seed=7, every_n_plies=3, min_ply=2
        )


def test_interrupted_source_restarts_without_partial_records(tmp_path: Path) -> None:
    output = tmp_path / "dataset"
    with pytest.raises(RuntimeError, match="simulated interruption"):
        generate(FIXTURE, output, InterruptingTeacher())

    interrupted = load_manifest(output / "manifest.json")
    assert not interrupted.complete
    assert interrupted.shards == []
    assert interrupted.completed_sources == {}

    teacher = FakeTeacher()
    completed = generate(FIXTURE, output, teacher)
    assert completed.complete
    assert teacher.calls == 6
    assert sum(shard.records for shard in completed.shards) == 6
