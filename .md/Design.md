# Product Design

## Scope

No graphical interface was required for v1. Its product surfaces remain a developer CLI, a UCI
process, structured logs, reports, and artifacts. Phase 8 adds an optional local website without
changing those headless contracts. Pygame/images remain legacy baseline components only.

## CLI behavior

- Every command has `--help`, inputs/defaults/outputs, and an example.
- Overwrite requires `--force`; otherwise create a new run or stop.
- Long commands show phase, completed/total work, elapsed time, rate, and ETA when calculable.
- Success summarizes run ID, outputs, counts, metrics, and elapsed time. Failures identify the file/field/record/tool and corrective action.
- Exit 0 means complete success. Invalid or incomplete work returns nonzero.
- Human text is default. `--json` emits one versioned final JSON result to stdout while progress goes to stderr.
- Meaning cannot rely on color. Any future ANSI color honors `NO_COLOR` and non-interactive terminals.

Planned verbs are `doctor`, `generate-data`, `train`, `evaluate-model`, `export`, `search`, and `benchmark`. Once implemented, command/flag changes require compatibility documentation.

## Progress and reports

- Data generation reports games, candidates, labeled/skipped counts by reason, Stockfish rate, shards, time, and resume state.
- Training reports epoch, losses, MAE, RMSE, sign accuracy, learning rate, best epoch, examples, elapsed time, and ETA; `last` and `best` are clearly distinguished.
- Search reports depth/seldepth, centipawn or mate score, nodes, NPS, elapsed time, transposition hits, and principal variation.
- Match reports include W/D/L, score percentage, color balance, openings, seeds, limits, adjudication, model hashes, hardware, and versions.

## Logging and UCI

- Logs contain timestamp, severity, component, run ID, and event. Default is `INFO`; `--verbose` enables `DEBUG`, and `--quiet` limits console noise.
- Optional file logs use JSON Lines. Do not log full datasets, tensors, or per-node search events normally.
- UCI stdout contains protocol messages only; logs and diagnostics go to stderr/file.
- UCI sends standard `info` after completed iterations and stays responsive to `stop` and `quit` through one cooperative background search worker.
- Startup readiness requires a validated inference model. Runtime `ModelPath` reload is transactional, and malformed commands or failed option changes are diagnosed on stderr without corrupting protocol output or valid engine state.

## Accessibility and portability

All workflows are keyboard-operated, scriptable, readable in narrow/redirected terminals, and independent of color/animation. Paths remain portable and defaults fit a CPU-only laptop.

## Phase 8 website

The selected Aurora Glass direction uses a deep navy background with restrained cyan, violet,
and emerald light blooms; translucent dark panels; a high-contrast teal board; and cyan active
states. The desktop layout prioritizes the board on the left and a compact status/history panel
on the right, collapsing cleanly on narrow screens. Motion is brief and honors reduced-motion.

Only New Game, Undo Turn, Flip Board, and Resign remain visible during play. Side and think-time
choices belong in New Game; promotion and game-over actions appear contextually. The frontend is
split into React/TypeScript components and styles rather than embedded in Python or one HTML
file.

The browser integrates through a thin service around `SearchEngine`. It cannot duplicate chess
rules, import training internals, manipulate tensors, or own authoritative search state. The
service publishes legal moves, outcomes, SAN history, and search progress over REST/WebSocket.
