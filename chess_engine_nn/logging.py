"""Central logging configuration for CLI and runtime components."""

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class JsonLineFormatter(logging.Formatter):
    """Format one structured JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "severity": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }
        run_id = getattr(record, "run_id", None)
        if run_id is not None:
            payload["run_id"] = run_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True)


def configure_logging(
    *, verbose: bool = False, quiet: bool = False, log_file: Path | None = None
) -> logging.Logger:
    """Configure the package logger with stderr and optional JSONL output."""
    if verbose and quiet:
        raise ValueError("verbose and quiet cannot both be enabled")
    logger = logging.getLogger("chess_engine_nn")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG if verbose else logging.WARNING if quiet else logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logger.addHandler(console)
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JsonLineFormatter())
        logger.addHandler(file_handler)
    return logger
