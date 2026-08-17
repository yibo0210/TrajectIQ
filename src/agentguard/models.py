from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AgentVersion:
    name: str
    prompt_revision: str
    tool_policy: str
    max_steps: int = 6


@dataclass(frozen=True)
class Task:
    task_id: str
    category: str
    input: str
    expected_tools: tuple[str, ...]
    expected_arguments: dict[str, dict[str, Any]]
    expected_answer_contains: tuple[str, ...]
    critical: bool = False
    tags: tuple[str, ...] = ()


@dataclass
class Span:
    step: int
    kind: str
    name: str
    input: Any
    output: Any
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
