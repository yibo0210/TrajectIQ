import re
from dataclasses import asdict
from typing import Any

from opentelemetry import trace as trace_api

from .data import DELIVERY, ORDERS, POLICIES
from .models import AgentVersion, Span, Task


def _get_order_id(text: str) -> str | None:
    match = re.search(r"A\d{4}", text)
    return match.group(0) if match else None


def _call_tool(tool_name: str, arguments: dict[str, Any]) -> tuple[Any, str | None]:
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
    if "transfer" in input_lowercase or "person" in input_lowercase:
        return [("create_ticket", {"reason": task.input})]
    if "arrive" in input_lowercase:
        return [("query_order", {"order_id": order_id}), ("estimate_delivery", {"order_id": order_id})]
    if "refund" in input_lowercase or "order" in input_lowercase:
        planned_tools = [("query_order", {"order_id": order_id})]
        if "when" in input_lowercase:
            planned_tools.append(("search_policy", {"topic": "refund_timeline"}))
        return planned_tools
    if "return" in input_lowercase:
        return [("search_policy", {"topic": "return_opened"})]
    return []


def _run_task(*, version: AgentVersion, task: Task, tracer: Any | None) -> dict[str, Any]:
    spans: list[Span] = [Span(1, "planner", "plan", task.input, None)]
    resolved_tracer = tracer or trace_api.get_tracer(__name__)
    with resolved_tracer.start_as_current_span("planner") as planner_span:
        planner_span.set_attribute("openinference.span.kind", "AGENT")
        planner_span.set_attribute("input.value", task.input)
        planned_tools = _plan_tools(version=version, task=task)
        planner_span.set_attribute("output.value", str(planned_tools))

    answer_parts: list[str] = []
    for step, (tool_name, arguments) in enumerate(planned_tools, start=2):
        with resolved_tracer.start_as_current_span(tool_name) as tool_span:
            tool_span.set_attribute("openinference.span.kind", "TOOL")
            tool_span.set_attribute("tool.name", tool_name)
            tool_span.set_attribute("input.value", str(arguments))
            output, error = _call_tool(tool_name, arguments)
            tool_span.set_attribute("output.value", str(output))
            if error:
                tool_span.set_attribute("error.type", error)
        spans.append(Span(step, "tool", tool_name, arguments, output, error))
        if tool_name == "query_order" and output:
            answer_parts.append(f"Order status: {output['status']}; refund status: {output['refund'] or 'no refund record'}. " )
        elif tool_name == "search_policy" and output:
            answer_parts.append(output)
        elif tool_name == "estimate_delivery" and output:
            answer_parts.append(output)
        elif tool_name == "create_ticket" and output:
            answer_parts.append(f"Created support ticket {output['ticket_id']}.")

    answer = "".join(answer_parts) or "Unable to process this request."
    with resolved_tracer.start_as_current_span("final_answer") as final_span:
        final_span.set_attribute("openinference.span.kind", "CHAIN")
        final_span.set_attribute("output.value", answer)
    spans.append(Span(len(spans) + 1, "final", "final_answer", None, answer))
    return {"version": asdict(version), "task_id": task.task_id, "answer": answer, "spans": [span.to_dict() for span in spans]}


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
        return result
