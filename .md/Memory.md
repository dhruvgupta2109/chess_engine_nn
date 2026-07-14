# Project Memory

Update this handoff record after every completed phase or architectural decision. Never mark planned work complete.

## Current status

- **Active phase:** Phase 8 implementation complete; interactive browser/device QA pending.
- **Completed phases:** Phase 0 through Phase 7 (2026-07-14).
- **Current work:** The Aurora Glass local website, authoritative web game service, packaged
  launcher, and automated validation are implemented on top of the frozen v1 engine.
- **Next milestone:** Run the interactive full-game, responsive, keyboard, touch, and
  reduced-motion browser checks, then close Phase 8 if they pass.

## Imported baseline

- `board.py`: custom board and move logic.
- `evaluate.py`: handcrafted positional evaluation.
- `search.py`: minimax/alpha-beta, used at depth 2.
- `game.py`: Pygame human-versus-engine UI.
- `try_neuron.py`: educational OR-gate neuron.
- `imgs/`: legacy pieces.

The nested project now has packaging metadata, `python-chess`, NumPy, PyTorch 2.13.0, strict TOML configuration, feature-schema v1, material/neural evaluators, data/training/export modules, optimized search, asynchronous UCI, and release tooling. Stockfish 18 remains an offline labeling dependency only; CPU is the reproducibility and gameplay default. The local ignored release artifact is `artifacts/models/phase7-full-2013-01.pt`.

The baseline stays only for comparison. New modules must not build on its custom `Board`.

## Locked decisions

- Goal: strongest practical CPU-focused architecture for this Python project.
- Rules: `python-chess`; interface: UCI; persisted position boundary: FEN.
- Model: compact NNUE-style scalar evaluator trained in PyTorch from Stockfish labels.
- Search: single-threaded iterative-deepening negamax, alpha-beta, quiescence, transposition table, move ordering, and time control.
- Scores: signed centipawns from side-to-move perspective; mate is search-only.
- Schema v1: side-relative piece-square occupancy, side to move, castling, and legal en passant.
- Runtime needs no Stockfish, training data/state, GPU, or Pygame.
- Phase 8 UI is a local React client over a thin FastAPI service; `python-chess` remains the sole
  rules authority and searches are generation-checked background work.

## Risks

- The imported rules lack tests and are not an oracle.
- PyTorch at every leaf may limit NPS; Phases 4/6 decide from profiles whether incremental, quantized, or native inference is needed.
- Strength depends on representative data, teacher settings, leakage prevention, and scale.
- CPU labeling/training may be slow, requiring resume and smoke modes.
- V1 `Threads` is fixed at 1.
- Beating the baseline is not an Elo rating.
- `architechture.md` remains misspelled for compatibility.

## Immediate actions

1. Retain or back up the ignored release model and its checksum alongside the Phase 7 report.
2. Commit the Phase 7 harness, tests, configuration, and documentation.
3. Complete the Phase 8 interactive browser/device QA before marking it closed.

### Update 2026-07-13
- Phase/status: Phase 0 baseline capture pending; Phase 1 implementation started.
- Completed: packaging, dependencies, config, schema-v1 encoding, material evaluator, doctor CLI, and 16 tests.
- Verified by: `pytest`, Ruff, and JSON doctor execution.
- Active components: `config.py`, `encoding.py`, `evaluator.py`, `cli.py`, configs, and tests.
- Decisions/deviations: PyTorch remains an optional `training` dependency until neural training begins.
- Blockers/risks: Stockfish is not installed; baseline capture and PyTorch model remain pending.
- Next action: capture the imported baseline, then start Phase 2 records/sampling.
- Artifact/report paths: none yet.

### Update 2026-07-13 — Phase 0/1 closure
- Phase/status: Phase 0 and Phase 1 complete; ready for Phase 2.
- Completed: reproducible legacy capture, frozen eight-opening fixture/match protocol, deterministic seed utility, structured logging, directory-aware doctor output, and golden encoding fixtures.
- Verified by: legacy capture script, full pytest suite, Ruff, doctor JSON, build, and clean-install smoke checks.
- Active components: foundation package is stable; next work belongs to `data/` records, PGN, split, and label modules.
- Decisions/deviations: legacy Pygame image-path failure is documented and intentionally not fixed; PyTorch stays optional until Phase 3.
- Blockers/risks: Stockfish is absent locally and must be installed/configured before live label integration tests; Phase 2 unit work can proceed with a fake teacher.
- Next action: implement versioned dataset record and manifest contracts.
- Artifact/report paths: `.md/Baseline.md`, `tests/positions/baseline_openings.epd`, and `tests/positions/encoding_v1_golden.json`.

