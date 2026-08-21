"""YAML-driven release gates for deterministic TrajectIQ regressions."""

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from .attribution import attribute_regressions
from .regression import RegressionReport, compare_versions
from .run import VERSIONS


@dataclass(frozen=True)
class GateViolation:
    rule: str
    severity: str
    actual: float | int
    threshold: float | int
    message: str


@dataclass(frozen=True)
class GateResult:
    status: str
    baseline: str
    candidate: str
    violations: tuple[GateViolation, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_gate_config(path: Path) -> dict[str, Any]:
    """Load and validate the small YAML gate configuration surface."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Gate configuration must be a YAML mapping.")
    thresholds = payload.get("thresholds")
    if not isinstance(thresholds, dict):
        raise ValueError("Gate configuration must contain a thresholds mapping.")
    return payload


def evaluate_gate(*, report: RegressionReport, config: dict[str, Any]) -> GateResult:
    """Evaluate candidate quality against configurable regression thresholds."""
    thresholds = config["thresholds"]
    violations: list[GateViolation] = []

    minimum_success_rate = thresholds.get("minimum_success_rate")
    if minimum_success_rate is not None and report.candidate.success_rate < minimum_success_rate:
        violations.append(GateViolation("minimum_success_rate", "block", report.candidate.success_rate, minimum_success_rate, "Candidate task success rate is below the required minimum."))

    maximum_success_rate_drop = thresholds.get("maximum_success_rate_drop")
    success_rate_drop = report.baseline.success_rate - report.candidate.success_rate
    if maximum_success_rate_drop is not None and success_rate_drop > maximum_success_rate_drop:
        violations.append(GateViolation("maximum_success_rate_drop", "block", success_rate_drop, maximum_success_rate_drop, "Candidate task success rate regressed beyond the allowed drop."))

    minimum_tool_selection_accuracy = thresholds.get("minimum_tool_selection_accuracy")
    if minimum_tool_selection_accuracy is not None and report.candidate.tool_selection_accuracy < minimum_tool_selection_accuracy:
        violations.append(GateViolation("minimum_tool_selection_accuracy", "block", report.candidate.tool_selection_accuracy, minimum_tool_selection_accuracy, "Candidate tool selection accuracy is below the required minimum."))

    maximum_critical_task_regressions = thresholds.get("maximum_critical_task_regressions")
    critical_regressions = sum(item.is_critical for item in report.regressions)
    if maximum_critical_task_regressions is not None and critical_regressions > maximum_critical_task_regressions:
        violations.append(GateViolation("maximum_critical_task_regressions", "block", critical_regressions, maximum_critical_task_regressions, "Candidate regressed on more critical tasks than allowed."))

    maximum_task_regressions = thresholds.get("maximum_task_regressions")
    if maximum_task_regressions is not None and len(report.regressions) > maximum_task_regressions:
        violations.append(GateViolation("maximum_task_regressions", "warning", len(report.regressions), maximum_task_regressions, "Candidate has more task regressions than the warning threshold."))

    metric_rules = (
        ("maximum_average_latency_ms", report.candidate.average_latency_ms, "block", "Candidate average latency is above the allowed threshold."),
        ("maximum_average_total_tokens", report.candidate.average_total_tokens, "warning", "Candidate average token usage is above the allowed threshold."),
        ("maximum_average_cost_usd", report.candidate.average_cost_usd, "warning", "Candidate average estimated cost is above the allowed threshold."),
    )
    for rule, actual, severity, message in metric_rules:
        threshold = thresholds.get(rule)
        if threshold is not None and actual > threshold:
            violations.append(GateViolation(rule, severity, actual, threshold, message))

    status = "BLOCK" if any(item.severity == "block" for item in violations) else "WARNING" if violations else "PASS"
    return GateResult(status=status, baseline=report.baseline.version, candidate=report.candidate.version, violations=tuple(violations))


def render_markdown(*, result: GateResult, report: RegressionReport) -> str:
    """Render a CI-friendly release decision with diagnostic detail."""
    lines = ["# TrajectIQ Release Gate", "", f"Status: **{result.status}**", f"Baseline: {result.baseline}", f"Candidate: {result.candidate}", ""]
    if not result.violations:
        lines.append("All configured quality thresholds passed.")
        return "\n".join(lines) + "\n"
    lines.extend(["## Gate findings", ""])
    lines.extend(f"- [{item.severity.upper()}] {item.rule}: actual={item.actual}, threshold={item.threshold}. {item.message}" for item in result.violations)
    attributions = attribute_regressions(baseline=VERSIONS[result.baseline], candidate=VERSIONS[result.candidate])
    if attributions:
        lines.extend(["", "## First-error diagnostics", ""])
        lines.extend(f"- {item.task_id}: {item.category} at step {item.step} ({item.baseline_span} -> {item.candidate_span})" for item in attributions)
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a TrajectIQ release gate")
    parser.add_argument("--config", type=Path, default=Path("release-gate.yaml"))
    parser.add_argument("--baseline", choices=VERSIONS, default="baseline")
    parser.add_argument("--candidate", choices=VERSIONS, default="regression")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    config = load_gate_config(args.config)
    report = compare_versions(baseline=VERSIONS[args.baseline], candidate=VERSIONS[args.candidate])
    result = evaluate_gate(report=report, config=config)
    rendered = json.dumps(result.to_dict(), indent=2) if args.format == "json" else render_markdown(result=result, report=report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="" if rendered.endswith("\n") else "\n")
    if result.status == "BLOCK":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
