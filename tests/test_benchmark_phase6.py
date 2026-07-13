import json
import subprocess
import sys
from pathlib import Path


def test_phase6_benchmark_emits_versioned_reproducibility_report(tmp_path: Path) -> None:
    output = tmp_path / "phase6.json"
    process = subprocess.run(
        [
            sys.executable,
            "tools/benchmark_phase6.py",
            "--micro-iterations",
            "10",
            "--repeats",
            "1",
            "--search-depth",
            "1",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert process.returncode == 0, process.stderr
    report = json.loads(process.stdout)
    assert json.loads(output.read_text()) == report
    assert report["benchmark_schema_version"] == 1
    assert report["model"]["config"]["input_dim"] == 781
    assert len(report["model"]["weights_sha256"]) == 64
    assert {item["variant"] for item in report["middlegame_ablations"]} == {
        "baseline",
        "lexical_ordering",
        "no_transposition_table",
        "no_quiescence_extension",
        "full_window",
    }
    assert report["tactical_control"]["passed"] == report["tactical_control"]["total"]
