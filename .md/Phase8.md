# Phase 8 — Glass Chess Website

## Status

**Implementation complete; interactive browser/device QA remains before closure (2026-07-14).**

The Aurora Glass MVP, authoritative Python game service, compiled local website, launcher,
package data, and automated tests are implemented. The real Phase 7 model has completed an
end-to-end packaged-wheel smoke game. Phase 8 remains open until the visual, keyboard, touch,
responsive, and complete-game checks below are performed in a browser.

Phase 8 adds a local-first browser interface for playing against the frozen neural chess
engine. It replaces the earlier desktop/Pygame proposal. The website must be a structured
frontend application with separate components and styles, not a single HTML file and not UI
markup embedded in Python.

## Goal

Provide a polished, responsive chess website that starts with one command, loads the existing
CPU model, and lets a human complete a legal game against the neural engine. The design should
take functional inspiration from the outer repository's `game.py`—a clear board, selection,
promotion, check, and human-versus-engine flow—without importing its custom board, evaluator,
search, or blocking event loop.

The website is a post-v1 adapter. It must not change the trained model, search rules, score
contract, UCI behavior, or Phase 7 release evidence.

## Locked product scope

The initial website supports:

- human versus neural engine;
- play as White, Black, or a randomly selected side;
- engine think-time presets: Fast (250 ms), Normal (1 second), and Strong (3 seconds);
- click-to-move and drag-to-move interaction;
- legal destination indicators;
- selected-square, previous-move, and check highlighting;
- promotion choice for knight, bishop, rook, or queen;
- standard algebraic move history;
- engine-thinking state with depth, nodes, and elapsed time;
- automatic board orientation toward the human plus manual board flipping;
- undo of one complete turn, returning control to the human;
- resignation and complete game-over reporting;
- correct castling, en passant, checkmate, stalemate, repetition, fifty-move, and
  insufficient-material handling;
- responsive desktop, tablet, and mobile layouts;
- actionable model/backend loading and connection errors; and
- device-local preferences for side, think time, and orientation.

## Necessary controls

Only four controls remain visible during a game:

1. **New Game** — opens the side and think-time choices.
2. **Undo Turn** — cancels active search and restores the position before the latest human
   move.
3. **Flip Board** — reverses board orientation without changing game state.
4. **Resign** — asks for confirmation and ends the current game.

Contextual controls appear only when needed:

- the promotion dialog offers knight, bishop, rook, and queen;
- the game-over dialog offers Play Again and Review Board; and
- a failed startup offers Retry and a concise model-path correction.

The browser's normal window controls provide close, back, and refresh behavior. The website
does not add redundant buttons for those actions.

## Explicit non-goals

The first Phase 8 release does not include:

- accounts, authentication, profiles, or cloud synchronization;
- public hosting or internet-accessible engine compute;
- online or local multiplayer;
- engine-versus-engine tournaments;
- opening books or tablebases;
- training, labeling, checkpoint, or model-management controls;
- multiple engine selection;
- chat, leaderboards, achievements, or social features;
- a theme editor;
- a chess database or general PGN library;
- an evaluation bar or hint system;
- persistent server-side game storage; or
- changes to the legacy engine files.

Public deployment is a separate future decision because it requires a continuously running
Python/PyTorch service, resource limits, security controls, monitoring, and hosting costs.

## Visual design

### Direction

Use a restrained dark glassmorphism system rather than making every surface transparent.
Gameplay contrast and piece recognition take priority over decorative blur.

- Background: deep navy-to-black gradient with slow, subtle violet, cyan, and emerald light
  blooms.
- Glass panels: translucent dark fill, 20–28 px backdrop blur, one-pixel light border, and
  soft layered shadow.
- Board frame: glass outer shell with an opaque-enough board surface for reliable contrast.
- Accent: cool cyan for active state, violet for secondary state, green for ready/success,
  amber for warning, and red for check/error/resignation.
