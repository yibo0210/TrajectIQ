"""Optional OpenTelemetry export for TrajectIQ runs."""

import os
from typing import Any

from opentelemetry import trace as trace_api

DEFAULT_ENDPOINT = "http://localhost:6006/v1/traces"


def _resolve_endpoint(endpoint: str | None) -> str:
    resolved_endpoint = endpoint or os.environ.get("PHOENIX_COLLECTOR_ENDPOINT") or DEFAULT_ENDPOINT
    resolved_endpoint = resolved_endpoint.rstrip("/")
    return resolved_endpoint if resolved_endpoint.endswith("/v1/traces") else f"{resolved_endpoint}/v1/traces"


def configure_tracing(*, project_name: str = "trajectiq", endpoint: str | None = None) -> Any:
    """Configure an OTLP exporter and return its tracer provider."""
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk import trace as trace_sdk
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    headers: dict[str, str] = {}
    api_key = os.environ.get("PHOENIX_API_KEY")
    if api_key:
        headers["authorization"] = f"Bearer {api_key}"
    resource = Resource.create({"openinference.project.name": project_name})
    provider = trace_sdk.TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint=_resolve_endpoint(endpoint), headers=headers or None)))
    if type(trace_api.get_tracer_provider()).__name__ == "ProxyTracerProvider":
        trace_api.set_tracer_provider(provider)
    return provider
