import json
from pathlib import Path

import chess
import pytest

from chess_engine_nn.data.records import (
    DatasetManifest,
    PositionRecord,
    ShardMetadata,
    TeacherSettings,
    file_sha256,
    save_manifest_atomic,
)


@pytest.fixture
def training_dataset(tmp_path: Path) -> Path:
    output = tmp_path / "dataset"
    output.mkdir()
    teacher = TeacherSettings("FixtureTeacher", "1", "depth", 1, 16, 1)
    positions = [
        (chess.STARTING_FEN, 0),
        ("7k/8/8/8/8/8/Q7/K7 w - - 0 1", 100),
        ("7k/8/8/8/8/8/Q7/K7 b - - 0 1", -100),
        ("7k/8/8/8/8/8/R7/K7 w - - 0 1", 50),
        ("7k/8/8/8/8/8/R7/K7 b - - 0 1", -50),
        ("7k/8/8/8/8/8/P7/K7 w - - 0 1", 20),
    ]
    split_positions = {
        "train": positions * 3,
        "validation": positions,
        "test": list(reversed(positions)),
    }
    manifest = DatasetManifest.create(
        run_id="training-fixture",
        seed=11,
        split_ratios={"train": 60, "validation": 20, "test": 20},
        config={"fixture": True},
    )
    manifest.teacher = teacher.__dict__
    for split, examples in split_positions.items():
        path = output / f"fixture-{split}.jsonl"
        with path.open("w") as file:
            for index, (fen, score) in enumerate(examples):
                record = PositionRecord(
                    fen=fen,
                    score_cp=score,
                    mate_in=None,
                    game_id=f"{split}-{index}",
                    ply=index,
                    result="1/2-1/2" if score == 0 else "1-0",
                    split=split,  # type: ignore[arg-type]
                    teacher=teacher,
                )
                file.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
        manifest.shards.append(
            ShardMetadata(
                path=path.name,
                split=split,  # type: ignore[arg-type]
                records=len(examples),
                sha256=file_sha256(path),
                source_sha256=f"fixture-{split}",
            )
        )
        manifest.counts[split] = len(examples)
    manifest.complete = True
    save_manifest_atomic(manifest, output / "manifest.json")
    return output
