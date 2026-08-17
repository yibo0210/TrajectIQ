import json

from agentguard.agent import run_task
from agentguard.data import TASKS
from agentguard.openinference import load_openinference_export
from agentguard.run import VERSIONS
from agentguard.trace_io import compare_trace_collections


def _write_openinference_export(path, version_name: str) -> None:
    spans = []
    for index, task in enumerate(TASKS):
        result = run_task(version=VERSIONS[version_name], task=task)
        trace_id = f"trace-{index:03d}"
        spans.append(
            {
                "trace_id": trace_id,
                "name": "agent_run",
                "start_time_unix_nano": index * 100,
                "attributes": {
                    "openinference.span.kind": "AGENT",
                    "trajectiq.task_id": task.task_id,
                    "output.value": result["answer"],
                },
            }
        )
        for step, span in enumerate(result["spans"], start=1):
            if span["kind"] != "tool":
                continue
            spans.append(
                {
                    "trace_id": trace_id,
                    "name": span["name"],
                    "start_time_unix_nano": index * 100 + step,
                    "attributes": {
                        "openinference.span.kind": "TOOL",
                        "tool.name": span["name"],
                        "input.value": json.dumps(span["input"]),
                        "output.value": json.dumps(span["output"]),
                    },
                }
            )
    path.write_text(json.dumps({"version": version_name, "spans": spans}), encoding="utf-8")


def test_openinference_export_adapts_to_the_same_regression_result(tmp_path) -> None:
    baseline_path = tmp_path / "baseline-otel.json"
    candidate_path = tmp_path / "candidate-otel.json"
    _write_openinference_export(baseline_path, "baseline")
    _write_openinference_export(candidate_path, "regression")

    report = compare_trace_collections(
        baseline_path=baseline_path,
        candidate_path=candidate_path,
        input_format="openinference",
    )

    assert len(report.regressions) == 10
    assert report.regressions[0].task_id == "refund_001"


def test_openinference_adapter_accepts_otlp_attribute_arrays(tmp_path) -> None:
    path = tmp_path / "otlp.json"
    path.write_text(
        json.dumps(
            {
                "version": "candidate",
                "spans": [
                    {
                        "traceId": "trace-1",
                        "name": "agent_run",
                        "attributes": [
                            {"key": "openinference.span.kind", "value": {"stringValue": "AGENT"}},
                            {"key": "trajectiq.task_id", "value": {"stringValue": "refund_001"}},
                            {"key": "output.value", "value": {"stringValue": "answer"}},
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    version, runs = load_openinference_export(path)

    assert version == "candidate"
    assert runs["refund_001"]["answer"] == "answer"
