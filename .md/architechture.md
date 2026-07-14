# Architecture

> The existing filename `architechture.md` is intentionally retained for compatibility.

## System flow

```text
PGN -> sampler -> Stockfish labeler -> versioned dataset shards
                                            |
                                            v
                                      PyTorch trainer
                                            |
                               checkpoint -> exporter
                                            |
                                            v
UCI/CLI ---------------------> python-chess Board -> alpha-beta search -> inference evaluator
Browser -> REST/WebSocket service --------^  |                    |
                                             +---- legal moves ---+
```

`python-chess` owns rules. Search owns move selection. The model estimates only the value of non-terminal positions.

## Proposed structure

```text
chess_engine_nn/
  __init__.py
  cli.py
  config.py
  encoding.py
  model.py
  evaluator.py
  search.py
  time_control.py
  transposition.py
  uci.py
  web_api/{app.py,game_service.py,static/}
  data/{pgn.py,label.py,records.py,split.py}
  training/{dataset.py,train.py,metrics.py,export.py}
configs/{dev.toml,train.toml,benchmark.toml}
tests/{unit,integration,positions}/
data/{raw,processed}/              # ignored except fixtures
artifacts/{checkpoints,models,reports}/  # ignored
web/                                     # React/TypeScript Phase 8 source
```

Imported top-level Python files remain unchanged and are not runtime dependencies. Only the
offline controlled-match adapter imports their classes to benchmark the new engine.

The Phase 8 browser is a post-v1 adapter. The server owns the live `chess.Board`, legal-move
validation, outcomes, SAN history, and background search lifecycle. The frontend renders server
state and submits UCI moves; it does not implement an independent rules engine. A monotonically
increasing game generation prevents a cancelled or late search from changing a newer position.
The compiled frontend is Python package data, and the launcher binds to loopback by default.

## Position and feature schema

Live positions are `chess.Board`; FEN is the persisted/debug boundary and UCI notation is the external move format. Search pushes/pops safely and leaves the caller's board unchanged.

Feature schema v1 has 781 binary features:

- 768 piece-square features (`12 × 64`);
- one side-to-move feature;
- four castling-right flags;
- eight en-passant-file flags, all zero without a legal en-passant capture.

For black to move, colors are swapped and squares vertically mirrored before indexing. Castling and en-passant features undergo the same perspective transform. Golden tests lock the mapping. The shared encoder exposes sorted sparse indices for inference and equivalent dense batches for training.

## Model

The exported v1 architecture is:

```text
sparse binary features
  -> linear accumulator (256)
  -> clipped ReLU [0,1]
  -> linear (32)
  -> clipped ReLU [0,1]
  -> linear (1)
  -> tanh [-1,1]
  -> centipawn conversion and clamp
```

Dimensions remain artifact metadata. Targets and outputs are normalized by the configured centipawn cap; `tanh` keeps the learned value finite before conversion back to integer centipawns. Dense PyTorch training is used initially, while the evaluator interface allows later incremental accumulators or quantized/native inference.

```python
class PositionEvaluator(Protocol):
    def evaluate(self, board: chess.Board) -> int: ...
    def evaluate_batch(self, boards: Sequence[chess.Board]) -> numpy.ndarray: ...
```

Scores are finite signed centipawns from the side-to-move perspective and clamped to `[-EVAL_MAX, EVAL_MAX]`, strictly below `MATE_THRESHOLD`.

## Search contract

```python
@dataclass(frozen=True)
class SearchLimits:
    depth: int | None = None
    nodes: int | None = None
    move_time_ms: int | None = None
    white_time_ms: int | None = None
    black_time_ms: int | None = None
    white_increment_ms: int = 0
    black_increment_ms: int = 0
    moves_to_go: int | None = None

@dataclass(frozen=True)
class SearchResult:
    best_move: chess.Move | None
    score_cp: int | None
    mate_in: int | None
    depth: int
    seldepth: int
    nodes: int
    elapsed_ms: int
    principal_variation: tuple[chess.Move, ...]
    completed: bool
```

`SearchEngine.search(board, limits, observer, stop_event) -> SearchResult` checks terminal state, iterates depths, runs negamax alpha-beta and quiescence, probes/stores exact/lower/upper transposition bounds, checks cancellation, and publishes completed iterations. It returns the last completed iteration; if interrupted in depth 1 it returns the best examined legal move or a deterministic legal fallback.

The initial engine is single-threaded. Mutable state belongs to one search invocation.

### Phase 4 reference performance

On the reference Apple Silicon laptop, the deterministic untrained `256-32-1` architecture measured approximately 18,000 single-position evaluations/second. Starting-position depth-2 search visited 387 nodes in 39 ms, approximately 9,900 NPS. These are regression baselines, not release-strength claims; measurements must record model, hardware, limits, and versions.

