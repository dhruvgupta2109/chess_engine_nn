"""Capture the untouched parent repository engine's initial-position baseline."""

import contextlib
import io
import json
import platform
import sys
import time
from pathlib import Path

LEGACY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(LEGACY_ROOT))

from board import Board  # noqa: E402
from evaluate import Evaluate  # noqa: E402
from search import Search  # noqa: E402


def main() -> int:
    board = Board()
    search_output = io.StringIO()
    started = time.perf_counter()
    with contextlib.redirect_stdout(search_output):
        score, move = Search().minmax(board, -1, 2)
    result = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "initial_legal_white": len(board.get_all_legal_moves(1)),
        "initial_legal_black": len(board.get_all_legal_moves(-1)),
        "initial_eval_white_to_move": Evaluate().evaluate(board, 1),
        "search_side": "black",
        "search_depth": 2,
        "score": score,
        "move_tuple": move,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "diagnostic_lines": len(search_output.getvalue().splitlines()),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