### Update 2026-07-13 — Phase 2 closure
- Phase/status: Phase 2 complete; ready for Phase 3.
- Completed: versioned records/manifests, streaming PGN sampling, stable game IDs, seeded game-level 90/5/5 splits, global position deduplication, Stockfish labels, atomic JSONL shards, resume/corruption handling, and `generate-data`.
- Verified by: 41 tests, Ruff, real Stockfish 18 perspective test, real end-to-end fixture generation, interrupted-run recovery, corrupt-shard rejection, and JSONL throughput benchmark.
- Active components: `data/records.py`, `pgn.py`, `split.py`, `label.py`, `generate.py`, CLI/configuration, and data tests.
- Decisions/deviations: sharded JSONL is the schema-v1 storage format; measured at about 363k writes/sec and 624k reads/sec for 25,000 representative records on the reference laptop.
- Repository correction: the nested project contained a self-referential `chess_engine_nn` Git link with no `.gitmodules` entry; it was replaced by the normal tracked Python package so source files survive commits and clones.
- Blockers/risks: the fixture corpus is only a smoke dataset; useful training requires user-supplied PGNs and substantially more labeled positions.
- Next action: install PyTorch and implement Phase 3 model/training artifacts.
- Artifact/report paths: ignored `data/processed/development-v1/` plus its manifest; benchmark tool at `tools/benchmark_jsonl.py`.

### Update 2026-07-13 — Phase 3 closure
- Phase/status: Phase 3 complete; ready for Phase 4.
- Completed: versioned `256-32-1` model, clipped activations and bounded output, indexed JSONL datasets, deterministic batching, Huber training, MAE/RMSE/sign/outcome/bucket metrics, early stopping, exact resume, atomic `last`/`best` checkpoints, inference-only export, checksum and golden-position validation, and train/evaluate/export CLI commands.
- Verified by: 56 tests, Ruff, CPU smoke training, exact resumed-versus-uninterrupted weights, held-out neural-versus-material comparison, corrupt-artifact rejection, and CLI round trips.
- Active components: `model.py`, `training/dataset.py`, `metrics.py`, `train.py`, `export.py`, neural evaluator loading, CLI, and training configuration.
- Decisions/deviations: PyTorch is now a core dependency because v1 gameplay inference uses it; CPU is the reproducibility default and MPS remains optional acceleration.
- Blockers/risks: the checked smoke corpus is intentionally tiny and proves mechanics only; a useful-strength release still requires a substantially larger PGN-derived training corpus.
- Next action: implement Phase 4 search against the `PositionEvaluator` boundary.
- Artifact/report paths: checkpoints/models remain ignored; tests create and validate temporary artifacts.

### Update 2026-07-13 — Phase 4 closure
- Phase/status: Phase 4 complete; ready for Phase 5.
- Completed: terminal/mate-distance scoring, iterative-deepening negamax, aspiration retries, alpha-beta, quiescence with check evasions, bounded exact/lower/upper transposition entries, mate-score normalization, deterministic capture/promotion/killer/history ordering, node/time/external stops, observers, PV/statistics, runtime-safe neural loading, and the `search` CLI.
- Verified by: 72 tests, Ruff, maintained mate/capture/promotion tactics, repetition/fifty-move/stalemate/checkmate cases, board-history preservation, deterministic fallback, stop/time bounds, artifact-boundary subprocess test, and CPU benchmark.
- Active components: `search.py`, `time_control.py`, `transposition.py`, `artifacts.py`, runtime evaluator, search CLI, tactical fixtures, and search benchmarks.
- Decisions/deviations: Python/PyTorch reference performance is about 18k single evaluations/sec and 9.9k depth-2 search NPS on the reference laptop using an untrained deterministic model.
- Blockers/risks: strength remains limited by the smoke model and Python inference overhead; Phase 6 profiling decides whether incremental/quantized inference is justified.
- Next action: implement Phase 5 UCI worker and protocol.
- Artifact/report paths: `tests/positions/search_tactics.json` and `tools/benchmark_search.py`.

### Update 2026-07-13 — Phase 5 closure
- Phase/status: Phase 5 complete; ready for Phase 6.
- Completed: asynchronous UCI command loop, single cooperative search worker, required commands and `go` fields, standard iteration info, shared clock allocation, transactional model reload, bounded hash replacement, fixed `Threads=1`, deterministic seed updates, and safe new-game clearing.
- Verified by: 84 tests, Ruff, malformed-command/stdout-purity coverage, transcript and stop/quit race tests, strict move-time tolerance, real neural UCI transcript, wheel/sdist build, and isolated wheel installation with module and console-entry UCI searches.
- Active components: `uci.py`, existing `search.py`/`time_control.py`, `tests/test_uci.py`, and the `chess-engine-nn-uci` entry point.
- Decisions/deviations: production UCI has no silent material fallback and fails readiness until a validated inference model is loaded; explicit evaluator injection remains available only as a development/test seam. Claimable draws with legal moves return a deterministic legal move rather than `0000`.
- Blockers/risks: the available deterministic smoke artifact proves runtime mechanics only; useful strength still requires a larger trained corpus and Phase 6 profiling/ablations.
- Next action: profile measured evaluator/search bottlenecks and optimize only with before/after correctness evidence.
- Artifact/report paths: runtime models/reports remain ignored; maintained UCI coverage is in `tests/test_uci.py`.

