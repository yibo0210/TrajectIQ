import re
from dataclasses import asdict
from typing import Any

from opentelemetry import trace as trace_api

from .data import DELIVERY, ORDERS, POLICIES
from .metrics import aggregate_run_metrics, estimate_cost, estimate_tokens
from .models import AgentVersion, Span, Task


def _get_order_id(text: str) -> str | None:
    match = re.search(r"A\d{4}", text)
    return match.group(0) if match else None


def call_tool(tool_name: str, arguments: dict[str, Any]) -> tuple[Any, str | None]:
    """Execute a support tool for both the deterministic and live Agent runners."""
    if tool_name == "query_order":
        order = ORDERS.get(arguments.get("order_id"))
        return (order, None) if order else (None, "order_not_found")
    if tool_name == "search_policy":
        return POLICIES.get(arguments.get("topic", "return_opened")), None
    if tool_name == "estimate_delivery":
        return DELIVERY.get(arguments.get("order_id")), None
    if tool_name == "create_ticket":
        return {"ticket_id": "T-100", "status": "created"}, None
    return None, "unknown_tool"


def _plan_tools(*, version: AgentVersion, task: Task) -> list[tuple[str, dict[str, Any]]]:
    order_id = _get_order_id(task.input)
    input_lowercase = task.input.lower()
    if version.tool_policy == "regression" and "refund" in input_lowercase:
        return [("estimate_delivery", {"order_id": order_id})]
    if "transfer" in input_lowercase or "person" in input_lowercase or "ticket" in input_lowercase:
        return [("create_ticket", {"reason": task.input})]
    if "refund" in input_lowercase:
        planned_tools = [("query_order", {"order_id": order_id})]
        if "when" in input_lowercase:
            planned_tools.append(("search_policy", {"topic": "refund_timeline"}))
        return planned_tools
    if "arriv" in input_lowercase:
        return [("query_order", {"order_id": order_id}), ("estimate_delivery", {"order_id": order_id})]
    if "order" in input_lowercase:
        return [("query_order", {"order_id": order_id})]
    if order_id:
        return [("query_order", {"order_id": order_id})]
    if "return" in input_lowercase:
        return [("search_policy", {"topic": "return_opened"})]
    return []


