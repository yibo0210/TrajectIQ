"""Adapt Phoenix and OpenTelemetry JSON span exports to TrajectIQ trajectories."""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _otlp_value(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    for key in ("stringValue", "boolValue", "intValue", "doubleValue"):
        if key in value:
            return value[key]
    if "arrayValue" in value and isinstance(value["arrayValue"], dict):
        values = value["arrayValue"].get("values", [])
        return [_otlp_value(item) for item in values]
    if "kvlistValue" in value and isinstance(value["kvlistValue"], dict):
        return {item["key"]: _otlp_value(item.get("value")) for item in value["kvlistValue"].get("values", [])}
    return value


def _attributes(span: dict[str, Any]) -> dict[str, Any]:
    attributes = span.get("attributes", {})
    if isinstance(attributes, dict):
        return attributes
    if isinstance(attributes, list):
        return {
            item["key"]: _otlp_value(item.get("value"))
            for item in attributes
            if isinstance(item, dict) and isinstance(item.get("key"), str)
        }
    return {}


def _parse_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _span_start(span: dict[str, Any], index: int) -> tuple[int, int]:
    value = span.get("start_time") or span.get("start_time_unix_nano") or span.get("startTimeUnixNano") or ""
    try:
        return int(value), index
    except (TypeError, ValueError):
        return 0, index


def load_openinference_export(path: Path) -> tuple[str, dict[str, dict[str, Any]]]:
    """Load a Phoenix/OpenTelemetry JSON export into normalized TrajectIQ runs.

    The export must provide a version plus either a top-level ``spans`` array or
    a ``traces`` array containing ``spans``. Every trace needs a
    ``trajectiq.task_id`` attribute on one span. Tool spans use OpenInference's
    ``TOOL`` kind and ``tool.name`` semantic attribute.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("version"), str):
        raise ValueError(f"OpenInference export {path} must contain a version.")
    raw_spans: list[dict[str, Any]] = []
    if isinstance(payload.get("spans"), list):
        raw_spans = [span for span in payload["spans"] if isinstance(span, dict)]
    elif isinstance(payload.get("traces"), list):
        for trace in payload["traces"]:
            if isinstance(trace, dict) and isinstance(trace.get("spans"), list):
                trace_id = trace.get("trace_id") or trace.get("traceId")
                for span in trace["spans"]:
                    if isinstance(span, dict):
                        raw_spans.append({**span, "trace_id": span.get("trace_id") or span.get("traceId") or trace_id})
    else:
        raise ValueError(f"OpenInference export {path} must contain spans or traces.")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, span in enumerate(raw_spans):
        trace_id = span.get("trace_id") or span.get("traceId")
        if not isinstance(trace_id, str) or not trace_id:
            raise ValueError(f"Span {index} in {path} is missing trace_id.")
        grouped[trace_id].append(span)

    runs: dict[str, dict[str, Any]] = {}
    for trace_id, spans in grouped.items():
        ordered = sorted(enumerate(spans), key=lambda item: _span_start(item[1], item[0]))
        task_id = next(
            (attrs["trajectiq.task_id"] for _, span in ordered if isinstance((attrs := _attributes(span)).get("trajectiq.task_id"), str)),
            None,
        )
        if not task_id:
            raise ValueError(f"Trace {trace_id} in {path} is missing trajectiq.task_id.")
        if task_id in runs:
            raise ValueError(f"OpenInference export {path} contains duplicate task_id {task_id}.")

        normalized_spans: list[dict[str, Any]] = []
        answer = ""
        for step, (_, span) in enumerate(ordered, start=1):
            attrs = _attributes(span)
            span_kind = str(attrs.get("openinference.span.kind", "CHAIN")).upper()
            name = str(attrs.get("tool.name") or span.get("name") or "unnamed_span")
            output = _parse_value(attrs.get("output.value"))
            if isinstance(output, str) and output and (name == "final_answer" or span_kind in {"AGENT", "CHAIN"}):
                answer = output
            error = attrs.get("error.type")
            if not error and str(span.get("status_code", "")).upper() == "ERROR":
                error = span.get("status_message") or "span_error"
            normalized_spans.append(
                {
                    "step": step,
                    "kind": "tool" if span_kind == "TOOL" else "final" if name == "final_answer" else "planner",
                    "name": name,
                    "input": _parse_value(attrs.get("input.value")),
                    "output": output,
                    "error": error,
                }
            )
        if not answer:
            answer = str(_parse_value(_attributes(ordered[-1][1]).get("output.value")) or "")
        runs[task_id] = {"task_id": task_id, "answer": answer, "spans": normalized_spans}
    return payload["version"], runs
