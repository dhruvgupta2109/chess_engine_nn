import json

from chess_engine_nn.cli import main


def test_doctor_json_is_machine_readable(capsys) -> None:
    assert main(["doctor", "--json"]) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["ok"] is True
    assert result["feature_schema_version"] == 1
    assert result["feature_count"] == 781
    assert captured.err == ""