### Update 2026-07-13 — Phase 6 closure
- Phase/status: Phase 6 complete; ready for Phase 7.
- Completed: component profiling, exact bitboard feature encoding, guarded draw-claim checks, specialized single-position inference, repetition-safe transposition reuse, maintained benchmark/report tooling, and search-feature ablations.
- Verified by: paired seven-repeat before/after measurements, randomized seeded encoding equivalence, exact single/batch inference comparison, repetition boundary tests, all 3/3 maintained tactics, 89 tests, Ruff, wheel/sdist builds, isolated installation, and neural CLI/UCI smoke searches.
- Active components: optimized `encoding.py`, `evaluator.py`, and `search.py`; `tools/benchmark_phase6.py`; Phase 6 regression tests and report.
- Decisions/deviations: measured CPU performance improved about 52% for evaluation and 3.06x for the identical depth-2 search. TorchScript, dynamic int8, thread changes, and disabling strength-oriented search features were rejected. Untrained-weight ablations are not strength or Elo evidence.
- Blockers/risks: Phase 7 needs a substantially larger PGN-derived corpus and trained frozen candidate; the deterministic reference model proves mechanics and performance only.
- Next action: generate the release-scale dataset, train/freeze the candidate, then run the controlled 208-game baseline match and held-out release evaluation.
- Artifact/report paths: `.md/Phase6.md`, `tools/benchmark_phase6.py`, and ignored `artifacts/reports/phase6-reference.json`.

### Update 2026-07-14 — Phase 7 closure
- Phase/status: Phase 7 and the v1 release criteria are complete; Phase 8 is deferred.
- Completed: 1.73-million-position release dataset, CPU candidate training and validation selection, immutable inference export, one-time held-out test evaluation, controlled legacy match adapter, 208-game balanced-color match, release sample configuration, and model/release report.
- Verified by: neural validation MAE/sign accuracy beating material, frozen test metrics, 143–39–26 match result (78.125%), 56.25% sensitivity score after removing all legacy forfeits, zero candidate forfeits, 94 tests, Ruff, wheel/sdist builds, real neural UCI transcript, and isolated console-entry wheel search.
- Active components: frozen ignored model `artifacts/models/phase7-full-2013-01.pt`, `tools/run_legacy_match.py`, `configs/release.toml`, maintained tests, and `.md/Phase7.md`.
- Decisions/deviations: the imported engine made illegal moves in 104 games, all as White; the locked protocol records these as forfeits. The complete score and conservative no-forfeit sensitivity result are both reported. No Elo claim is made.
- Blockers/risks: model/data/match artifacts are intentionally ignored and require separate retention; the large-error validation bucket remains the weakest evaluation region; Phase 8 improvements are out of v1 scope.
- Next action: back up the release artifact, commit Phase 7, and select future work only if desired.

### Update 2026-07-14 — Phase 8 implementation
- Phase/status: implementation complete; interactive browser/device QA remains before closure.
- Completed: selected Aurora Glass React/TypeScript UI, authoritative FastAPI game service,
  REST/WebSocket updates, legal click/drag moves, promotion, SAN history, background neural
  search, cancellation/stale-result protection, New Game, full-turn Undo, Flip, Resign, compiled
  package assets, and one-command local launcher.
- Verified by: 102 Python tests, Ruff, frontend lint/tests, both production builds, wheel/sdist
  inspection, and an isolated-wheel real-model launch that served the UI and played `e4 e5`.
- Decisions/deviations: loopback/local-first only; Unicode chess glyphs avoid depending on the
  legacy image set; public hosting remains out of scope.
- Blockers/risks: interactive visual, responsive, keyboard, touch, reduced-motion, and full-game
  browser checks remain; the in-app browser automation surface was unavailable in this session.
- Next action: launch with `chess-engine-nn-web --model
  artifacts/models/phase7-full-2013-01.pt`, complete the browser checklist, then close Phase 8.
- Artifact/report paths: frontend source `web/`; service `chess_engine_nn/web_api/`; compiled
  package assets `chess_engine_nn/web_api/static/`; plan/status `.md/Phase8.md`.
- Artifact/report paths: tracked `.md/Phase7.md`; ignored model, dataset, checkpoint, match summary, and PGN under `artifacts/` and `data/processed/`.

## Update template

```markdown
### Update YYYY-MM-DD
- Phase/status:
- Completed:
- Verified by:
- Active components:
- Decisions/deviations:
- Blockers/risks:
- Next action:
- Artifact/report paths:
```

On phase completion, update `.md/phases.md` and ensure the root README reports actual rather than planned state.
