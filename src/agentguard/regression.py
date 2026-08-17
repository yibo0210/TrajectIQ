"""Version comparison and regression reporting for TrajectIQ."""

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .agent import run_task
from .data import TASKS
from .models import AgentVersion, Task
from .run import VERSIONS


@dataclass(frozen=True)
class TaskEvaluation:
    task_id: str
    is_success: bool
    has_correct_tools: bool
    has_correct_arguments: bool
    has_expected_answer: bool
    is_critical: bool
    actual_tools: tuple[str, ...]
    expected_tools: tuple[str, ...]


@dataclass(frozen=True)
class VersionMetrics:
    version: str
    task_count: int
    success_rate: float
    tool_selection_accuracy: float
    tool_argument_accuracy: float
    answer_coverage: float
    average_steps: float
    critical_task_success_rate: float


@dataclass(frozen=True)
class RegressionReport:
    dataset: str
    baseline: VersionMetrics
    candidate: VersionMetrics
    regressions: tuple[TaskEvaluation, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["deltas"] = {
            "success_rate": self.candidate.success_rate - self.baseline.success_rate,
            "tool_selection_accuracy": self.candidate.tool_selection_accuracy - self.baseline.tool_selection_accuracy,
            "tool_argument_accuracy": self.candidate.tool_argument_accuracy - self.baseline.tool_argument_accuracy,
            "answer_coverage": self.candidate.answer_coverage - self.baseline.answer_coverage,
        }
        return payload


def _get_tool_spans(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [span for span in result["spans"] if span["kind"] == "tool"]


def evaluate_task(*, task: Task, result: dict[str, Any]) -> TaskEvaluation:
    tool_spans = _get_tool_spans(result)
    actual_tools = tuple(span["name"] for span in tool_spans)
    has_correct_tools = actual_tools == task.expected_tools
    has_correct_arguments = has_correct_tools and all(
        span["input"] == task.expected_arguments.get(span["name"], span["input"])
        for span in tool_spans
    )
    has_expected_answer = all(
        expected_text.lower() in result["answer"].lower()
        for expected_text in task.expected_answer_contains
    )
    return TaskEvaluation(
        task_id=task.task_id,
        is_success=has_correct_tools and has_correct_arguments and has_expected_answer,
        has_correct_tools=has_correct_tools,
        has_correct_arguments=has_correct_arguments,
        has_expected_answer=has_expected_answer,
        is_critical=task.critical,
        actual_tools=actual_tools,
        expected_tools=task.expected_tools,
    )


def evaluate_version(*, version: AgentVersion, tasks: tuple[Task, ...] = TASKS) -> tuple[VersionMetrics, tuple[TaskEvaluation, ...]]:
    runs = tuple((task, run_task(version=version, task=task)) for task in tasks)
    evaluations = tuple(evaluate_task(task=task, result=result) for task, result in runs)
    task_count = len(evaluations)
    critical_evaluations = tuple(item for item in evaluations if item.is_critical)
    metrics = VersionMetrics(
        version=version.name,
        task_count=task_count,
        success_rate=sum(item.is_success for item in evaluations) / task_count,
        tool_selection_accuracy=sum(item.has_correct_tools for item in evaluations) / task_count,
        tool_argument_accuracy=sum(item.has_correct_arguments for item in evaluations) / task_count,
        answer_coverage=sum(item.has_expected_answer for item in evaluations) / task_count,
        average_steps=sum(len(_get_tool_spans(result)) for _, result in runs) / task_count,
        critical_task_success_rate=(sum(item.is_success for item in critical_evaluations) / len(critical_evaluations) if critical_evaluations else 1.0),
    )
    return metrics, evaluations


def compare_versions(*, baseline: AgentVersion, candidate: AgentVersion, tasks: tuple[Task, ...] = TASKS, dataset_name: str = "customer_support_v1") -> RegressionReport:
    baseline_metrics, baseline_evaluations = evaluate_version(version=baseline, tasks=tasks)
    candidate_metrics, candidate_evaluations = evaluate_version(version=candidate, tasks=tasks)
    baseline_by_task_id = {item.task_id: item for item in baseline_evaluations}
    regressions = tuple(item for item in candidate_evaluations if baseline_by_task_id[item.task_id].is_success and not item.is_success)
    return RegressionReport(dataset=dataset_name, baseline=baseline_metrics, candidate=candidate_metrics, regressions=regressions)


def render_markdown(report: RegressionReport) -> str:
    def format_percent(value: float) -> str:
        return f"{value * 100:.1f}%"

    metric_rows = (
        ("Task success rate", report.baseline.success_rate, report.candidate.success_rate),
        ("Tool selection accuracy", report.baseline.tool_selection_accuracy, report.candidate.tool_selection_accuracy),
        ("Tool argument accuracy", report.baseline.tool_argument_accuracy, report.candidate.tool_argument_accuracy),
        ("Answer coverage", report.baseline.answer_coverage, report.candidate.answer_coverage),
        ("Critical task success rate", report.baseline.critical_task_success_rate, report.candidate.critical_task_success_rate),
    )
    lines = ["# TrajectIQ Regression Report", "", f"Baseline: {report.baseline.version}", f"Candidate: {report.candidate.version}", f"Dataset: {report.dataset}", "", "## Metrics", "", "| Metric | Baseline | Candidate | Delta |", "| --- | ---: | ---: | ---: |"]
    lines.extend(f"| {label} | {format_percent(baseline_value)} | {format_percent(candidate_value)} | {format_percent(candidate_value - baseline_value)} |" for label, baseline_value, candidate_value in metric_rows)
    lines.extend(["", "## Regressions", ""])
    if not report.regressions:
        lines.append("No task regressions detected.")
    else:
        lines.extend(f"- {item.task_id}: expected {', '.join(item.expected_tools)}, got {', '.join(item.actual_tools)}" for item in report.regressions)
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two TrajectIQ Agent versions")
    parser.add_argument("--baseline", choices=VERSIONS, default="baseline")
    parser.add_argument("--candidate", choices=VERSIONS, default="regression")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()
    report = compare_versions(baseline=VERSIONS[args.baseline], candidate=VERSIONS[args.candidate])
    rendered = json.dumps(report.to_dict(), ensure_ascii=False, indent=2) if args.format == "json" else render_markdown(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="" if rendered.endswith("\n") else "\n")


if __name__ == "__main__":
    main()
