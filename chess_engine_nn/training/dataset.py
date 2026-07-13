"""Indexed, streaming-access JSONL training dataset."""

import json
from pathlib import Path

import chess
import torch
from torch.utils.data import Dataset

from chess_engine_nn.data.records import (
    DatasetError,
    PositionRecord,
    SplitName,
    file_sha256,
    load_manifest,
)
from chess_engine_nn.encoding import FeatureEncoder


class JsonlPositionDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    """Index record byte offsets while decoding one record at a time on access."""

    def __init__(self, dataset_dir: Path, split: SplitName, *, target_cap_cp: int = 10_000) -> None:
        if target_cap_cp <= 0:
            raise ValueError("target_cap_cp must be positive")
        self.dataset_dir = dataset_dir
        self.split = split
        self.target_cap_cp = target_cap_cp
        self.encoder = FeatureEncoder()
        self.manifest = load_manifest(dataset_dir / "manifest.json")
        if not self.manifest.complete:
            raise DatasetError(f"Dataset manifest is incomplete: {dataset_dir}")
        self.index: list[tuple[Path, int]] = []
        for shard in self.manifest.shards:
            if shard.split != split:
                continue
            path = dataset_dir / shard.path
            if not path.is_file() or file_sha256(path) != shard.sha256:
                raise DatasetError(f"Dataset shard is missing or corrupt: {path}")
            before = len(self.index)
            with path.open("rb") as file:
                while True:
                    offset = file.tell()
                    line = file.readline()
                    if not line:
                        break
                    self.index.append((path, offset))
            if len(self.index) - before != shard.records:
                raise DatasetError(f"Dataset shard record count does not match manifest: {path}")

    def __len__(self) -> int:
        return len(self.index)

    def record_at(self, index: int) -> PositionRecord:
        path, offset = self.index[index]
        with path.open("rb") as file:
            file.seek(offset)
            line = file.readline()
        try:
            record = PositionRecord.from_dict(json.loads(line))
        except (UnicodeDecodeError, json.JSONDecodeError, DatasetError) as error:
            raise DatasetError(f"Invalid indexed record at {path}:{offset}: {error}") from error
        if record.split != self.split:
            raise DatasetError(f"Record split does not match shard split at {path}:{offset}")
        return record

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        record = self.record_at(index)
        features = torch.from_numpy(self.encoder.encode_dense(chess.Board(record.fen)))
        clipped = max(-self.target_cap_cp, min(self.target_cap_cp, record.score_cp))
        target = torch.tensor(clipped / self.target_cap_cp, dtype=torch.float32)
        return features, target
