import threading
import time

import chess

from chess_engine_nn.evaluator import MaterialEvaluator
from chess_engine_nn.search import SearchEngine
from chess_engine_nn.web_api import GameActionError, GameService


def test_new_game_exposes_authoritative_state_and_rejects_illegal_move() -> None:
    service = GameService(MaterialEvaluator())
    state = service.new_game("white", 250)

    assert state["phase"] == "human_turn"
    assert state["human_color"] == "white"
    assert state["captures"] == {"white": [], "black": []}
    assert state["material_advantage"] == {"white": 0, "black": 0}
    assert "e2e4" in state["legal_moves"]
    try:
        service.submit_move("e2e5")
    except GameActionError as error:
        assert "illegal" in str(error)
    else:
        raise AssertionError("illegal move was accepted")


def test_human_move_gets_engine_reply_and_undo_returns_to_human() -> None:
    service = GameService(MaterialEvaluator())
    service.new_game("white", 250)
    moved = service.submit_move("e2e4")
    assert moved["phase"] == "engine_thinking"

    deadline = time.monotonic() + 3
    while service.state()["phase"] == "engine_thinking" and time.monotonic() < deadline:
        time.sleep(0.01)
    replied = service.state()
    assert replied["phase"] == "human_turn"
    assert len(replied["moves"]) == 2

    undone = service.undo_turn()
    assert undone["phase"] == "human_turn"
    assert undone["moves"] == []
    assert undone["fen"] == chess.STARTING_FEN


def test_black_cannot_undo_before_making_a_move() -> None:
    service = GameService(MaterialEvaluator())
    service.new_game("black", 250)

    deadline = time.monotonic() + 3
    while service.state()["phase"] == "engine_thinking" and time.monotonic() < deadline:
        time.sleep(0.01)

    before = service.state()
    assert before["phase"] == "human_turn"
    assert len(before["moves"]) == 1

    try:
        service.undo_turn()
    except GameActionError as error:
        assert "make a move" in str(error)
    else:
        raise AssertionError("undo was accepted before Black made a move")

    after = service.state()
    assert after["fen"] == before["fen"]
    assert after["phase"] == "human_turn"


class SlowSearchEngine(SearchEngine):
    def search(self, board, limits, observer=None, stop_event=None):
        while stop_event is not None and not stop_event.is_set():
            time.sleep(0.005)
        return super().search(
            board,
            limits,
            observer=observer,
            stop_event=threading.Event(),
        )


def test_undo_cancels_pending_reply_and_stale_result_cannot_apply() -> None:
    evaluator = MaterialEvaluator()
    service = GameService(
        evaluator,
        search_factory=lambda: SlowSearchEngine(evaluator),
    )
    service.new_game("white", 250)
    service.submit_move("e2e4")
    undone = service.undo_turn()

    assert undone["fen"] == chess.STARTING_FEN
    assert undone["moves"] == []
    time.sleep(0.05)
    assert service.state()["fen"] == chess.STARTING_FEN


def test_resign_records_color_relative_result() -> None:
    service = GameService(MaterialEvaluator())
    service.new_game("white", 250)

    state = service.resign()

    assert state["phase"] == "game_over"
    assert state["result"] == "0-1"
    assert state["termination"] == "white_resigned"


def test_capture_summary_tracks_normal_and_en_passant_captures() -> None:
    service = GameService(MaterialEvaluator())
    with service._lock:
        service._board = chess.Board()
        for move in ("e2e4", "a7a6", "e4e5", "d7d5", "e5d6"):
            service._board.push_uci(move)
        captures, advantage = service._capture_summary_locked()

    assert captures == {"white": ["p"], "black": []}
    assert advantage == {"white": 1, "black": 0}

    with service._lock:
        service._board.push_uci("e7d6")
        captures, advantage = service._capture_summary_locked()

    assert captures == {"white": ["p"], "black": ["P"]}
    assert advantage == {"white": 0, "black": 0}
