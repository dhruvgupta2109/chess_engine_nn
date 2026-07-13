"""Versioned logical records and append-safe dataset manifests."""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import chess

from chess_engine_nn.errors import ChessEngineError

DATASET_SCHEMA_VERSION = 1
SplitName = Literal["train", "validation", "test"]


class DatasetError(ChessEngineError):
    """Raised for corrupt, incompatible, or incomplete dataset artifacts."""


@dataclass(frozen=True)
class TeacherSettings:
    """Stockfish identity and deterministic analysis settings."""

    name: str
    version: str
    limit_type: Literal["depth", "nodes", "time"]
    limit_value: int | float
    hash_mb: int
    threads: int


@dataclass(frozen=True)
class PositionRecord:
    """One supervised position labeled from its side-to-move perspective."""

    fen: str
    score_cp: int
    mate_in: int | None
    game_id: str
    ply: int
    result: Literal["1-0", "0-1", "1/2-1/2", "*"]
    split: SplitName
    teacher: TeacherSettings
    schema_version: int = DATASET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DATASET_SCHEMA_VERSION:
            raise DatasetError(f"Unsupported record schema: {self.schema_version}")
        try:
            board = chess.Board(self.fen)
        except ValueError as error:
            raise DatasetError(f"Invalid record FEN: {self.fen}") from error
        if not board.is_valid():
            raise DatasetError(f"Record contains an invalid board: {self.fen}")
        if self.ply < 0:
            raise DatasetError("Record ply must be non-negative")
        if self.result not in {"1-0", "0-1", "1/2-1/2", "*"}:
            raise DatasetError(f"Invalid game result: {self.result}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PositionRecord":
        data = dict(value)
        data["teacher"] = TeacherSettings(**data["teacher"])
        try:
            return cls(**data)
        except (KeyError, TypeError) as error:
            raise DatasetError(f"Malformed position record: {error}") from error


@dataclass(frozen=True)
class ShardMetadata:
    path: str
    split: SplitName
    records: int
    sha256: str
    source_sha256: str


@dataclass
class DatasetManifest:
    """Auditable state for a resumable dataset-generation run."""

    run_id: str
    created_at: str
    schema_version: int
    seed: int
    split_ratios: dict[str, int]
    generation_config: dict[str, Any]
    teacher: dict[str, Any] | None = None
    shards: list[ShardMetadata] = field(default_factory=list)
    completed_sources: dict[str, str] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    complete: bool = False

    @classmethod
    def create(
        cls, *, run_id: str, seed: int, split_ratios: dict[str, int], config: dict[str, Any]
    ) -> "DatasetManifest":
        return cls(
            run_id=run_id,
            created_at=datetime.now(UTC).isoformat(),
            schema_version=DATASET_SCHEMA_VERSION,
            seed=seed,
            split_ratios=split_ratios,
            generation_config=config,
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["shards"] = [asdict(shard) for shard in self.shards]
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DatasetManifest":
        data = dict(value)
        data["shards"] = [ShardMetadata(**shard) for shard in data.get("shards", [])]
        try:
            manifest = cls(**data)
        except (KeyError, TypeError) as error:
            raise DatasetError(f"Malformed dataset manifest: {error}") from error
        if manifest.schema_version != DATASET_SCHEMA_VERSION:
            raise DatasetError(f"Unsupported manifest schema: {manifest.schema_version}")
        return manifest


def normalized_position_key(fen: str) -> str:
    """Hash the rule-relevant first four FEN fields for deterministic deduplication."""
    board = chess.Board(fen)
    normalized = " ".join(board.fen(en_passant="legal").split()[:4])
    return hashlib.sha256(normalized.encode()).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_manifest(path: Path) -> DatasetManifest:
    try:
        return DatasetManifest.from_dict(json.loads(path.read_text()))
    except FileNotFoundError as error:
        raise DatasetError(f"Manifest not found: {path}") from error
    except json.JSONDecodeError as error:
        raise DatasetError(f"Invalid manifest JSON: {path}: {error}") from error


def save_manifest_atomic(manifest: DatasetManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n")
    temporary.replace(path)
