# Phase 7 Model and Release Report

## Scope

Phase 7 trained and froze the v1 neural candidate, evaluated its held-out test split once,
ran the locked 208-game comparison with the imported engine, and verified the CPU release
workflow. The match demonstrates improvement over this repository's imported baseline; it
is not an Elo measurement.

## Corpus and training

The source is the Lichess standard-rated January 2013 database. Its downloaded `.zst` file
passed SHA-256 `aa40b3671fa3cf1072eb182892cd90b0e1e003a4a5943492f64b77e7f3fd1635`.
The decompressed PGN SHA-256 is
`8963b6a1620a0e9c77e5515a0744ec133e86869487188af047bb0a74400dee37`.

Stockfish 18 labeled sampled positions at depth 8 with one thread and 64 MiB hash. Seed
`20260713`, game-level 90/5/5 assignment, and cross-split normalized-position deduplication
produced:

| Item | Count |
|---|---:|
| Games read / malformed | 121,332 / 0 |
| Train positions | 1,557,221 |
| Validation positions | 86,213 |
| Test positions | 86,452 |
| Duplicate positions skipped | 109,549 |
| Terminal positions skipped | 10,973 |

The manifest SHA-256 is
`62f70244ff0a6eb6b1f8047b3db0e781a45d23ae4264919d5f05abccf48f2ff5`.
CPU training used the production `781 -> 256 -> 32 -> 1` model, batch size 64, learning rate
0.001, Huber delta 0.1, and early stopping patience 5. Training stopped after epoch 10; the
validation-selected checkpoint was epoch 5 with loss `0.002154201837581384`.

## Frozen model and metrics

The immutable inference artifact is
`artifacts/models/phase7-full-2013-01.pt` (ignored from Git by design).

- Artifact SHA-256: `7f0514f09bd1e84091e7fbf852412b6f86b80c41d240a9c7b5db166a031a8387`
- Weight SHA-256: `d6235f88143c0aca158125bdb0d0648c20f9647d923e564aac0dcb43da779f4f`
- Artifact schema: inference v1, feature schema v1, architecture v1
- Export metadata source commit: `375ac317f2bb8ac85ca279d8b3aa983100927cde`

Validation comparison before freezing:

| Evaluator | MAE cp | RMSE cp | Sign accuracy | Outcome accuracy |
|---|---:|---:|---:|---:|
| Neural candidate | 346.8515 | 1,390.1720 | 86.7405% | 66.6031% |
| Material-only | 396.9739 | 1,446.8542 | 71.3472% | 53.5427% |

The frozen test split was evaluated exactly once. It produced loss `0.002174905`, MAE
`349.6487` cp, RMSE `1,395.6952` cp, sign accuracy `86.4071%`, and outcome accuracy
`67.1593%`. Test bucket MAE was `89.1245` cp for 0–100, `133.9459` for 101–300,
`219.3035` for 301–900, and `4,997.8683` for 901+.

## Controlled legacy match

`tools/run_legacy_match.py` implements the protocol frozen in `Baseline.md`: eight openings,
13 cycles, reversed colors, seed `20260713`, both engines at depth 2, normal
`python-chess` terminal rules, and a 150-ply draw cap. Every translated legacy move is
checked against `python-chess` before it is applied.

```bash
python3 tools/run_legacy_match.py \
  --model artifacts/models/phase7-full-2013-01.pt \
  --openings tests/positions/baseline_openings.epd \
  --output artifacts/reports/phase7-legacy-match \
  --cycles 13 --max-plies 150 --depth 2 --seed 20260713
```

The candidate scored **143 wins, 39 draws, and 26 losses: 162.5/208 or 78.125%**. It played
104 games with each color and made no illegal moves. Its color-relative results were
52–39–13 as White and 91–0–13 as Black.

The imported engine made an illegal move in 104 games, all while playing White. As required
by the locked protocol, these were recorded as legacy forfeits and never corrected. For a
conservative sensitivity check, removing all 104 forfeits leaves 39 wins, 39 draws, and 26
losses: 58.5/104 or **56.25%**, still above the release threshold. Other terminations were
65 checkmates, 26 threefold repetitions, and 13 ply-cap draws.

- Opening fixture SHA-256: `dd03ecc5ecd6e9379289a8a1bcdb3db28823dafc4d2ad7e8c9a98155c1ff04e2`
- Match PGN SHA-256: `d26d61592a84e895e6dba02415038ab4f3ec25bf5f6a20c26580d68248ceab68`
- Machine report: `artifacts/reports/phase7-legacy-match/summary.json`
- Per-game record: `artifacts/reports/phase7-legacy-match/games.pgn`

The match ran on Apple arm64 with Python 3.11.4, python-chess 1.11.2, NumPy 2.4.4, and
PyTorch 2.13.0 in 1,442.4 seconds.

## Release verification

- 94 unit, integration, tactical, legality, timing, artifact, and UCI tests passed.
- Ruff passed with no findings.
- Wheel and source distribution built successfully.
- Wheel SHA-256: `81efc69576fc4d490f742c440c828dbdd62f4a2a208c7d8ea8eec381f4a69d9f`.
- Source distribution SHA-256: `433f30fc15ee69dc2e83a9972cbbfe6db2f4bef579a852d22b58301e2bd75059`.
- An isolated Python 3.11 wheel install loaded the frozen CPU model and returned a legal move
  through the `chess-engine-nn-uci` console entry point.
- A real source-tree UCI transcript reached depth 2, emitted protocol-only stdout, returned
  `bestmove d2d4`, and completed model load plus search in 0.593 seconds.
- Gameplay imports require no Stockfish, dataset, optimizer, training checkpoint, GPU, or
  Pygame.

Use the repository sample with:

```bash
python3 -m chess_engine_nn.cli --config configs/release.toml search --depth 4
python3 -m chess_engine_nn.uci --model artifacts/models/phase7-full-2013-01.pt
```

Before distributing a separately copied model, verify its artifact SHA-256 against this
report.
