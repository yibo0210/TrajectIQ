"""Evaluate normalized execution traces exported by external Agent runtimes."""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .data import TASKS
from .dataset import load_dataset
from .models import Task
from .openinference import load_openinference_export
from .regression import RegressionReport, compare_results, render_markdown


@dataclass(frozen=True)
class TraceCollection:
    """A portable collection of Agent trajectories for one version."""

    version: str
    runs: dict[str, dict[str, Any]]


def _normalize_run(run: object, *, source: Path) -> tuple[str, dict[str, Any]]:
    if not isinstance(run, dict):
        raise ValueError(f"Every run in {source} must be a JSON object.")
    task_id = run.get("task_id")
    answer = run.get("answer")
    spans = run.get("spans")
    if not isinstance(task_id, str) or not task_id:
        raise ValueError(f"Every run in {source} must contain a non-empty task_id.")
    if not isinstance(answer, str):
        raise ValueError(f"Run {task_id} in {source} must contain a string answer.")
    if not isinstance(spans, list):
        raise ValueError(f"Run {task_id} in {source} must contain a spans array.")

    normalized_spans: list[dict[str, Any]] = []
    for index, span in enumerate(spans):
        if not isinstance(span, dict) or not isinstance(span.get("name"), str):
            raise ValueError(f"Run {task_id} span {index} in {source} must contain a name.")
        start_time_ms = span.get("start_time_ms", 0)
        end_time_ms = span.get("end_time_ms", start_time_ms)
        normalized_spans.append(
            {
                "step": span.get("step", index + 1),
                "kind": span.get("kind", "tool"),
                "name": span["name"],
                "input": span.get("input"),
                "output": span.get("output"),
                "error": span.get("error"),
                "start_time_ms": span.get("start_time_ms", 0),
                "end_time_ms": span.get("end_time_ms", span.get("start_time_ms", 0)),
                "duration_ms": span.get("duration_ms", max(0, end_time_ms - start_time_ms)),
                "prompt_tokens": span.get("prompt_tokens", 0),
                "completion_tokens": span.get("completion_tokens", 0),
                "cost_usd": span.get("cost_usd", 0.0),
            }
        )
    metrics = run.get("metrics")
    return task_id, {"task_id": task_id, "answer": answer, "spans": normalized_spans, "metrics": metrics or {}}


def load_trace_collection(path: Path) -> TraceCollection:
    """Load the public TrajectIQ trajectory JSON format from disk.

    The file shape is ``{"version": "...", "runs": [...]}``; each run needs
    ``task_id``, ``answer``, and ordered spans with ``kind`` and ``name``.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Trace collection {path} must be a JSON object.")
    version = payload.get("version")
    runs = payload.get("runs")
    if not isinstance(version, str) or not version:
        raise ValueError(f"Trace collection {path} must contain a version.")
    if not isinstance(runs, list):
        raise ValueError(f"Trace collection {path} must contain a runs array.")
    normalized_runs = dict(_normalize_run(run, source=path) for run in runs)
    if len(normalized_runs) != len(runs):
        raise ValueError(f"Trace collection {path} contains duplicate task_id values.")
    return TraceCollection(version=version, runs=normalized_runs)


def load_trace_input(path: Path, *, input_format: str) -> TraceCollection:
    """Load either the normalized TrajectIQ schema or an OpenInference export."""
    if input_format == "trajectiq":
        return load_trace_collection(path)
    if input_format == "openinference":
        version, runs = load_openinference_export(path)
        return TraceCollection(version=version, runs=runs)
    raise ValueError(f"Unsupported trace input format: {input_format}")


def compare_trace_collections(*, baseline_path: Path, candidate_path: Path, tasks: tuple[Task, ...] = TASKS, dataset_name: str = "customer_support_v1", input_format: str = "trajectiq") -> RegressionReport:
    """Compare two external trajectory exports with TrajectIQ's core evaluator."""
    baseline = load_trace_input(baseline_path, input_format=input_format)
    candidate = load_trace_input(candidate_path, input_format=input_format)
    expected_task_ids = {task.task_id for task in tasks}
    for label, collection in (("baseline", baseline), ("candidate", candidate)):
        missing = expected_task_ids - collection.runs.keys()
        if missing:
            raise ValueError(f"{label} trace collection is missing task IDs: {', '.join(sorted(missing))}")
    return compare_results(
        baseline_name=baseline.version,
        candidate_name=candidate.version,
        tasks=tasks,
        baseline_results=baseline.runs,
        candidate_results=candidate.runs,
        dataset_name=dataset_name,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two external TrajectIQ trajectory exports")
    parser.add_argument("--baseline-traces", type=Path, required=True)
    parser.add_argument("--candidate-traces", type=Path, required=True)
    parser.add_argument("--dataset-name", default="customer_support_v1")
    parser.add_argument("--dataset", type=Path, help="Optional JSONL dataset using the TrajectIQ task schema.")
    parser.add_argument("--dataset-version", default="custom")
    parser.add_argument("--input-format", choices=("trajectiq", "openinference"), default="trajectiq")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    dataset = load_dataset(args.dataset, name=args.dataset_name, version=args.dataset_version) if args.dataset else None
    report = compare_trace_collections(
        baseline_path=args.baseline_traces,
        candidate_path=args.candidate_traces,
        tasks=dataset.tasks if dataset else TASKS,
        dataset_name=dataset.identifier if dataset else args.dataset_name,
        input_format=args.input_format,
    )
    rendered = json.dumps(report.to_dict(), ensure_ascii=False, indent=2) if args.format == "json" else render_markdown(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="" if rendered.endswith("\n") else "\n")


if __name__ == "__main__":
    main()
