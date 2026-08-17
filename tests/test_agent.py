from trajectiq.agent import run_task
from trajectiq.data import TASKS
from trajectiq.run import VERSIONS


def _get_task(task_id: str):
    return next(task for task in TASKS if task.task_id == task_id)


def test_baseline_refund_task_uses_order_and_policy_tools() -> None:
    result = run_task(version=VERSIONS["baseline"], task=_get_task("refund_001"))

    tool_names = [span["name"] for span in result["spans"] if span["kind"] == "tool"]

    assert tool_names == ["query_order", "search_policy"]
    assert "3-5" in result["answer"]


def test_regression_refund_task_selects_the_wrong_tool_reproducibly() -> None:
    result = run_task(version=VERSIONS["regression"], task=_get_task("refund_001"))

    tool_spans = [span for span in result["spans"] if span["kind"] == "tool"]

    assert [span["name"] for span in tool_spans] == ["estimate_delivery"]
    assert tool_spans[0]["input"] == {"order_id": "A1001"}
    assert result["answer"] == "Unable to process this request."
