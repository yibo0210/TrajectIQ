import json

import pytest

from trajectiq.agent import run_task
from trajectiq.data import TASKS
from trajectiq.run import VERSIONS
from trajectiq.trace_io import compare_trace_collections, load_trace_collection


def _write_trace_export(path, version_name: str) -> None:
    payload = {
        "version": version_name,
        "runs": [run_task(version=VERSIONS[version_name], task=task) for task in TASKS],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_external_trace_collections_use_the_core_regression_evaluator(tmp_path) -> None:
    baseline_path = tmp_path / "baseline.json"
    candidate_path = tmp_path / "candidate.json"
    _write_trace_export(baseline_path, "baseline")
    _write_trace_export(candidate_path, "regression")

    report = compare_trace_collections(
        baseline_path=baseline_path,
        candidate_path=candidate_path,
    )

    assert report.baseline.version == "baseline"
    assert report.candidate.version == "regression"
    assert len(report.regressions) == 10


def test_trace_collection_rejects_an_invalid_run(tmp_path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({"version": "candidate", "runs": [{"task_id": "refund_001"}]}), encoding="utf-8")

    with pytest.raises(ValueError, match="string answer"):
        load_trace_collection(path)
