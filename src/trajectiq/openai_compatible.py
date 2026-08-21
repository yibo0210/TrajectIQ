"""A real OpenAI-compatible tool-calling Agent that emits TrajectIQ traces."""

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from opentelemetry import trace as trace_api

from .agent import call_tool
from .data import TASKS
from .models import Span, Task
from .metrics import aggregate_run_metrics, estimate_cost
from .telemetry import configure_tracing
from .mock_openai import start_mock_server


SYSTEM_PROMPT = """You are an e-commerce support Agent. Use the available tools when needed.
Give a concise customer-facing answer after tool execution. Do not invent order facts."""

TOOLS = [
    {"type": "function", "function": {"name": "query_order", "description": "Look up an order by ID.", "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}}},
    {"type": "function", "function": {"name": "search_policy", "description": "Read a refund or return policy.", "parameters": {"type": "object", "properties": {"topic": {"type": "string", "enum": ["refund_timeline", "return_opened"]}}, "required": ["topic"]}}},
    {"type": "function", "function": {"name": "estimate_delivery", "description": "Estimate order delivery by ID.", "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}}},
    {"type": "function", "function": {"name": "create_ticket", "description": "Escalate a customer issue to support.", "parameters": {"type": "object", "properties": {"reason": {"type": "string"}}, "required": ["reason"]}}},
]


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class AssistantTurn:
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ChatClient(Protocol):
    def complete(self, messages: list[dict[str, Any]]) -> AssistantTurn: ...


class OpenAICompatibleClient:
    """Minimal dependency-free client for the OpenAI Chat Completions protocol."""

    def __init__(self, *, api_key: str, model: str, base_url: str) -> None:
        self._api_key = api_key
        self._model = model
        self._url = f"{base_url.rstrip('/')}/chat/completions"

    def complete(self, messages: list[dict[str, Any]]) -> AssistantTurn:
        body = json.dumps({"model": self._model, "messages": messages, "tools": TOOLS, "tool_choice": "auto"}).encode("utf-8")
        request = urllib.request.Request(
            self._url,
            data=body,
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"OpenAI-compatible API returned HTTP {error.code}.") from error
        except urllib.error.URLError as error:
            raise RuntimeError("Unable to reach the OpenAI-compatible API.") from error
        try:
            message = payload["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("OpenAI-compatible API returned an unexpected response shape.") from error
        tool_calls = tuple(
            ToolCall(
                call_id=str(item.get("id", "")),
                name=item["function"]["name"],
                arguments=json.loads(item["function"].get("arguments", "{}")),
            )
            for item in message.get("tool_calls", [])
        )
        usage = payload.get("usage", {})
        return AssistantTurn(
            content=message.get("content") or "",
            tool_calls=tool_calls,
            prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
            completion_tokens=int(usage.get("completion_tokens", 0) or 0),
        )


def run_openai_task(*, task: Task, client: ChatClient, tracer: Any | None = None, max_turns: int = 4) -> dict[str, Any]:
    """Run one live tool-calling task and return the standard TrajectIQ trajectory."""
    resolved_tracer = tracer or trace_api.get_tracer(__name__)
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": task.input}]
    spans: list[Span] = [Span(1, "planner", "planner", task.input, None)]
    answer = ""

    with resolved_tracer.start_as_current_span("agent_run") as root_span:
        root_span.set_attribute("openinference.span.kind", "AGENT")
        root_span.set_attribute("trajectiq.task_id", task.task_id)
        root_span.set_attribute("input.value", task.input)
        for turn in range(max_turns):
            started = time.perf_counter()
            with resolved_tracer.start_as_current_span("llm_turn") as llm_span:
                llm_span.set_attribute("openinference.span.kind", "LLM")
                llm_span.set_attribute("input.value", json.dumps(messages))
                response = client.complete(messages)
                llm_span.set_attribute("output.value", response.content)
                llm_span.set_attribute("llm.token_count.prompt", response.prompt_tokens)
                llm_span.set_attribute("llm.token_count.completion", response.completion_tokens)
                llm_span.set_attribute("llm.token_count.total", response.prompt_tokens + response.completion_tokens)
            duration_ms = max(1, round((time.perf_counter() - started) * 1000))
            cost_usd = estimate_cost(
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                model_name="gpt-4o-mini",
            )
            spans.append(
                Span(
                    len(spans) + 1,
                    "llm",
                    "llm_turn",
                    list(messages),
                    response.content,
                    start_time_ms=0,
                    end_time_ms=duration_ms,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    cost_usd=cost_usd,
                )
            )
            if not response.tool_calls:
                answer = response.content
                break
            messages.append({"role": "assistant", "content": response.content, "tool_calls": [{"id": call.call_id, "type": "function", "function": {"name": call.name, "arguments": json.dumps(call.arguments)}} for call in response.tool_calls]})
            for call in response.tool_calls:
                with resolved_tracer.start_as_current_span(call.name) as tool_span:
                    tool_span.set_attribute("openinference.span.kind", "TOOL")
                    tool_span.set_attribute("tool.name", call.name)
                    tool_span.set_attribute("input.value", json.dumps(call.arguments))
                    output, error = call_tool(call.name, call.arguments)
                    tool_span.set_attribute("output.value", json.dumps(output))
                    if error:
                        tool_span.set_attribute("error.type", error)
                spans.append(Span(len(spans) + 1, "tool", call.name, call.arguments, output, error))
                messages.append({"role": "tool", "tool_call_id": call.call_id, "name": call.name, "content": json.dumps(output if error is None else {"error": error})})
        else:
            raise RuntimeError(f"Agent exceeded the {max_turns}-turn limit for {task.task_id}.")
        if not answer:
            raise RuntimeError(f"Agent did not return a final answer for {task.task_id}.")
        root_span.set_attribute("output.value", answer)
    spans.append(Span(len(spans) + 1, "final", "final_answer", None, answer))
    serialized_spans = [span.to_dict() for span in spans]
    return {
        "task_id": task.task_id,
        "answer": answer,
        "spans": serialized_spans,
        "metrics": aggregate_run_metrics(serialized_spans),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a live OpenAI-compatible tool-calling Agent for TrajectIQ")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    parser.add_argument("--task-id", default="refund_001")
    parser.add_argument("--all", action="store_true", help="Run the complete 36-task dataset. This may incur API charges.")
    parser.add_argument("--max-turns", type=int, default=4)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--trace", action="store_true", help="Export OpenInference spans to Phoenix via OTLP.")
    parser.add_argument("--endpoint", help="Phoenix OTLP endpoint or base URL")
    parser.add_argument("--mock", action="store_true", help="Use the local deterministic OpenAI-compatible mock; no API key or network required.")
    parser.add_argument("--mock-port", type=int, default=0, help="Mock server port; 0 selects an available local port.")
    args = parser.parse_args()
    mock_server = None
    if args.mock:
        mock_server, _ = start_mock_server(port=args.mock_port)
        api_key = "mock-key"
        base_url = f"http://127.0.0.1:{mock_server.server_port}/v1"
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = args.base_url
    if not api_key:
        parser.error("OPENAI_API_KEY is required. No API call was made.")
    tasks = TASKS if args.all else tuple(task for task in TASKS if task.task_id == args.task_id)
    if not tasks:
        parser.error(f"Unknown task_id: {args.task_id}")
    tracer = None
    if args.trace:
        provider = configure_tracing(project_name="trajectiq-openai-compatible", endpoint=args.endpoint)
        tracer = provider.get_tracer("trajectiq.openai_compatible")
    try:
        client = OpenAICompatibleClient(api_key=api_key, model=args.model, base_url=base_url)
        runs = [run_openai_task(task=task, client=client, tracer=tracer, max_turns=args.max_turns) for task in tasks]
        payload = {"version": f"openai-compatible:{args.model}", "runs": runs}
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)
    finally:
        if mock_server is not None:
            mock_server.shutdown()
            mock_server.server_close()


if __name__ == "__main__":
    main()
