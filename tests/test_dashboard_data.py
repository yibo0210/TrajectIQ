import json
from pathlib import Path

from trajectiq.dashboard_data import build_dashboard_data


def test_dashboard_data_contains_report_diagnosis_and_gate() -> None:
    config_path = Path(__file__).parents[1] / "release-gate.yaml"

    payload = build_dashboard_data(
        baseline_name="baseline",
        candidate_name="regression",
        gate_config=config_path,
    )

    assert payload["gate"]["status"] == "BLOCK"
    assert payload["report"]["candidate"]["version"] == "regression"
    assert payload["diagnoses"][0]["task_id"] == "refund_001"


def test_dashboard_data_can_be_serialized_as_json() -> None:
    config_path = Path(__file__).parents[1] / "release-gate.yaml"

    payload = build_dashboard_data(
        baseline_name="baseline",
        candidate_name="fixed",
        gate_config=config_path,
    )

    assert json.loads(json.dumps(payload))["gate"]["status"] == "PASS"
