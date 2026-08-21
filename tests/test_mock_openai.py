from trajectiq.data import TASKS
from trajectiq.mock_openai import mock_completion
from trajectiq.openai_compatible import OpenAICompatibleClient, run_openai_task
from trajectiq.mock_openai import start_mock_server


def _task(task_id: str):
    return next(task for task in TASKS if task.task_id == task_id)


def test_mock_completion_returns_openai_tool_call_shape() -> None:
    response = mock_completion({"model": "mock", "messages": [{"role": "user", "content": "When will my refund arrive?"}]})

    tool_call = response["choices"][0]["message"]["tool_calls"][0]
    assert tool_call["function"]["name"] == "query_order"
    assert response["usage"]["total_tokens"] > 0


def test_mock_server_runs_existing_openai_client_without_api_key() -> None:
    server, _ = start_mock_server()
    try:
        client = OpenAICompatibleClient(
            api_key="not-real",
            model="trajectiq-mock",
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
        )
        result = run_openai_task(task=_task("refund_001"), client=client)
    finally:
        server.shutdown()
        server.server_close()

    tool_names = [span["name"] for span in result["spans"] if span["kind"] == "tool"]
    assert tool_names == ["query_order", "search_policy"]
    assert "3-5" in result["answer"]
    assert result["metrics"]["total_tokens"] > 0
    assert result["metrics"]["cost_usd"] > 0
