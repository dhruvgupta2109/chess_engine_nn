import json
from pathlib import Path

from chess_engine_nn.cli import main


def test_doctor_json_is_machine_readable(capsys) -> None:
    assert main(["doctor", "--json"]) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["ok"] is True
    assert result["feature_schema_version"] == 1
    assert result["feature_count"] == 781
    assert captured.err == ""


def test_training_evaluation_and_export_commands(training_dataset, tmp_path: Path, capsys) -> None:
    checkpoints = tmp_path / "checkpoints"
    assert (
        main(
            [
                "--config",
                "configs/dev.toml",
                "train",
                "--dataset",
                str(training_dataset),
                "--output",
                str(checkpoints),
                "--json",
            ]
        )
        == 0
    )
    trained = json.loads(capsys.readouterr().out)
    assert trained["ok"]

    assert (
        main(
            [
                "--config",
                "configs/dev.toml",
                "evaluate-model",
                "--dataset",
                str(training_dataset),
                "--checkpoint",
                trained["best_checkpoint"],
                "--json",
            ]
        )
        == 0
    )
    evaluated = json.loads(capsys.readouterr().out)
    assert evaluated["count"] == 6

    model_path = tmp_path / "models" / "nnue.pt"
    assert (
        main(
            [
                "export",
                "--checkpoint",
                trained["best_checkpoint"],
                "--output",
                str(model_path),
                "--json",
            ]
        )
        == 0
    )
    exported = json.loads(capsys.readouterr().out)
    assert exported["model"] == str(model_path)
    assert model_path.is_file()
    assert (
        main(
            [
                "--config",
                "configs/dev.toml",
                "search",
                "--model",
                str(model_path),
                "--depth",
                "1",
                "--json",
            ]
        )
        == 0
    )
    searched = json.loads(capsys.readouterr().out)
    assert searched["best_move"]


def test_search_command_returns_legal_move(capsys) -> None:
    assert main(["--config", "configs/dev.toml", "search", "--depth", "1", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["best_move"]
    assert result["depth"] == 1
    assert result["nodes"] > 0
