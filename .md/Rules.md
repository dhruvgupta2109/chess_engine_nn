# Engineering Rules

## Chess and scores

- `python-chess` is authoritative. The model evaluates only; it never generates, validates, or bypasses legal moves.
- Search leaves the caller's board unchanged and resolves terminal results before neural evaluation.
- Repetition uses active history; FEN alone cannot reconstruct it. Promotions, castling, and en passant always receive dedicated tests.
- Scores are signed integer centipawns from the side-to-move perspective; positive favors that side.
- Neural scores are finite and clamped below the separate mate range. Mate distance prefers faster wins/slower losses. Draws score zero.
- Normalize Stockfish targets before storage. Score scale/cap changes require versioning and golden tests.

## Data and reproducibility

- Split by stable game ID and prevent normalized positions crossing splits.
- Record seed, resolved config, dataset manifest, dependency/model/schema versions, teacher settings, and source commit.
- Never tune on test data; use it only after freezing a candidate.
- Generated data, models, logs, and large reports stay out of Git; only tiny fixtures are committed.
- Reject and count corrupt records rather than silently skipping them.
- Write manifests/checkpoints/models to temporary files, validate, then atomically rename.

## Dependencies and boundaries

- Target Python 3.11; use `python-chess`, PyTorch, NumPy, and pytest.
- Stockfish is offline-only. Pygame is legacy-only. New runtime modules import neither.
- Separate data generation, training, inference, search, UCI, and UI. Runtime cannot import datasets, optimizers, or Stockfish labeling.
- Search depends on `PositionEvaluator`, not PyTorch training internals. One encoder serves training and inference.
- Use typed configuration instead of mutable globals or hard-coded machine paths.
- Public APIs require type hints and docstrings specifying perspective, units, ownership, and failures.

## Errors and configuration

- Use typed errors for configuration, data, Stockfish, artifacts, encoding, and protocol boundaries.
- Reject invalid FEN, unknown config, contradictory limits, bad ranges, incompatible artifacts/shapes, and non-finite output before work begins.
- Never fall back to random weights. Failed UCI reload keeps the last valid model; startup without one fails readiness.
- CLI errors go to stderr with nonzero exit and no completed partial artifact. UCI stdout is protocol-only.
- Cancellation is normal and returns the last safe search result.
- Precedence is defaults, TOML, CLI. Stockfish labeling selects exactly one limit type.

## Artifact compatibility

- Artifacts declare architecture/schema versions, tensor dimensions, score scale, and checksum.
- Loaders validate metadata, weights, and golden-position inference.
- UCI accepts inference-only artifacts, not training checkpoints.
- Old versions require a tested migration or an actionable rejection.
- Preserve atomic `last`, validation-selected `best`, and immutable release artifacts.

## Tests and performance

- Every bug fix adds a regression test.
- Unit tests cover encoding, scores, config, artifacts, transposition bounds, and time allocation.
- Integration tests cover data generation, resume, checkpoint/export, search, UCI, and interruption.
- Maintain golden feature/model outputs plus tactical and terminal suites.
- Normal tests are offline; Stockfish tests are marked and skip clearly when unavailable. Random tests record seeds.
- Strength never excuses illegal moves, broken terminal state, protocol corruption, incompatibility, or missed time bounds.
- Profile before optimizing and record workload, hardware, versions, model hash, and before/after results.
- Bound transposition memory and check cancellation often enough for the time tolerance.
- Quantization, native code, incremental caching, and threading require isolated correctness tests and measured justification.

## Prohibited shortcuts

- Training on validation/test records or splitting one game across datasets.
- Reporting training loss alone as engine strength or claiming informal Elo.
- Returning unchecked model moves or using different training/runtime encoders.
- Silent fallback for missing/corrupt artifacts or hard-coded local paths.
- Making Stockfish, GPU, Pygame, or the imported custom board a new runtime dependency.
