from pathlib import Path

from trajectiq.gate import evaluate_gate, load_gate_config
from trajectiq.regression import compare_versions
from trajectiq.run import VERSIONS


CONFIG_PATH = Path(__file__).parents[1] / "release-gate.yaml"


def test_default_gate_blocks_regressed_candidate() -> None:
    config = load_gate_config(CONFIG_PATH)
    report = compare_versions(
        baseline=VERSIONS["baseline"], candidate=VERSIONS["regression"]
    )

    result = evaluate_gate(report=report, config=config)

    assert result.status == "BLOCK"
    assert {item.rule for item in result.violations} == {
        "minimum_success_rate",
        "maximum_success_rate_drop",
        "minimum_tool_selection_accuracy",
        "maximum_critical_task_regressions",
        "maximum_task_regressions",
    }


def test_default_gate_passes_fixed_candidate() -> None:
    config = load_gate_config(CONFIG_PATH)
    report = compare_versions(baseline=VERSIONS["baseline"], candidate=VERSIONS["fixed"])

    result = evaluate_gate(report=report, config=config)

    assert result.status == "PASS"
    assert result.violations == ()


def test_excess_noncritical_regressions_only_warn() -> None:
    config = {"thresholds": {"maximum_task_regressions": 1}}
    report = compare_versions(
        baseline=VERSIONS["baseline"], candidate=VERSIONS["regression"]
    )

    result = evaluate_gate(report=report, config=config)

    assert result.status == "WARNING"
    assert [item.rule for item in result.violations] == ["maximum_task_regressions"]


def test_production_metric_thresholds_are_enforced() -> None:
    report = compare_versions(baseline=VERSIONS["baseline"], candidate=VERSIONS["fixed"])
    result = evaluate_gate(
        report=report,
        config={"thresholds": {"maximum_average_latency_ms": 1}},
    )

    assert result.status == "BLOCK"
    assert result.violations[0].rule == "maximum_average_latency_ms"
