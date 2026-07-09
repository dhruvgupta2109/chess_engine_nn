# `chess_engine_nn` Package Specification

This directory contains the new engine project. Packaging, strict configuration, feature-schema v1, a material evaluator, the `doctor` command, and foundation tests are implemented. Model, search, data, training, and UCI modules below remain planned. See the [project README](../README.md) and [architecture](../.md/architechture.md).

## Responsibility

The package owns shared encoding, NNUE model/inference, alpha-beta search, UCI, offline PGN/Stockfish data generation, training, metrics, export, configuration, errors, and CLI. It owns neither a UI nor chess rules; `python-chess` supplies board state and legal moves.

## Planned modules

```text
__init__.py          version and small public exports
cli.py               developer/data/training/benchmark commands
config.py            typed TOML configuration
encoding.py          versioned side-relative features
model.py             NNUE PyTorch model and metadata
evaluator.py         runtime and batch evaluators
search.py            iterative negamax and quiescence
time_control.py      budgets and cancellation
transposition.py     bounded table and replacement
uci.py               UCI adapter/search worker
data/                PGN, Stockfish labels, records, splits
training/            datasets, training, metrics, export
```

Legacy top-level modules are not dependencies.

## Public interfaces

```python
class FeatureEncoder:
    schema_version: int
    def active_indices(self, board: chess.Board) -> numpy.ndarray: ...
    def encode_batch(self, boards: Sequence[chess.Board]) -> torch.Tensor: ...

class PositionEvaluator(Protocol):
    def evaluate(self, board: chess.Board) -> int: ...
    def evaluate_batch(self, boards: Sequence[chess.Board]) -> numpy.ndarray: ...

class SearchEngine:
    def search(
        self,
        board: chess.Board,
        limits: SearchLimits,
        observer: SearchObserver | None = None,
        stop_event: threading.Event | None = None,
    ) -> SearchResult: ...

def load_evaluator(path: Path, *, device: str = "cpu") -> PositionEvaluator: ...
```

Schema v1 has 768 piece-square, one side-to-move, four castling, and eight legal-en-passant-file features. Black-to-move positions swap colors and mirror vertically. Golden tests fix exact indices.

Evaluator scores are signed integer centipawns from side-to-move perspective and remain below mate scores. Search results contain a legal best move, centipawn/mate score, depth/seldepth, nodes, time, PV, and completion state. Search cannot alter the input board. Loading validates versions, checksum, shapes, and golden positions or raises typed `ModelArtifactError`; silent/random fallback is forbidden.

## Entry points

```bash
python -m chess_engine_nn.cli doctor
python -m chess_engine_nn.cli generate-data
python -m chess_engine_nn.cli train
python -m chess_engine_nn.cli evaluate-model
python -m chess_engine_nn.cli export
python -m chess_engine_nn.cli search
python -m chess_engine_nn.cli benchmark
python -m chess_engine_nn.uci --model PATH
```

## Artifacts

- Raw PGNs: `data/raw/`
- Shards/manifests: `data/processed/`
- Checkpoints: `artifacts/checkpoints/`
- Inference models: `artifacts/models/`
- Metrics/matches/profiles: `artifacts/reports/`

These are ignored except tiny fixtures/config examples. Artifacts carry schema/configuration/provenance/checksum metadata.

## Dependency direction

```text
encoding <- model <- evaluator <- search <- uci
    ^          ^          ^
    |          |          +--- runtime boundary
    |          +--- training/export
    +--- records/datasets
```

Training may import encoding/model. Runtime cannot import PGN readers, Stockfish, datasets, optimizers, or training loops.

## Ready definition

V1 is ready when it installs on Python 3.11, passes unit/integration/tactical/UCI tests, loads a validated CPU model, respects limits, returns only legal moves, and passes the [PRD baseline match](../.md/prd.md).
