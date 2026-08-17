"""Versioned JSONL evaluation dataset loading for TrajectIQ."""

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Iterable

from .models import Task


@dataclass(frozen=True)
class EvaluationDataset:
    name: str
    version: str
    tasks: tuple[Task, ...]

    @property
    def identifier(self) -> str:
        return f"{self.name}_{self.version}"


def _task_from_payload(payload: dict[str, Any], *, source: str) -> Task:
    required = ("task_id", "category", "input", "expected_tools", "expected_arguments", "expected_answer_contains")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"Dataset row in {source} is missing: {', '.join(missing)}")
    if not all(isinstance(payload[key], str) for key in ("task_id", "category", "input")):
        raise ValueError(f"Dataset row in {source} has invalid task identity fields.")
    if not isinstance(payload["expected_tools"], list) or not all(isinstance(item, str) for item in payload["expected_tools"]):
        raise ValueError(f"Dataset row {payload['task_id']} in {source} has invalid expected_tools.")
    if not isinstance(payload["expected_arguments"], dict) or not isinstance(payload["expected_answer_contains"], list):
        raise ValueError(f"Dataset row {payload['task_id']} in {source} has invalid expectations.")
    tags = payload.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise ValueError(f"Dataset row {payload['task_id']} in {source} has invalid tags.")
    return Task(
        task_id=payload["task_id"],
        category=payload["category"],
        input=payload["input"],
        expected_tools=tuple(payload["expected_tools"]),
        expected_arguments=payload["expected_arguments"],
        expected_answer_contains=tuple(payload["expected_answer_contains"]),
        critical=bool(payload.get("critical", False)),
        tags=tuple(tags),
    )


def _load_rows(lines: Iterable[str], *, source: str) -> tuple[Task, ...]:
    tasks: list[Task] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"Dataset row {line_number} in {source} must be a JSON object.")
        tasks.append(_task_from_payload(payload, source=f"{source}:{line_number}"))
    task_ids = [task.task_id for task in tasks]
    if not tasks or len(task_ids) != len(set(task_ids)):
        raise ValueError(f"Dataset {source} must contain unique task IDs.")
    return tuple(tasks)


def load_dataset(path: Path, *, name: str, version: str) -> EvaluationDataset:
    """Load a repository or user-provided JSONL evaluation dataset."""
    return EvaluationDataset(name=name, version=version, tasks=_load_rows(path.read_text(encoding="utf-8").splitlines(), source=str(path)))


def load_default_dataset() -> EvaluationDataset:
    """Load the packaged customer-support v1 evaluation dataset."""
    resource = resources.files("agentguard.datasets").joinpath("customer_support_v1.jsonl")
    with resource.open("r", encoding="utf-8") as handle:
        tasks = _load_rows(handle, source="customer_support_v1.jsonl")
    return EvaluationDataset(name="customer_support", version="v1", tasks=tasks)
