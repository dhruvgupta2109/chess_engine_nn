from fastapi.testclient import TestClient

from chess_engine_nn.evaluator import MaterialEvaluator
from chess_engine_nn.web_api.app import create_app


def test_web_api_status_game_and_move_contract() -> None:
    app = create_app(evaluator=MaterialEvaluator())
    with TestClient(app) as client:
        status = client.get("/api/v1/status")
        assert status.status_code == 200
        assert status.json()["model"]["ready"]

        initial = client.get("/api/v1/games/current").json()
        assert initial["phase"] == "not_started"

        created = client.post(
            "/api/v1/games",
            json={"human_side": "white", "think_time_ms": 250},
        )
        assert created.status_code == 200
        assert created.json()["phase"] == "human_turn"

        illegal = client.post(
            "/api/v1/games/current/moves",
            json={"move": "e2e5"},
        )
        assert illegal.status_code == 409
        assert "illegal" in illegal.json()["detail"]


def test_websocket_starts_with_authoritative_state() -> None:
    app = create_app(evaluator=MaterialEvaluator())
    with TestClient(app) as client, client.websocket_connect("/api/v1/events") as websocket:
        event = websocket.receive_json()

    assert event["type"] == "game.state"
    assert event["payload"]["phase"] == "not_started"
