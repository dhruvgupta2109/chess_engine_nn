"""Measure the Phase 2 JSONL record format without retaining generated data."""

import json
import tempfile
import time
from pathlib import Path


def main(records: int = 25_000) -> int:
    sample = {
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "score_cp": 20,
        "mate_in": None,
        "game_id": "0" * 64,
        "ply": 12,
        "result": "1/2-1/2",
        "split": "train",
        "teacher": {
            "name": "Stockfish 18",
            "version": "18",
            "limit_type": "depth",
            "limit_value": 8,
            "hash_mb": 64,
            "threads": 1,
        },
        "schema_version": 1,
    }
    encoded = json.dumps(sample, sort_keys=True) + "\n"
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "benchmark.jsonl"
        started = time.perf_counter()
        with path.open("w") as file:
            for index in range(records):
                sample["ply"] = index
                file.write(json.dumps(sample, sort_keys=True) + "\n")
        write_seconds = time.perf_counter() - started
        started = time.perf_counter()
        with path.open() as file:
            loaded = sum(1 for line in file if json.loads(line))
        read_seconds = time.perf_counter() - started
        result = {
            "records": loaded,
            "sample_bytes": len(encoded),
            "file_bytes": path.stat().st_size,
            "write_records_per_second": round(records / write_seconds),
            "read_records_per_second": round(records / read_seconds),
        }
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
