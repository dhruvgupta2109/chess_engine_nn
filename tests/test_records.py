import json
from pathlib import Path

import chess
import pytest

from chess_engine_nn.data.records import (
    DATASET_SCHEMA_VERSION,
    DatasetError,
    DatasetManifest,
    PositionRecord,
    TeacherSettings,
    load_manifest,
    normalized_position_key,
    save_manifest_atomic,
)


def teacher() -> TeacherSettings:
    return TeacherSettings("Fakefish 1", "1", "depth", 1, 16, 1)


def test_position_record_round_trip() -> None:
    record = PositionRecord(
        fen=chess.STARTING_FEN,
        score_cp=20,
        mate_in=None,
        game_id="game",
        ply=0,
        result="*",
        split="train",
        teacher=teacher(),
    )
    assert PositionRecord.from_dict(record.to_dict()) == record
    assert record.schema_version == DATASET_SCHEMA_VERSION


def test_invalid_record_is_rejected() -> None:
    with pytest.raises(DatasetError, match="Invalid record FEN"):
        PositionRecord("bad", 0, None, "game", 0, "*", "train", teacher())


def test_normalized_key_ignores_move_counters() -> None:
    first = chess.STARTING_FEN
    second = chess.STARTING_BOARD_FEN + " w KQkq - 42 99"
    assert normalized_position_key(first) == normalized_position_key(second)


def test_manifest_atomic_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    manifest = DatasetManifest.create(
        run_id="test", seed=7, split_ratios={"train": 90, "validation": 5, "test": 5}, config={}
    )
    save_manifest_atomic(manifest, path)
    assert load_manifest(path).to_dict() == manifest.to_dict()
    assert not path.with_suffix(".json.tmp").exists()
    assert json.loads(path.read_text())["schema_version"] == DATASET_SCHEMA_VERSION
