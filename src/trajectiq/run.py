import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .agent import run_task
from .data import TASKS
from .models import AgentVersion
from .telemetry import configure_tracing

VERSIONS = {
    "baseline": AgentVersion("baseline", "prompt-v1", "baseline"),
    "regression": AgentVersion("regression", "prompt-v2", "regression"),
    "fixed": AgentVersion("fixed", "prompt-v3", "baseline"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic TrajectIQ support Agent")
    parser.add_argument("--version", choices=VERSIONS, default="baseline")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--trace", action="store_true", help="Export traces to Phoenix via OTLP")
    parser.add_argument("--endpoint", help="Phoenix OTLP endpoint or base URL")
    args = parser.parse_args()

    tracer = None
    if args.trace:
        provider = configure_tracing(endpoint=args.endpoint, project_name=f"trajectiq-{args.version}")
        tracer = provider.get_tracer("trajectiq")
    results = [run_task(version=VERSIONS[args.version], task=task, tracer=tracer) for task in TASKS]
    payload = {"version": asdict(VERSIONS[args.version]), "results": results}
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
