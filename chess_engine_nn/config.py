"""Strict TOML configuration for development and runtime foundations."""

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, TypeVar

from chess_engine_nn.errors import ConfigurationError


@dataclass(frozen=True)
class PathsConfig:
    data_dir: Path = Path("data")
    artifacts_dir: Path = Path("artifacts")
    stockfish_path: Path | None = None


@dataclass(frozen=True)
class RuntimeConfig:
    seed: int = 20260713
    hash_mb: int = 64
    threads: int = 1
    model_path: Path | None = None


@dataclass(frozen=True)
class DataConfig:
    run_name: str = "development-v1"
    every_n_plies: int = 4
    min_ply: int = 8
    max_positions_per_game: int = 32
    train_ratio: int = 90
    validation_ratio: int = 5
    test_ratio: int = 5


@dataclass(frozen=True)
class StockfishConfig:
    executable: Path | None = None
    depth: int | None = 8
    nodes: int | None = None
    time_ms: int | None = None
    hash_mb: int = 64
    threads: int = 1
    mate_score_cp: int = 10_000


@dataclass(frozen=True)
class TrainingConfig:
    accumulator_dim: int = 256
    hidden_dim: int = 32
    target_cap_cp: int = 10_000
    batch_size: int = 64
    learning_rate: float = 0.001
    epochs: int = 20
    patience: int = 5
    checkpoint_every: int = 1
    huber_delta: float = 0.1
    draw_band_cp: int = 50
    device: str = "cpu"
    num_workers: int = 0


@dataclass(frozen=True)
class SearchConfig:
    default_depth: int = 4
    max_quiescence_depth: int = 8
    aspiration_window_cp: int = 50


@dataclass(frozen=True)
class AppConfig:
    paths: PathsConfig = PathsConfig()
    runtime: RuntimeConfig = RuntimeConfig()
    data: DataConfig = DataConfig()
    stockfish: StockfishConfig = StockfishConfig()
    training: TrainingConfig = TrainingConfig()
    search: SearchConfig = SearchConfig()


T = TypeVar("T")


def _build_section(cls: type[T], values: dict[str, Any], section: str) -> T:
    allowed = {field.name for field in fields(cls)}
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise ConfigurationError(f"Unknown {section} configuration keys: {', '.join(unknown)}")

    converted = dict(values)
    for key in ("data_dir", "artifacts_dir", "stockfish_path", "model_path", "executable"):
        if key in converted and converted[key] is not None:
            if not isinstance(converted[key], str):
                raise ConfigurationError(f"{section}.{key} must be a path string")
            converted[key] = Path(converted[key]).expanduser()
    try:
        return cls(**converted)
    except TypeError as error:
        raise ConfigurationError(f"Invalid {section} configuration: {error}") from error


def load_config(path: Path | None = None, *, overrides: dict[str, Any] | None = None) -> AppConfig:
    """Load defaults, then TOML, then dotted-key overrides."""
    raw: dict[str, Any] = {}
    if path is not None:
        try:
            with path.open("rb") as file:
                raw = tomllib.load(file)
        except FileNotFoundError as error:
            raise ConfigurationError(f"Configuration file not found: {path}") from error
        except tomllib.TOMLDecodeError as error:
            raise ConfigurationError(f"Invalid TOML in {path}: {error}") from error

    sections = ("paths", "runtime", "data", "stockfish", "training", "search")
    unknown_sections = sorted(set(raw) - set(sections))
    if unknown_sections:
        raise ConfigurationError(f"Unknown configuration sections: {', '.join(unknown_sections)}")
    if any(
        not isinstance(raw.get(section, {}), dict)
        for section in sections
    ):
        raise ConfigurationError("Configuration sections must be TOML tables")

    merged = {
        section: dict(raw.get(section, {}))
        for section in sections
    }
    for dotted_key, value in (overrides or {}).items():
        try:
            section, key = dotted_key.split(".", 1)
        except ValueError as error:
            raise ConfigurationError(f"Override must use section.key: {dotted_key}") from error
        if section not in merged:
            raise ConfigurationError(f"Unknown override section: {section}")
        merged[section][key] = value

    config = AppConfig(
        paths=_build_section(PathsConfig, merged["paths"], "paths"),
        runtime=_build_section(RuntimeConfig, merged["runtime"], "runtime"),
        data=_build_section(DataConfig, merged["data"], "data"),
        stockfish=_build_section(StockfishConfig, merged["stockfish"], "stockfish"),
        training=_build_section(TrainingConfig, merged["training"], "training"),
        search=_build_section(SearchConfig, merged["search"], "search"),
    )
    _validate(config)
    return config


def _validate(config: AppConfig) -> None:
    if config.runtime.seed < 0:
        raise ConfigurationError("runtime.seed must be non-negative")
    if not 1 <= config.runtime.hash_mb <= 1_048_576:
        raise ConfigurationError("runtime.hash_mb must be between 1 and 1048576")
    if config.runtime.threads != 1:
        raise ConfigurationError("runtime.threads must be 1 in engine v1")
    if not config.data.run_name or any(character in config.data.run_name for character in "/\\"):
        raise ConfigurationError("data.run_name must be a non-empty directory name")
    if config.data.every_n_plies <= 0 or config.data.max_positions_per_game <= 0:
        raise ConfigurationError("data sampling intervals must be positive")
    if config.data.min_ply < 0:
        raise ConfigurationError("data.min_ply must be non-negative")
    from chess_engine_nn.data.split import validate_split_ratios

    validate_split_ratios(
        config.data.train_ratio, config.data.validation_ratio, config.data.test_ratio
    )
    selected_limits = sum(
        value is not None
        for value in (config.stockfish.depth, config.stockfish.nodes, config.stockfish.time_ms)
    )
    if selected_limits != 1:
        raise ConfigurationError("stockfish requires exactly one of depth, nodes, or time_ms")
    if config.stockfish.hash_mb <= 0 or config.stockfish.threads <= 0:
        raise ConfigurationError("stockfish hash_mb and threads must be positive")
    if config.stockfish.mate_score_cp <= 0:
        raise ConfigurationError("stockfish.mate_score_cp must be positive")
    training = config.training
    integer_positive = (
        training.accumulator_dim,
        training.hidden_dim,
        training.target_cap_cp,
        training.batch_size,
        training.epochs,
        training.checkpoint_every,
    )
    if min(integer_positive) <= 0:
        raise ConfigurationError(
            "training dimensions, batch size, epochs, and cap must be positive"
        )
    if training.patience < 0 or training.num_workers < 0 or training.draw_band_cp < 0:
        raise ConfigurationError("training patience, workers, and draw band cannot be negative")
    if training.learning_rate <= 0 or training.huber_delta <= 0:
        raise ConfigurationError("training learning_rate and huber_delta must be positive")
    if training.device not in {"cpu", "mps"}:
        raise ConfigurationError("training.device must be 'cpu' or 'mps'")
    if config.search.default_depth <= 0 or config.search.max_quiescence_depth < 0:
        raise ConfigurationError("search depths are invalid")
    if config.search.aspiration_window_cp <= 0:
        raise ConfigurationError("search.aspiration_window_cp must be positive")
