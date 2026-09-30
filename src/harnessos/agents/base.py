from abc import ABC, abstractmethod
from pathlib import Path

from harnessos.protocol.models import Agent, AgentResult, Task


class AgentRuntime(ABC):
    @abstractmethod
    def execute(self, task: Task, agent: Agent, context: str = "", repository: Path | None = None) -> AgentResult:
        """Run a task through an external runtime and normalize its result."""