- Typography: modern sans-serif with tabular numerals for clocks and search statistics.
- Motion: 150–200 ms transitions; no continuous motion except a subtle engine-thinking
  indicator and very slow background light movement.
- Corners: consistent 16–24 px radii on major glass surfaces and 10–12 px on controls.

### Accessibility rules

- Text and interactive controls must meet WCAG AA contrast.
- Meaning cannot depend on transparency, blur, animation, or color alone.
- Every control needs a visible keyboard focus state and accessible name.
- Board squares must be keyboard reachable; Enter/Space selects and moves.
- Legal destinations need a shape indicator in addition to a color change.
- Reduced-motion preferences disable background and move animations.
- Touch targets are at least 44 by 44 CSS pixels.
- Status changes such as check, engine thinking, and game over use an ARIA live region.

## Responsive layout

### Desktop

Use a two-column first viewport:

```text
┌─────────────────────────────────────────────────────────┐
│  NEURAL CHESS                         ● Model ready      │
├──────────────────────────────────┬──────────────────────┤
│                                  │  YOUR TURN           │
│                                  │  Playing as White    │
│          CHESSBOARD              │                      │
│                                  │  Move history        │
│                                  │  1. e4      e5       │
│                                  │  2. Nf3     Nc6      │
│                                  │                      │
│                                  │  Depth · Nodes · Time│
│                                  │  New / Undo / Flip   │
│                                  │  Resign              │
└──────────────────────────────────┴──────────────────────┘
```

The board receives the majority of available height. The right glass panel contains status,
move history, compact search statistics, and controls.

### Tablet

Keep the board above or beside a narrower control panel depending on orientation. Controls
may wrap, but the move history must remain scrollable without shrinking the board excessively.

### Mobile

Place the board immediately below the compact header. Put status and the four controls in a
bottom glass panel, with move history in a collapsible section. No horizontal page scrolling
is allowed.

## User flows

### Startup

1. The launcher starts the Python service and serves the compiled website.
2. The service validates and loads the inference-only model once on CPU.
3. The website shows a short loading state while connecting.
4. A successful connection opens the New Game dialog.
5. A missing or corrupt model produces an actionable error and no silent material fallback.

### New game

1. Choose White, Black, or Random.
2. Choose Fast, Normal, or Strong think time.
3. Create a fresh authoritative `chess.Board` on the backend.
4. Orient the board toward the human.
5. If the engine is White, start its first search without blocking the page.

### Human move

1. The frontend displays legal moves supplied by the backend.
2. The user clicks or drags a piece to a destination.
3. Promotion opens a choice before submission.
4. The backend validates and applies the move with `python-chess`.
5. The updated FEN, move list, legal moves, check state, and outcome are returned.
6. If the game continues, the engine search begins.

### Engine move

1. Search runs against a copied, history-preserving board.
2. Completed-iteration information is streamed to the frontend.
3. The final move is verified as legal and applied to the authoritative game.
4. The frontend animates the move and returns control to the human.

### Undo, restart, resign, and disconnect

- Undo and New Game cancel and join active search before changing state.
- Undo removes the engine reply and preceding human move when both exist; during an active
  reply search it removes only the pending human move.
- Resign asks for confirmation, cancels active search, and records the correct result.
- A disconnected browser cancels its active search after a short cleanup timeout.
- Every search result carries a generation identifier; stale results are discarded.

## Architecture

### Boundary

`python-chess` remains the only rule and legal-move authority. The browser renders state and
sends user intent but never declares a move legal, determines a result, or evaluates a
position. The backend calls the existing `SearchEngine` directly through a thin service; it
does not duplicate UCI parsing or import training and Stockfish modules.

### Proposed project structure

