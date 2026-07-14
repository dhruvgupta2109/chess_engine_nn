# Phase 6 Performance and Ablation Report

## Scope and interpretation

Phase 6 profiles the CPU reference implementation, removes measured runtime waste, and records controlled search ablations. It does not claim playing strength or Elo: the reproducibility model uses deterministic untrained weights with the production `781 -> 256 -> 32 -> 1` shape. Strength conclusions require the larger trained corpus and frozen candidate planned for Phase 7.

The maintained machine-readable report is generated into the ignored path `artifacts/reports/phase6-reference.json` by:

```bash
cd chess_engine_nn
python3 tools/benchmark_phase6.py \
  --micro-iterations 2000 \
  --repeats 5 \
  --search-depth 3 \
  --output artifacts/reports/phase6-reference.json
```

## Reference environment

- Apple M4 MacBook Air, 10 cores, 24 GB memory, arm64;
- macOS 26.5.1;
- Python 3.11.4;
- python-chess 1.11.2;
- NumPy 2.4.4;
- PyTorch 2.13.0 with four default CPU threads;
- deterministic seed `20260713`;
- 208,449-parameter production-shaped model;
- model weight SHA-256 `08b98d8719e52034128b0ede8a6bbf1eb407967a26370d2a20bee00dfa10482a`;
- Phase 6 base commit `8e136f4`.

## Profile findings and changes

The original depth-2 profile spent about two-thirds of search time in `can_claim_threefold_repetition()` from positions where a claim was mathematically impossible. Single-position encoding also rebuilt a `piece_map` and ran a general NumPy uniqueness pass for features that are unique by construction.

Implemented changes:

1. Guard threefold and fifty-move claim checks with the minimum required reversible-ply counters. The seven-ply threefold-claim boundary has a dedicated regression test.
2. Build piece features from python-chess bitboards while preserving the exact schema-v1 ordering. Golden fixtures plus a seeded 100-position reference comparison prove equivalence.
3. Use a one-dimensional, inference-only path for individual neural evaluations while retaining the batch path. Single and batch centipawn results are tested for exact equality.
4. Compute repetition sensitivity once per transposition node, skip the expensive check before four reversible plies, and reuse the result for both probe and store decisions.

Paired before/after measurements used the same process, model, board, seed, seven repeats, warm-up, and identical 387-node search:

| Measurement | Before | After | Change |
|---|---:|---:|---:|
| Neural evaluations/second | 18,844 | 28,684 | +52.2% |
| Depth-2 search time | 37.496 ms | 12.235 ms | -67.4% |
| Depth-2 search NPS | 10,321 | 31,630 | 3.06x |
| Nodes / best move / score | 387 / `g2g3` / -284 cp | 387 / `g2g3` / -284 cp | unchanged |

The maintained final component run measured approximately 142k active encodings/s, 135k dense encodings/s, 29k neural evaluations/s, 61k legal-move lists/s, 544k push/pop pairs/s, 124k position hashes/s, and 23 million transposition probes/s. Timing is descriptive and varies with system load.

## Search ablations

The fixed middlegame at depth 3 produced:

| Variant | Nodes | Time | Best move / score | Decision |
|---|---:|---:|---|---|
| Baseline | 20,852 | 1,021.6 ms | `d3h7` / 478 cp | retain |
| Lexical move ordering | 34,168 | 1,723.8 ms | `d3h7` / 478 cp | reject; 64% more nodes |
| No transposition table | 29,364 | 1,421.5 ms | `d3h7` / 478 cp | reject; 41% more nodes |
| No quiescence extension | 7,247 | 194.5 ms | `d3h7` / 478 cp | reject; faster but removes tactical horizon protection |
| Full alpha-beta window | 20,014 | 955.9 ms | `d3h7` / 478 cp | do not tune from untrained weights |

The maintained material tactical control remains 3/3. Search correctness, terminal handling, time limits, and UCI behavior remain release-blocking regardless of speed.

## Rejected runtime experiments

- TorchScript improved an isolated forward-only loop but reduced the real evaluator pipeline from about 28k to 21k evaluations/s and emitted PyTorch 2.13 deprecation warnings. It was reverted.
- Dynamic int8 linear quantization is unavailable in this Apple PyTorch build (`NoQEngine`) and was not added.
- Changing PyTorch CPU threads from four to one or two produced no material single-position benefit, so the global runtime setting remains untouched.
- Incremental accumulators and native code are not justified by this profile. Neural evaluation remains the largest cost, but the Python reference now meets the current search/time gates without adding compatibility risk.
