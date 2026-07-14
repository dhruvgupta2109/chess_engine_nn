# Neural Chess website

This directory contains the structured React/TypeScript frontend for Phase 8. The browser
renders authoritative state from the local Python API; it does not implement chess rules.

## Development

From the nested Python project, start the real engine service:

```bash
python3 -m chess_engine_nn.web_api \
  --model artifacts/models/phase7-full-2013-01.pt \
  --no-open
```

Then run the frontend from this directory:

```bash
npm install
npm run dev
```

Open `http://localhost:3000`. The API listens only on `127.0.0.1:8765` by default.

## Builds

```bash
npm run lint
npm run build
npm run build:local
```

`build` validates the Sites-compatible frontend. `build:local` compiles the same React
components into `chess_engine_nn/web_api/static/`, allowing the Python launcher to serve the
entire local website at `http://127.0.0.1:8765`.
