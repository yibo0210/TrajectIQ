from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agentguard.agent import run_task
from agentguard.data import TASKS
from agentguard.run import VERSIONS


def test_traced_task_has_one_root_and_four_child_spans() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("agentguard-test")
    task = next(value for value in TASKS if value.task_id == "refund_001")

    run_task(version=VERSIONS["baseline"], task=task, tracer=tracer)

    spans = exporter.get_finished_spans()
    root_span = next(span for span in spans if span.name == "agent_run")
    child_spans = [span for span in spans if span.name != "agent_run"]

    assert [span.name for span in spans] == [
        "planner",
        "query_order",
        "search_policy",
        "final_answer",
        "agent_run",
    ]
    assert all(span.parent is not None and span.parent.span_id == root_span.context.span_id for span in child_spans)