### Phase 6 measured runtime

Phase 6 kept the schema/model/search contracts unchanged while replacing `piece_map` feature discovery with exact bitboard scans, specializing single-position inference, guarding impossible draw claims, and avoiding duplicate repetition checks around transposition access. A paired seven-repeat benchmark on the reference M4 improved neural evaluation from 18,844 to 28,684 positions/second and the identical 387-node depth-2 search from 37.496 to 12.235 ms.

The versioned `tools/benchmark_phase6.py` report records component rates, representative searches, ablations, environment, seed, production-shaped model metadata, and weight checksum. The report showed that move ordering and transposition bounds materially reduce nodes; quiescence remains enabled for tactical correctness. TorchScript, unavailable int8 quantization, and thread changes were rejected from measured results. See [Phase 6 Performance and Ablation Report](Phase6.md).

## UCI adapter

The UCI loop owns stdin/stdout, one search worker, and cancellation. The command thread remains available while search runs and converts `position` into a history-preserving `chess.Board` plus `go` fields into the shared `SearchLimits`. A locked writer serializes completed-iteration `info` messages and the final `bestmove`; diagnostics use stderr only.

Options are `ModelPath`, transposition-table `Hash` in MiB, `Threads` fixed to 1, and deterministic `Seed`. Model reload is transactional: validation and replacement-engine construction finish before the active evaluator is exchanged, so a failed reload retains the previous model. Hash changes rebuild bounded search state, while `ucinewgame` clears the table, killers, and history only after safely joining a cancelled worker.

Production startup has no evaluator fallback. `isready` succeeds only after a validated inference artifact is loaded through `--model` or `setoption name ModelPath`; tests and development code may explicitly inject a `PositionEvaluator`. `bestmove 0000` is emitted only when `python-chess` reports no legal moves, including the distinction between terminal claims with legal moves and checkmate/stalemate.

## Dataset contract

The logical record is:

```text
fen: string
score_cp: int
mate_in: int or null
game_id: string
ply: int
result: 1-0, 0-1, 1/2-1/2, or *
teacher: name, version, limit type/value, hash MiB, threads
schema_version: int
```

Dataset schema v1 uses UTF-8 JSON Lines split into atomic source/split shards plus a JSON manifest. A 25,000-record Phase 2 benchmark measured approximately 363k writes/second and 624k reads/second on the reference Apple Silicon laptop, making JSONL sufficient for the first training corpus while remaining inspectable and streamable. The manifest records shard checksums/counts, split rule, generation config, provenance, and completion state. A future format change must preserve the logical record/reader boundary and be justified by larger-corpus measurements.

Stockfish scores normalize to side-to-move perspective. Mate values are capped for training with original distance retained. A seeded hash of stable game ID assigns a default 90/5/5 split. Deterministic deduplication prevents a normalized position from crossing splits.

## Training and artifacts

Training validates schemas, fits only train data, selects checkpoints on validation loss, evaluates the frozen best model once on test, then exports and reports it. Default loss is Huber over clipped centipawn targets.

A resumable checkpoint contains architecture/schema versions, dimensions, model/optimizer state, epoch/step, metrics, resolved config, seed, dataset manifest ID, versions, and source commit. An inference artifact contains only weights, required architecture/encoding/score metadata, data identifier, metric summary, and checksum.

Artifacts are written to a temporary path, reloaded against golden positions, then atomically renamed. Unsupported versions or shapes are rejected.

## Release benchmark boundary

The offline `tools/run_legacy_match.py` adapter translates a `python-chess` position into the
imported board representation only at the comparison boundary. `python-chess` remains the
rules authority: every translated move is checked against its legal move set, normal terminal
and draw rules decide games, and an illegal legacy move is a recorded forfeit. The adapter is
not imported by the package or UCI runtime.

The frozen v1 artifact was trained from 1,557,221 leakage-safe Stockfish-labeled training
positions and selected on 86,213 validation positions. Its 86,452-position test split was
evaluated once. The locked 208-game, balanced-color, depth-2 comparison scored 78.125%; a
sensitivity result excluding all legacy illegal-move forfeits was 56.25%. Full provenance,
metrics, checksums, commands, and interpretation limits are in [Phase 7](Phase7.md).

## Configuration and dependencies

Precedence is built-in defaults, TOML, then explicit CLI flags. Unknown keys, contradictory limits, invalid ranges, and missing paths are errors. `STOCKFISH_PATH` may provide a machine path and is recorded in resolved run metadata.

- Python 3.11 baseline.
- `python-chess`, PyTorch, and NumPy for the engine/model.
- pytest and benchmark tools for development.
- Stockfish only for offline labels/matches.
- Pygame only for the legacy baseline.

Quantized evaluators, books, tablebases, parallel search, and UI are later adapters and do not change v1 boundaries.
