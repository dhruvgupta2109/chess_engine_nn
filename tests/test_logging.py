import json
from pathlib import Path

import pytest

from chess_engine_nn.logging import configure_logging


def test_console_logging_uses_stderr(capsys) -> None:
    logger = configure_logging()
    logger.info("foundation ready")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "foundation ready" in captured.err


def test_json_file_logging_contains_required_fields(tmp_path: Path) -> None:
    path = tmp_path / "logs" / "run.jsonl"
    logger = configure_logging(quiet=True, log_file=path)
    logger.info("measured", extra={"run_id": "phase-1"})
    for handler in logger.handlers:
        handler.flush()
    record = json.loads(path.read_text().strip())
    assert record["severity"] == "INFO"
    assert record["component"] == "chess_engine_nn"
    assert record["message"] == "measured"
    assert record["run_id"] == "phase-1"
    assert record["timestamp"]


def test_verbose_and_quiet_are_mutually_exclusive() -> None:
    with pytest.raises(ValueError, match="cannot both"):
        configure_logging(verbose=True, quiet=True)
