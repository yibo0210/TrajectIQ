from trajectiq.attribution import attribute_regressions, locate_first_error, render_markdown
from trajectiq.agent import run_task
from trajectiq.data import TASKS
from trajectiq.run import VERSIONS


def _get_task(task_id: str):
    return next(task for task in TASKS if task.task_id == task_id)


def test_attribution_locates_the_first_wrong_tool_selection() -> None:
    task = _get_task("refund_001")
    attribution = locate_first_error(
        task=task,
        baseline_result=run_task(version=VERSIONS["baseline"], task=task),
        candidate_result=run_task(version=VERSIONS["regression"], task=task),
    )

    assert attribution.category == "tool_selection_error"
    assert attribution.step == 2
    assert attribution.baseline_span == "query_order"
    assert attribution.candidate_span == "estimate_delivery"
    assert attribution.is_critical


def test_attribution_diagnoses_all_regressions() -> None:
    attributions = attribute_regressions(
        baseline=VERSIONS["baseline"], candidate=VERSIONS["regression"]
    )

    assert len(attributions) == 10
    assert [item.task_id for item in attributions[:2]] == ["refund_001", "refund_002"]
    assert {item.category for item in attributions} == {"tool_selection_error"}
    assert "refund_001" in render_markdown(attributions)


def test_fixed_version_produces_no_attributions() -> None:
    attributions = attribute_regressions(
        baseline=VERSIONS["baseline"], candidate=VERSIONS["fixed"]
    )

    assert attributions == ()
