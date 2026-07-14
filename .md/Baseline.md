# Imported Engine Baseline

## Purpose

This captures the untouched imported engine used for migration and strength comparisons. It is not a correctness oracle and is not part of the new package runtime.

## Reproduction

From the outer repository root:

```bash
python3 chess_engine_nn/tools/capture_legacy_baseline.py
```

The script imports only the legacy `board.py`, `evaluate.py`, and `search.py`, suppresses their per-move diagnostic output, searches the initial position as black at fixed depth 2, and prints JSON. It does not alter legacy state or files.

The interactive launch remains:

```bash
python3 game.py
```

At capture time it failed during initialization because `game.py` searches for piece PNGs directly under the repository root while assets are under `imgs/`. This is a recorded legacy limitation, not a neural-engine blocker; legacy code was intentionally left unchanged.

## Captured result

Captured on 2026-07-13 using Python 3.11.4 on Apple Silicon macOS:

| Measurement | Result |
|---|---:|
| Initial legal moves, white | 20 |
| Initial legal moves, black | 20 |
| Handcrafted evaluation, white to move | 0.050000000000001765 pawns |
| Search side and depth | black, depth 2 |
| Selected legacy move tuple | `(0, 1, 2, 2, None)` (`b8c6`) |
| Search score | -0.049999999999996464 pawns |
| Wall time | 0.077156 seconds |
| Suppressed diagnostic lines | 138 |

Wall time is descriptive, not a stable performance threshold. Future reports must rerun the script and record hardware, versions, and multiple samples before comparing speed.

## Frozen opening and match protocol

The opening fixture is `chess_engine_nn/tests/positions/baseline_openings.epd`. It contains eight valid, unique, non-terminal positions spanning common open and closed setups.

The Phase 7 baseline match used:

- each opening twice per cycle with colors reversed;
- 13 cycles, producing 208 games;
- deterministic seed `20260713` for ordering and tie-breaking;
- the legacy engine at its fixed depth 2;
- the candidate at fixed depth 2 for the primary like-for-like comparison;
- a maximum of 150 plies;
- normal `python-chess` terminal/draw rules in the match harness;
- adjudication only at the ply cap, scored as a draw;
- a recorded candidate model checksum, dependency versions, hardware, W/D/L, color split, and per-game PGN.

Because the legacy engine is neither UCI-compatible nor based on `python-chess`, Phase 7 requires a narrow match adapter that translates positions/moves and verifies every legacy move before applying it. An illegal or untranslatable legacy move is a legacy forfeit and must be reported, never corrected silently.

The release gate remains a score above 50% for the neural candidate over all 208 games. This measures improvement over the imported baseline and is not an Elo claim.

The completed candidate scored 162.5/208 (78.125%). The legacy engine forfeited 104 games
after proposing illegal moves, all while playing White; excluding every one of those games
still leaves the candidate at 58.5/104 (56.25%). See the [Phase 7 report](Phase7.md) for the
full W/D/L, per-game artifacts, checksums, environment, and interpretation limits.
