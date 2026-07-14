# Delivery Phases

Phases complete in order. Exit criteria must pass on a clean Python 3.11 CPU environment, and `Memory.md` must be updated after every phase.

## Phase 0 — Specification and baseline capture

**Status: Complete (2026-07-13)**

- Approve the PRD, architecture, rules, design, and package contract.
- Document reproducible imported-engine launch, fixed openings, match settings, timing, and behavior without changing it.

**Exit:** Documents agree on score perspective, feature schema, APIs, model, and gates; the baseline comparison is reproducible; no planned implementation is marked complete.

## Phase 1 — Foundation

**Status: Complete (2026-07-13)**

- Add installable package/dependency metadata, typed TOML configuration, seed utilities, errors, logging, ignore rules, and tests.
- Establish `python-chess`, implement feature-schema v1 with golden fixtures, and add a material-only evaluator behind the final protocol.
- Implement `doctor` for environment/configuration checks.

**Exit:** Clean editable install; encoding symmetry/castling/en-passant/promotion tests; documented score signs; `doctor` reports optional Stockfish availability.

## Phase 2 — Dataset generation

**Status: Complete (2026-07-13)**

- Stream PGNs, create stable game IDs, sample positions, and integrate Stockfish with one explicit limit mode.
- Normalize centipawn/mate targets, write resumable shards/manifests, split by game, and deduplicate across splits.
- Benchmark JSONL and select the production sharded format behind the same reader API before scaling.

**Exit:** Fixed fixtures reproduce records/splits; invalid input is reported; resume creates no duplicates; no game or normalized position leaks across splits.

## Phase 3 — Baseline neural model

**Status: Complete (2026-07-13)**

- Implement the `256-32-1` NNUE-style PyTorch model, batching, Huber training, validation, early stopping, resume, metrics, and export.
- Add deterministic CPU smoke training and golden artifact round trips.

**Exit:** Loss decreases reproducibly; resumed and uninterrupted next steps agree; checkpoint/export evaluations match; neural held-out MAE and sign accuracy beat material-only.

## Phase 4 — Neural search

**Status: Complete (2026-07-13)**

- Implement terminal scoring, iterative-deepening negamax, alpha-beta, quiescence, mate distance, move ordering, observers, cancellation, and transposition bounds.
- Load inference without training or Stockfish imports; establish evaluator throughput and search NPS.

**Exit:** Only legal moves; input boards restored; terminal/tactical suites pass; depth/node/time/stop behavior meets the PRD.

## Phase 5 — UCI and time management

**Status: Complete (2026-07-13)**

- Implement the UCI loop and search worker, all required commands, clock allocation, options, clean protocol output, and transcript/race/reload tests.

**Exit:** Standard clients initialize/search/stop/new-game/quit; stdout is protocol-only; invalid reload preserves the prior model; time tolerance passes.

## Phase 6 — Strength and performance

**Status: Complete (2026-07-13)**

- Profile encoding, inference, board operations, quiescence, ordering, and transposition use.
- Run ablations and optimize measured bottlenecks; add incremental/quantized/native inference only when justified.

**Exit:** Every optimization has before/after CPU evidence and correctness tests; tactical and controlled match results improve or hold; reports include hardware, versions, model hash, limits, seeds, and commands.

## Phase 7 — Benchmark and release

**Status: Complete (2026-07-14)**

- Freeze model, openings, time control, adjudication, and seeds; run at least 200 balanced games against the imported engine.
- Evaluate the frozen model once on test; produce model report, sample configs, clean-install workflow, and checksums.

**Exit:** Above 50% baseline match score; held-out/tactical/legality/UCI tests pass; clean CPU install works; runtime needs no GPU, Stockfish, training state, data, or Pygame; no unsupported Elo claim.

## Phase 8 — Glass chess website

**Status: Implementation complete; interactive browser QA pending (2026-07-14)**

- Build the Aurora Glass React/TypeScript website and a thin local FastAPI adapter around the
  existing search engine.
- Keep `python-chess` authoritative, run search off the request thread, cancel safely, reject
  stale results, and package the compiled website with a one-command launcher.
- Complete desktop/mobile, keyboard, touch, reduced-motion, and full-game browser checks before
  marking the phase closed.

**Exit:** A human can finish a legal game against the frozen Phase 7 model from the packaged
website, all automated suites remain green, and the interactive browser checks pass.

Multi-threaded search, books/tablebases, advanced native inference, policy/value MCTS,
reinforcement/self-play, public hosting, and removal of legacy files remain separate future work.
