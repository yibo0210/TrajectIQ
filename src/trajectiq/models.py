from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AgentVersion:
    name: str
    prompt_revision: str
    tool_policy: str
    max_steps: int = 6
    model_name: str = "gpt-4o-mini"


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
    start_time_ms: int = 0
    end_time_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
