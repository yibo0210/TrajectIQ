"""First-error localization and deterministic failure attribution."""

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .agent import run_task
from .data import TASKS
from .models import AgentVersion, Task
from .regression import compare_versions
from .run import VERSIONS


@dataclass(frozen=True)
class FailureAttribution:
    task_id: str
    category: str
    step: int
    baseline_span: str | None
    candidate_span: str | None
    reason: str
    confidence: float
    is_critical: bool


def _get_tool_spans(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [span for span in result["spans"] if span["kind"] == "tool"]


def locate_first_error(*, task: Task, baseline_result: dict[str, Any], candidate_result: dict[str, Any]) -> FailureAttribution:
    """Find the first deterministic trajectory difference for one regressed task."""
    baseline_tools = _get_tool_spans(baseline_result)
    candidate_tools = _get_tool_spans(candidate_result)
    maximum_steps = max(len(baseline_tools), len(candidate_tools))

    for index in range(maximum_steps):
        baseline_span = baseline_tools[index] if index < len(baseline_tools) else None
        candidate_span = candidate_tools[index] if index < len(candidate_tools) else None
        step = index + 2
        if baseline_span is None:
            return FailureAttribution(
                task_id=task.task_id,
                category="tool_selection_error",
                step=step,
                baseline_span=None,
                candidate_span=candidate_span["name"] if candidate_span else None,
                reason="Candidate invoked an extra tool that is absent from the baseline trajectory.",
                confidence=1.0,
                is_critical=task.critical,
            )
        if candidate_span is None:
            return FailureAttribution(
                task_id=task.task_id,
                category="tool_selection_error",
                step=step,
                baseline_span=baseline_span["name"],
                candidate_span=None,
                reason="Candidate omitted a tool required by the baseline trajectory.",
                confidence=1.0,
                is_critical=task.critical,
            )
        if baseline_span["name"] != candidate_span["name"]:
            return FailureAttribution(
                task_id=task.task_id,
                category="tool_selection_error",
                step=step,
                baseline_span=baseline_span["name"],
                candidate_span=candidate_span["name"],
                reason="Candidate selected a different tool at the first divergent step.",
                confidence=1.0,
                is_critical=task.critical,
            )
        if baseline_span["input"] != candidate_span["input"]:
            return FailureAttribution(
                task_id=task.task_id,
                category="tool_argument_error",
                step=step,
                baseline_span=baseline_span["name"],
                candidate_span=candidate_span["name"],
                reason="Candidate passed different arguments to the same tool.",
                confidence=1.0,
                is_critical=task.critical,
            )
        if candidate_span["error"]:
            return FailureAttribution(
                task_id=task.task_id,
                category="tool_execution_error",
                step=step,
                baseline_span=baseline_span["name"],
                candidate_span=candidate_span["name"],
                reason=f"Candidate tool failed with {candidate_span['error']}.",
                confidence=1.0,
                is_critical=task.critical,
            )

    return FailureAttribution(
        task_id=task.task_id,
        category="generation_error",
        step=len(candidate_tools) + 2,
        baseline_span="final_answer",
        candidate_span="final_answer",
        reason="Tool trajectory matches the baseline but final answer expectations failed.",
        confidence=0.9,
        is_critical=task.critical,
    )


def attribute_regressions(*, baseline: AgentVersion, candidate: AgentVersion, tasks: tuple[Task, ...] = TASKS) -> tuple[FailureAttribution, ...]:
    """Attribute every baseline-pass to candidate-fail task regression."""
    report = compare_versions(baseline=baseline, candidate=candidate, tasks=tasks)
    tasks_by_id = {task.task_id: task for task in tasks}
    attributions: list[FailureAttribution] = []
    for regression in report.regressions:
        task = tasks_by_id[regression.task_id]
        attributions.append(
            locate_first_error(
                task=task,
                baseline_result=run_task(version=baseline, task=task),
                candidate_result=run_task(version=candidate, task=task),
            )
        )
    return tuple(attributions)


def render_markdown(attributions: tuple[FailureAttribution, ...]) -> str:
    """Render shareable first-error attribution details."""
    lines = ["# TrajectIQ First-Error Diagnostics", ""]
    if not attributions:
        lines.append("No regressions to diagnose.")
    else:
        lines.extend(
            f"- {item.task_id} | step {item.step} | {item.category} | {item.baseline_span or 'none'} -> {item.candidate_span or 'none'} | {item.reason}"
            for item in attributions
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose first errors in TrajectIQ regressions")
    parser.add_argument("--baseline", choices=VERSIONS, default="baseline")
    parser.add_argument("--candidate", choices=VERSIONS, default="regression")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    attributions = attribute_regressions(baseline=VERSIONS[args.baseline], candidate=VERSIONS[args.candidate])
    rendered = json.dumps([asdict(item) for item in attributions], indent=2) if args.format == "json" else render_markdown(attributions)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="" if rendered.endswith("\n") else "\n")


if __name__ == "__main__":
    main()