```text
chess_engine_nn/
  chess_engine_nn/
    web_api/
      __init__.py
      app.py                 HTTP/WebSocket application
      game_service.py        authoritative game lifecycle
      search_worker.py       cancellation and progress bridge
      schemas.py             versioned request/response contracts
      static.py              compiled frontend serving
  web/
    package.json
    tsconfig.json
    vite.config.ts
    src/
      components/
        ChessBoard.tsx
        GamePanel.tsx
        MoveHistory.tsx
        SearchStats.tsx
        GlassButton.tsx
        NewGameDialog.tsx
        PromotionDialog.tsx
        GameOverDialog.tsx
      hooks/
        useGameConnection.ts
        useBoardInteraction.ts
      services/
        gameClient.ts
        contracts.ts
      styles/
        tokens.css
        globals.css
        board.css
      App.tsx
      main.tsx
    public/
      pieces/
```

The website must remain componentized. Do not place the full interface, styles, and network
logic into one source file.

### Frontend

- React and TypeScript.
- Vite-based development and production build.
- Semantic DOM/CSS-grid board rather than a canvas, enabling accessibility and responsive
  sizing.
- Existing piece artwork may be copied into packaged web assets after its provenance is
  checked; runtime cannot reference the outer `imgs/` directory.
- Browser storage is limited to local preferences, never authoritative game state.
- No frontend chess-rules package is an authority. The server supplies legal moves and state.

### Backend

- FastAPI application with a single local game session for the initial release.
- Existing `load_evaluator`, `SearchEngine`, and `SearchLimits` APIs.
- One background search worker per active game and explicit cancellation.
- Pygame, Stockfish, datasets, optimizers, checkpoints, and legacy modules are not runtime
  dependencies.
- The backend binds to loopback by default and must not be publicly reachable accidentally.
- In-memory game state is sufficient; refresh may reconnect to the current local session, but
  server restart begins a new game.

## Service contract

Use versioned JSON messages. Exact URLs may change during implementation, but the logical
operations are fixed.

### HTTP operations

- `GET /api/v1/status` — readiness, model identity/checksum, and service version.
- `POST /api/v1/games` — create a game with human side and think time.
- `GET /api/v1/games/current` — obtain the current local game state.
- `POST /api/v1/games/current/moves` — submit one human UCI move and optional promotion.
- `POST /api/v1/games/current/undo` — cancel search and undo one turn.
- `POST /api/v1/games/current/resign` — cancel search and resign.
- `DELETE /api/v1/games/current` — cancel and discard the current game.

### WebSocket events

- `game.state` — authoritative board and game state changed.
- `search.started` — engine began thinking.
- `search.iteration` — completed depth, score, nodes, NPS, time, and PV.
- `search.completed` — verified engine move and updated state.
- `search.cancelled` — expected cancellation from undo/restart/resign.
- `game.over` — result and `python-chess` termination reason.
- `error` — recoverable, user-safe error code and message.

### Game-state response

At minimum, return:

- game identifier and monotonically increasing generation;
- FEN and side to move;
- human and engine colors;
- legal moves in UCI notation;
- SAN move history;
- previous move;
- check square when applicable;
- promotion choices when applicable;
- search status and latest completed iteration; and
- result and termination reason when complete.

## Search concurrency and correctness

- The UI thread and web event loop must never execute neural search directly.
- Search receives a copied board with full move history.
- Search progress crosses threads through a safe queue/callback bridge.
- The authoritative board changes only after a legal result from the active generation.
- New Game, Undo, Resign, shutdown, and disconnect signal cancellation.
- A late result from a cancelled generation is ignored.
- No user move is accepted while it is the engine's turn or after game over.
- All submitted moves and returned engine moves are checked against
  `python-chess.Board.legal_moves` immediately before application.

## Packaging and launch

Add a web optional dependency group so headless/UCI installs do not acquire web-server
dependencies unnecessarily. The production frontend is compiled before release and included
as package data in the wheel.

The target user command is:

```bash
chess-engine-nn-web \
  --model artifacts/models/phase7-full-2013-01.pt
```

Equivalent module execution should also work:

