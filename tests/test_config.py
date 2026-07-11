from pathlib import Path

import pytest

from chess_engine_nn.config import load_config
from chess_engine_nn.errors import ConfigurationError


def test_defaults_and_overrides() -> None:
    config = load_config(overrides={"runtime.seed": 7, "paths.data_dir": "fixtures"})
    assert config.runtime.seed == 7
    assert config.runtime.threads == 1
    assert config.paths.data_dir == Path("fixtures")


def test_toml_loads_and_cli_style_override_wins(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("[runtime]\nseed = 2\nhash_mb = 32\nthreads = 1\n")
    config = load_config(config_path, overrides={"runtime.seed": 3})
    assert config.runtime.seed == 3
    assert config.runtime.hash_mb == 32


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("[unknown]\nvalue = 1\n", "Unknown configuration sections"),
        ("[runtime]\nunknown = 1\n", "Unknown runtime configuration keys"),
        ("[runtime]\nthreads = 2\n", "must be 1"),
        ("[runtime]\nseed = -1\n", "non-negative"),
    ],
)
def test_invalid_config_is_rejected(tmp_path: Path, content: str, message: str) -> None:
    path = tmp_path / "bad.toml"
    path.write_text(content)
    with pytest.raises(ConfigurationError, match=message):
        load_config(path)
