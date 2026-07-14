# Product Requirements Document

## Product definition

Build a reproducible, CPU-first chess engine whose evaluation is learned from Stockfish supervision. It combines an NNUE-style scalar evaluator with alpha-beta search and exposes UCI for chess clients and automated matches. This is an engine and ML project; a UI is out of scope.

## Users and use cases

Primary users are developers training and improving models, players launching the engine through UCI, and experimenters running repeatable CPU matches. They must be able to generate labeled data, train/resume/export a model, evaluate a FEN, search under limits, use UCI, and compare checkpoints.

## Functional requirements

### Chess correctness

- `python-chess` is authoritative for legal moves, checks, promotions, castling, en passant, draw state, FEN, PGN, and UCI notation.
- Every returned move must be in `board.legal_moves`.
- Resolve mate, stalemate, insufficient material, repetition, and fifty-move outcomes before neural evaluation.

### Encoding

- Encode twelve piece/color types across 64 squares as sparse piece-square features.
- Canonicalize relative to the side to move so one network handles both colors.
- Add side to move, four castling flags, and legal en-passant state.
- Keep move counters for rule handling but omit them from v1 model inputs.
- Version the exact square mapping and use one encoder in training and inference.

### Dataset generation

- Stream PGNs, sample configurable non-terminal positions, and reject malformed or duplicate positions.
- Label with a configured Stockfish executable using exactly one configured depth, node, or time limit.
- Store FEN, side-to-move centipawn score, optional mate distance, game ID, ply, result, teacher settings, and schema version.
- Clip mate targets to a finite training cap while retaining `mate_in` metadata.
- Write append-safe shards and a manifest; interrupted work resumes without duplicating completed records.
- Split by stable game ID with a default 90/5/5 train/validation/test ratio. Positions from one game cannot cross splits.
- Never commit generated datasets or Stockfish binaries.

### Training and artifacts

- Use PyTorch and a compact `256-32-1` NNUE-style network suitable for frequent CPU inference.
- Train a bounded scalar value using Huber loss over clipped Stockfish centipawns.
- Support deterministic seeds, batch size, learning rate, epochs, early stopping, checkpoint cadence, resume, and CPU selection.
- Checkpoints contain model/optimizer state, progress, metrics, resolved config, feature/model versions, dataset ID, dependency versions, seed, and source commit when available.
- Select `best` by validation loss; never tune on the held-out test set.
- Report MAE, RMSE, sign accuracy outside a configured draw band, and loss by score bucket.
- Export a validated inference-only artifact containing no optimizer or dataset state.

### Evaluation and search

- Evaluate one `chess.Board` during search and batches during offline validation.
- Return finite signed integer centipawns from the side-to-move perspective, clamped below the mate range.
- Use iterative-deepening negamax, alpha-beta pruning, quiescence for captures/promotions/check evasions, a bounded transposition table, and deterministic move ordering.
- Move ordering uses the transposition move, promotions, captures, killer moves, and history scores.
- Search detects terminal/draw states on the active path and uses mate-distance scores.
- Support aspiration windows after the first full-window iteration, with a full-window retry on failure.
- Stop cooperatively for time, nodes, or UCI `stop` and return the last completed iteration.
- Report depth, selective depth, nodes, NPS, score, elapsed time, transposition hits, and principal variation.
- V1 search is single-threaded. `Threads` exists for UCI compatibility but only accepts `1`.

### UCI

- Implement `uci`, `isready`, `ucinewgame`, `position`, `go`, `stop`, `setoption`, and `quit`.
- Support `go depth`, `go nodes`, `go movetime`, and clock fields `wtime`, `btime`, `winc`, `binc`, and `movestogo`.
- Expose `ModelPath`, `Hash`, `Threads`, and `Seed` options.
- Stdout contains only UCI; diagnostics and logs use stderr or a file.
- A failed model update preserves the last validated model. `bestmove 0000` is used only with no legal moves.

### Configuration and storage

- Use checked-in TOML examples for development, training, runtime, and benchmarks.
- Precedence is built-in defaults, TOML, then explicit CLI flags; unknown keys are errors.
- Separate and ignore raw data, processed shards, checkpoints, models, logs, and reports.
- Store reproducibility and compatibility metadata with every artifact.

## Performance and strength

- Gameplay requires neither GPU nor Stockfish; default model load must complete within five seconds on the reference laptop.
- Establish evaluator throughput and search NPS empirically in Phase 4 rather than inventing an unmeasured gate.
- For `go movetime T`, return within `max(50 ms, 5% of T)` after budget on an idle reference laptop, excluding model load.
- Beat a material-only predictor on held-out MAE and sign accuracy.
- Score above 50% against the imported depth-2 engine over at least 200 balanced-color games using identical openings, fixed seeds, and recorded adjudication.
- Tactical or legality regressions block release even if match results improve.

## Reliability

- Fixed-seed sampling, splitting, smoke training, and benchmarks reproduce inputs and materially equivalent metrics under the same versions.
- Fail clearly on missing files, malformed config/FEN/PGN, unavailable Stockfish, incompatible checkpoints, or non-finite output.
- Long tasks are resumable where practical and partial artifacts are never marked complete.
- Ordinary tests run offline and without Stockfish; Stockfish tests are explicitly marked integration tests.

## Acceptance criteria

1. Encoding tests cover orientation, symmetry, castling, en passant, promotions, and metadata.
2. Dataset tests cover streaming, rejection, deduplication, deterministic game splits, score conversion, and resume.
3. Fixed-seed CPU smoke training lowers validation loss and round-trips checkpoint and inference artifacts.
4. Held-out metrics beat the material baseline and are stored with the model report.
5. Search returns only legal moves, passes terminal/tactical suites, preserves input boards, and respects stop limits.
6. Required UCI transcript tests pass with clean protocol stdout.
7. The candidate passes the controlled 200-game baseline match.
8. A clean Python 3.11 CPU environment installs, loads the model, runs UCI, and searches a sample position.

## Non-goals for v1

- Graphical, web, or mobile UI.
- Policy move prediction, MCTS, reinforcement learning, or self-play.
- Distributed/multi-GPU training or hosted services.
- Multi-threaded search, opening books, or tablebases.
- Reimplementing chess rules or claiming Elo without a controlled rating pool.

## Post-v1 Phase 8 extension

Phase 8 adds an optional local browser interface after the v1 engine contract was frozen. It is
a React/TypeScript client over a thin FastAPI REST/WebSocket service, keeps `python-chess`
authoritative, and loads the same inference-only artifact used by CLI/UCI. It does not add
training controls, hosted compute, accounts, multiplayer, or a second chess-rules
implementation. The detailed acceptance and verification criteria live in `Phase8.md`.
