from trajectiq.openai_compatible import AssistantTurn, ToolCall, run_openai_task
from trajectiq.data import TASKS


class FakeChatClient:
    def __init__(self) -> None:
        self.turns = 0

    def complete(self, messages):
        self.turns += 1
        if self.turns == 1:
            return AssistantTurn(
                content="",
                tool_calls=(ToolCall("call-1", "query_order", {"order_id": "A1001"}),),
            )
        return AssistantTurn("Order A1001 is delivered and the refund is processing.")


def test_live_agent_runner_emits_evaluation_ready_tool_trajectory() -> None:
    result = run_openai_task(task=next(task for task in TASKS if task.task_id == "refund_006"), client=FakeChatClient())

    tool_spans = [span for span in result["spans"] if span["kind"] == "tool"]
    assert result["task_id"] == "refund_006"
    assert result["answer"].startswith("Order A1001")
    assert tool_spans[0]["name"] == "query_order"
    assert tool_spans[0]["input"] == {"order_id": "A1001"}
