"""Run the local Phase 8 web API and optionally open its frontend."""

import argparse
import threading
import webbrowser
from pathlib import Path

import uvicorn

from chess_engine_nn.web_api.app import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True, help="inference-only model artifact")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--static-dir", type=Path, help="compiled website directory")
    parser.add_argument("--no-open", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    static_dir = args.static_dir
    if static_dir is None:
        packaged = Path(__file__).with_name("static")
        source_build = Path(__file__).resolve().parents[2] / "web" / "local-dist"
        static_dir = packaged if packaged.is_dir() else source_build
    app = create_app(model_path=args.model, static_dir=static_dir)
    if not args.no_open:
        url = f"http://{args.host}:{args.port}"
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
