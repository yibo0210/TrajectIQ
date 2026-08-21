"""Deterministic production-style telemetry for TrajectIQ trajectories."""

from typing import Any

MODEL_PRICING_USD_PER_MILLION: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}


def estimate_tokens(value: Any) -> int:
    """Estimate tokens without requiring a provider tokenizer."""
    if value is None:
        return 0
    text = value if isinstance(value, str) else str(value)
    return max(1, (len(text) + 3) // 4)


def estimate_cost(*, prompt_tokens: int, completion_tokens: int, model_name: str) -> float:
    prompt_price, completion_price = MODEL_PRICING_USD_PER_MILLION.get(
        model_name, MODEL_PRICING_USD_PER_MILLION["gpt-4o-mini"]
    )
    return prompt_tokens * prompt_price / 1_000_000 + completion_tokens * completion_price / 1_000_000


def span_metrics(span: dict[str, Any]) -> dict[str, float | int]:
    """Read normalized telemetry fields from either native or imported spans."""
    start = span.get("start_time_ms", 0) or 0
    end = span.get("end_time_ms", start) or start
    duration = span.get("duration_ms")
    if duration is None:
        duration = max(0, end - start)
    prompt = span.get("prompt_tokens", 0) or 0
    completion = span.get("completion_tokens", 0) or 0
    cost = span.get("cost_usd", 0.0) or 0.0
    return {
        "duration_ms": float(duration),
        "prompt_tokens": int(prompt),
        "completion_tokens": int(completion),
        "total_tokens": int(prompt + completion),
        "cost_usd": float(cost),
    }


def aggregate_run_metrics(spans: list[dict[str, Any]]) -> dict[str, float | int]:
    """Aggregate span telemetry into a stable run-level summary."""
    metrics = [span_metrics(span) for span in spans]
    return {
        "duration_ms": sum(item["duration_ms"] for item in metrics),
        "prompt_tokens": sum(item["prompt_tokens"] for item in metrics),
        "completion_tokens": sum(item["completion_tokens"] for item in metrics),
        "total_tokens": sum(item["total_tokens"] for item in metrics),
        "cost_usd": round(sum(item["cost_usd"] for item in metrics), 8),
    }
