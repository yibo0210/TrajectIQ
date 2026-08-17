from agentguard.regression import compare_versions, render_markdown
from agentguard.run import VERSIONS


def test_regression_report_identifies_refund_tasks_that_degraded() -> None:
    report = compare_versions(
        baseline=VERSIONS["baseline"], candidate=VERSIONS["regression"]
    )

    assert report.baseline.success_rate == 1.0
    assert report.candidate.success_rate == 4 / 6
    assert [item.task_id for item in report.regressions] == ["refund_001", "refund_002"]
    assert all(item.is_critical is (item.task_id == "refund_001") for item in report.regressions)


def test_fixed_version_has_no_regressions_against_baseline() -> None:
    report = compare_versions(baseline=VERSIONS["baseline"], candidate=VERSIONS["fixed"])

    assert report.regressions == ()
    assert report.candidate.success_rate == 1.0


def test_markdown_report_contains_metric_and_task_details() -> None:
    report = compare_versions(
        baseline=VERSIONS["baseline"], candidate=VERSIONS["regression"]
    )

    rendered = render_markdown(report)

    assert "Task success rate" in rendered
    assert "refund_001" in rendered
    assert "query_order, search_policy" in rendered
    assert "estimate_delivery" in rendered