def _run_task(*, version: AgentVersion, task: Task, tracer: Any | None) -> dict[str, Any]:
    clock_ms = 0
    planner_prompt_tokens = estimate_tokens(task.input)
    planner_completion_tokens = estimate_tokens(_plan_tools(version=version, task=task))
    planner_duration_ms = 12
    planner_cost = estimate_cost(
        prompt_tokens=planner_prompt_tokens,
        completion_tokens=planner_completion_tokens,
        model_name=version.model_name,
    )
    spans: list[Span] = [
        Span(
            1,
            "planner",
            "plan",
            task.input,
            None,
            start_time_ms=clock_ms,
            end_time_ms=clock_ms + planner_duration_ms,
            prompt_tokens=planner_prompt_tokens,
            completion_tokens=planner_completion_tokens,
            cost_usd=planner_cost,
        )
    ]
    resolved_tracer = tracer or trace_api.get_tracer(__name__)
    with resolved_tracer.start_as_current_span("planner") as planner_span:
        planner_span.set_attribute("openinference.span.kind", "AGENT")
        planner_span.set_attribute("input.value", task.input)
        planned_tools = _plan_tools(version=version, task=task)
        planner_span.set_attribute("output.value", str(planned_tools))
        planner_span.set_attribute("llm.model_name", version.model_name)
        planner_span.set_attribute("llm.token_count.prompt", planner_prompt_tokens)
        planner_span.set_attribute("llm.token_count.completion", planner_completion_tokens)
        planner_span.set_attribute("llm.token_count.total", planner_prompt_tokens + planner_completion_tokens)
        planner_span.set_attribute("llm.cost.total", planner_cost)

    answer_parts: list[str] = []
    clock_ms += planner_duration_ms
    for step, (tool_name, arguments) in enumerate(planned_tools, start=2):
        tool_output, error = call_tool(tool_name, arguments)
        tool_prompt_tokens = estimate_tokens(arguments)
        tool_completion_tokens = estimate_tokens(tool_output)
        tool_duration_ms = 8 + len(tool_name) % 5
        tool_cost = estimate_cost(
            prompt_tokens=tool_prompt_tokens,
            completion_tokens=tool_completion_tokens,
            model_name=version.model_name,
        )
        with resolved_tracer.start_as_current_span(tool_name) as tool_span:
            tool_span.set_attribute("openinference.span.kind", "TOOL")
            tool_span.set_attribute("tool.name", tool_name)
            tool_span.set_attribute("input.value", str(arguments))
            tool_span.set_attribute("output.value", str(tool_output))
            tool_span.set_attribute("trajectiq.duration_ms", tool_duration_ms)
            tool_span.set_attribute("llm.token_count.prompt", tool_prompt_tokens)
            tool_span.set_attribute("llm.token_count.completion", tool_completion_tokens)
            tool_span.set_attribute("llm.token_count.total", tool_prompt_tokens + tool_completion_tokens)
            tool_span.set_attribute("llm.cost.total", tool_cost)
            if error:
                tool_span.set_attribute("error.type", error)
        spans.append(
            Span(
                step,
                "tool",
                tool_name,
                arguments,
                tool_output,
                error,
                start_time_ms=clock_ms,
                end_time_ms=clock_ms + tool_duration_ms,
                prompt_tokens=tool_prompt_tokens,
                completion_tokens=tool_completion_tokens,
                cost_usd=tool_cost,
            )
        )
        clock_ms += tool_duration_ms
        if tool_name == "query_order" and tool_output:
            answer_parts.append(f"Order status: {tool_output['status']}; refund status: {tool_output['refund'] or 'no refund record'}. " )
        elif tool_name == "search_policy" and tool_output:
            answer_parts.append(tool_output)
        elif tool_name == "estimate_delivery" and tool_output:
            answer_parts.append(tool_output)
        elif tool_name == "create_ticket" and tool_output:
            answer_parts.append(f"Created support ticket {tool_output['ticket_id']}.")

    answer = "".join(answer_parts) or "Unable to process this request."
    final_duration_ms = 10
    final_prompt_tokens = estimate_tokens(answer)
    final_completion_tokens = estimate_tokens(answer)
    final_cost = estimate_cost(
        prompt_tokens=final_prompt_tokens,
        completion_tokens=final_completion_tokens,
        model_name=version.model_name,
    )
    with resolved_tracer.start_as_current_span("final_answer") as final_span:
        final_span.set_attribute("openinference.span.kind", "CHAIN")
        final_span.set_attribute("output.value", answer)
        final_span.set_attribute("trajectiq.duration_ms", final_duration_ms)
        final_span.set_attribute("llm.token_count.prompt", final_prompt_tokens)
        final_span.set_attribute("llm.token_count.completion", final_completion_tokens)
        final_span.set_attribute("llm.token_count.total", final_prompt_tokens + final_completion_tokens)
        final_span.set_attribute("llm.cost.total", final_cost)
    spans.append(
        Span(
            len(spans) + 1,
            "final",
            "final_answer",
            None,
            answer,
            start_time_ms=clock_ms,
            end_time_ms=clock_ms + final_duration_ms,
            prompt_tokens=final_prompt_tokens,
            completion_tokens=final_completion_tokens,
            cost_usd=final_cost,
        )
    )
    serialized_spans = [span.to_dict() for span in spans]
    return {
        "version": asdict(version),
        "task_id": task.task_id,
        "answer": answer,
        "spans": serialized_spans,
        "metrics": aggregate_run_metrics(serialized_spans),
    }


def run_task(*, version: AgentVersion, task: Task, tracer: Any | None = None) -> dict[str, Any]:
    """Run one task and optionally emit a hierarchical Phoenix trace."""
    if tracer is None:
        return _run_task(version=version, task=task, tracer=None)
    with tracer.start_as_current_span("agent_run") as root_span:
        root_span.set_attribute("openinference.span.kind", "AGENT")
        root_span.set_attribute("trajectiq.version", version.name)
        root_span.set_attribute("trajectiq.task_id", task.task_id)
        root_span.set_attribute("input.value", task.input)
        result = _run_task(version=version, task=task, tracer=tracer)
        root_span.set_attribute("output.value", result["answer"])
        for key, value in result["metrics"].items():
            root_span.set_attribute(f"trajectiq.{key}", value)
        return result