```bash
python3 -m chess_engine_nn.web_api \
  --model artifacts/models/phase7-full-2013-01.pt
```

The launcher should:

1. validate the model before reporting readiness;
2. bind only to `127.0.0.1` by default;
3. select or clearly report the port;
4. start the service;
5. open the default browser unless `--no-open` is supplied; and
6. shut down the search worker cleanly on interruption.

## Testing plan

### Backend unit tests

- create games for White, Black, and Random with a fixed seed;
- reject malformed, illegal, wrong-turn, and post-game moves;
- handle castling, en passant, promotion, check, mate, and every draw result;
- generate correct SAN history and legal-move lists;
- undo before search, during search, and after an engine response;
- cancel on New Game, resign, disconnect, and shutdown;
- reject stale search generations;
- preserve the authoritative board when search fails or is cancelled;
- reject missing/corrupt/incompatible model artifacts; and
- keep runtime imports free of training, Stockfish, and Pygame.

### Frontend tests

- square coordinate mapping in both orientations;
- click and drag interactions;
- legal-target, selection, prior-move, and check rendering;
- promotion dialog behavior;
- disabled controls during invalid states;
- move-history rendering and scrolling;
- new-game, undo, flip, resign, and retry flows;
- WebSocket reconnect and recoverable error display;
- keyboard navigation and reduced-motion behavior; and
- desktop, tablet, and mobile layout behavior.

### Integration and release tests

- start the real backend with the frozen Phase 7 model;
- complete at least one automated legal game through the web API;
- verify search cancellation under repeated undo/new-game actions;
- verify no stale move appears after cancellation;
- verify a human can complete a game through the browser;
- verify special moves and terminal dialogs end to end;
- verify frontend production build and Python wheel contents;
- install the final wheel in a clean Python 3.11 CPU environment;
- launch the packaged website with one command;
- confirm no GPU, Stockfish, dataset, training state, or Pygame is needed; and
- rerun all existing engine, tactical, timing, artifact, and UCI tests.

## Delivery sequence

### 8.1 — Specification and visual direction

- Lock this scope and update PRD/design/architecture language for a post-v1 web adapter.
- Create three comparable glassmorphism design previews before product implementation.
- Select one palette/layout direction and record its exact design tokens.
- Confirm piece-art provenance or select a distributable replacement set.

**Exit:** One approved desktop/mobile direction with no unresolved product-scope decisions.

### 8.2 — Authoritative game service

- Implement versioned schemas, game lifecycle, legal moves, SAN history, outcomes, and undo.
- Add deterministic fake-evaluator/search seams for ordinary offline tests.

**Exit:** Headless backend tests cover full rules and state transitions without frontend code.

### 8.3 — Asynchronous neural search bridge

- Integrate the frozen evaluator and `SearchEngine` worker.
- Add progress events, cancellation, generation checks, and shutdown behavior.

**Exit:** Real-model searches remain responsive and stale results cannot mutate game state.

### 8.4 — Website foundation and glass system

- Create the structured React/TypeScript application.
- Implement design tokens, background, glass surfaces, responsive layout, buttons, dialogs,
  and loading/error states.

**Exit:** Static desktop/mobile shells match the selected direction and accessibility rules.

### 8.5 — Board and game interaction

- Implement accessible board rendering, orientation, click/drag moves, legal indicators,
  highlights, promotion, move history, search stats, and game-over states.

**Exit:** A complete human-versus-engine game works in the development environment.

### 8.6 — Packaging and release validation

- Compile and package frontend assets.
- Add the one-command launcher and optional web dependencies.
- Run full backend/frontend/integration/browser and existing engine test suites.
- Build wheel/sdist and verify clean CPU installation.
- Update README files, Design, architecture, phases, Memory, and the Phase 8 report.

**Exit:** The Phase 8 completion criteria below all pass.

## Completion criteria

Phase 8 is complete only when:

