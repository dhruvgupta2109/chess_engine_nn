"""Resumable PGN-to-labeled-shard dataset generation."""

import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Protocol, cast

import chess

from chess_engine_nn.data.label import LabelResult
from chess_engine_nn.data.pgn import PgnStats, stream_sampled_positions
from chess_engine_nn.data.records import (
    DatasetError,
    DatasetManifest,
    PositionRecord,
    ShardMetadata,
    SplitName,
    TeacherSettings,
    file_sha256,
    load_manifest,
    normalized_position_key,
    save_manifest_atomic,
)
from chess_engine_nn.data.split import assign_game_split, validate_split_ratios


class PositionTeacher(Protocol):
    settings: TeacherSettings | None

    def label(self, board: chess.Board) -> LabelResult: ...


def _load_seen_keys(output_dir: Path, manifest: DatasetManifest) -> set[str]:
    seen: set[str] = set()
    for shard in manifest.shards:
        path = output_dir / shard.path
        if not path.is_file() or file_sha256(path) != shard.sha256:
            raise DatasetError(f"Completed shard is missing or corrupt: {path}")
        with path.open() as file:
            for line_number, line in enumerate(file, start=1):
                try:
                    record = PositionRecord.from_dict(json.loads(line))
                except (json.JSONDecodeError, DatasetError) as error:
                    message = f"Invalid record in {path}:{line_number}: {error}"
                    raise DatasetError(message) from error
                seen.add(normalized_position_key(record.fen))
    return seen


def generate_dataset(
    sources: Sequence[Path],
    output_dir: Path,
    teacher: PositionTeacher,
    *,
    seed: int,
    train_ratio: int = 90,
    validation_ratio: int = 5,
    test_ratio: int = 5,
    every_n_plies: int = 4,
    min_ply: int = 8,
    max_positions_per_game: int = 32,
) -> DatasetManifest:
    """Generate atomic JSONL shards, resuming completed source files safely."""
    validate_split_ratios(train_ratio, validation_ratio, test_ratio)
    if teacher.settings is None:
        raise DatasetError("Teacher has no validated settings")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    ratios = {"train": train_ratio, "validation": validation_ratio, "test": test_ratio}
    generation_config = {
        "every_n_plies": every_n_plies,
        "min_ply": min_ply,
        "max_positions_per_game": max_positions_per_game,
    }
    if manifest_path.exists():
        manifest = load_manifest(manifest_path)
        if manifest.seed != seed or manifest.split_ratios != ratios:
            raise DatasetError("Existing manifest seed or split ratios do not match this run")
        if manifest.generation_config != generation_config:
            raise DatasetError("Existing manifest sampling configuration does not match this run")
        if manifest.teacher != asdict(teacher.settings):
            raise DatasetError("Existing manifest teacher settings do not match this run")
    else:
        manifest = DatasetManifest.create(
            run_id=output_dir.name, seed=seed, split_ratios=ratios, config=generation_config
        )
        manifest.teacher = asdict(teacher.settings)
        save_manifest_atomic(manifest, manifest_path)

    manifest.complete = False
    save_manifest_atomic(manifest, manifest_path)
    seen = _load_seen_keys(output_dir, manifest)
    completed_hashes = set(manifest.completed_sources.values())

    for source in sources:
        if not source.is_file():
            raise DatasetError(f"PGN source not found: {source}")
        source_hash = file_sha256(source)
        if source_hash in completed_hashes:
            continue

        stats = PgnStats()
        handles: dict[SplitName, object] = {}
        temporary_paths: dict[SplitName, Path] = {}
        counts: dict[SplitName, int] = {"train": 0, "validation": 0, "test": 0}
        prefix = f"{source_hash[:12]}"
        try:
            for split in cast(tuple[SplitName, ...], ("train", "validation", "test")):
                temporary = output_dir / f".{prefix}-{split}.jsonl.tmp"
                temporary_paths[split] = temporary
                handles[split] = temporary.open("w", encoding="utf-8")

            for candidate in stream_sampled_positions(
                source,
                every_n_plies=every_n_plies,
                min_ply=min_ply,
                max_positions_per_game=max_positions_per_game,
                stats=stats,
            ):
                key = normalized_position_key(candidate.fen)
                if key in seen:
                    manifest.counts["duplicates_skipped"] = (
                        manifest.counts.get("duplicates_skipped", 0) + 1
                    )
                    continue
                split = assign_game_split(
                    candidate.game_id,
                    seed=seed,
                    train=train_ratio,
                    validation=validation_ratio,
                    test=test_ratio,
                )
                result = teacher.label(chess.Board(candidate.fen))
                record = PositionRecord(
                    fen=candidate.fen,
                    score_cp=result.score_cp,
                    mate_in=result.mate_in,
                    game_id=candidate.game_id,
                    ply=candidate.ply,
                    result=cast(object, candidate.result),  # validated by PositionRecord
                    split=split,
                    teacher=teacher.settings,
                )
                handle = handles[split]
                handle.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")  # type: ignore[attr-defined]
                counts[split] += 1
                seen.add(key)
        finally:
            for handle in handles.values():
                handle.close()  # type: ignore[attr-defined]

        for split, temporary in temporary_paths.items():
            if counts[split] == 0:
                temporary.unlink(missing_ok=True)
                continue
            final = output_dir / f"{prefix}-{split}.jsonl"
            temporary.replace(final)
            manifest.shards.append(
                ShardMetadata(
                    path=final.name,
                    split=split,
                    records=counts[split],
                    sha256=file_sha256(final),
                    source_sha256=source_hash,
                )
            )
            manifest.counts[split] = manifest.counts.get(split, 0) + counts[split]

        manifest.counts["games_read"] = manifest.counts.get("games_read", 0) + stats.games_read
        manifest.counts["games_with_errors"] = (
            manifest.counts.get("games_with_errors", 0) + stats.games_with_errors
        )
        manifest.counts["terminal_skipped"] = (
            manifest.counts.get("terminal_skipped", 0) + stats.terminal_skipped
        )
        manifest.completed_sources[str(source.resolve())] = source_hash
        completed_hashes.add(source_hash)
        save_manifest_atomic(manifest, manifest_path)

    manifest.complete = True
    save_manifest_atomic(manifest, manifest_path)
    return manifest