1. One documented command opens the website in a browser.
2. A human can finish a complete game against the frozen neural model.
3. The backend and frontend never apply an illegal move.
4. Castling, en passant, promotion, checkmate, stalemate, repetition, fifty-move, and
   insufficient-material behavior pass maintained tests.
5. The website stays interactive during search.
6. Undo, New Game, Resign, disconnect, and shutdown cancel safely.
7. No stale search result can change a newer position.
8. White, Black, and Random side selection work.
9. Desktop, tablet, mobile, keyboard, touch, contrast, and reduced-motion checks pass.
10. The wheel contains the compiled website and licensed piece assets.
11. A clean Python 3.11 CPU installation launches with the Phase 7 model.
12. Gameplay requires no GPU, Stockfish, dataset, training checkpoint, or Pygame.
13. All pre-existing engine, tactical, timing, artifact, packaging, and UCI checks remain
    green.
14. Documentation reports actual implementation and verification results without unsupported
    strength or Elo claims.

## Risks and mitigations

- **PyTorch search blocks the server:** isolate every search in a background worker and test
  cancellation races.
- **Late search mutates a restarted game:** require generation matching before applying a
  result.
- **Glass effects reduce readability:** use opaque-enough board colors, contrast tests, and
  reduced-transparency fallbacks.
- **Mobile board becomes too small:** prioritize board width and collapse secondary history.
- **Frontend duplicates chess rules:** backend supplies all authoritative legal moves and
  outcomes.
- **Piece assets fail after installation:** copy verified assets into package data and inspect
  wheel contents.
- **Optional UI expands the headless runtime:** keep web dependencies in a separate optional
  group and retain runtime-boundary tests.
- **Accidental public exposure:** bind to loopback by default and treat public hosting as a
  separate secured phase.

## Documentation required at closure

When Phase 8 actually passes its exit criteria, update:

- `README.md`;
- `chess_engine_nn/README.md`;
- `.md/prd.md`;
- `.md/Design.md`;
- `.md/architechture.md`;
- `.md/phases.md`;
- `.md/Memory.md`; and
- this file with final commands, dependency versions, screenshots, tests, limitations, and
  release evidence.

Do not mark Phase 8 complete from a static mockup or frontend-only demonstration. Completion
requires the real frozen model, authoritative game service, packaged website, and clean-install
verification.

## Implementation update — 2026-07-14

Implemented:

- a React/TypeScript frontend in `chess_engine_nn/web/`, split into board, game panel, new-game
  dialog, client service, types, and styles;
- the selected Aurora Glass visual direction with responsive desktop/mobile layouts,
  reduced-motion handling, visible focus states, and high-contrast board squares;
- click and drag moves, legal destinations, promotion, previous-move/check highlighting,
  board flip, SAN history, engine statistics, New Game, Undo Turn, and Resign;
- a FastAPI service in `chess_engine_nn/chess_engine_nn/web_api/` with REST and WebSocket state
  updates;
- `python-chess` as the sole rules authority, with generation-checked background searches and
  cooperative cancellation so stale searches cannot mutate a newer game;
- White, Black, and Random side selection plus 250 ms, 1 second, and 3 second think times;
- a compiled frontend bundled into the Python wheel and the `chess-engine-nn-web` launcher;
- maintained game-service, REST, WebSocket, cancellation, resignation, and packaging tests.

Automated verification passed:

- 102 Python tests;
- Ruff across the Python project;
- frontend lint and two rendered-output tests;
- production frontend and local embedded-frontend builds;
- wheel and source-distribution builds with compiled assets and console entry point; and
- isolated wheel launch with the real `phase7-full-2013-01.pt` model, serving the site and
  completing the move pair `e4 e5`.

Remaining closure work is an interactive browser pass for visual layout, full-game flow,
keyboard/touch behavior, responsive breakpoints, and reduced-motion behavior. Public hosting is
still intentionally outside Phase 8.
