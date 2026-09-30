from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _id() -> str:
    return str(uuid4())


class Role(str, Enum):
    EXPLORER = "explorer"
    ARCHITECT = "architect"
    IMPLEMENTER = "implementer"
    REVIEWER = "reviewer"
    TESTER = "tester"
    VERIFIER = "verifier"


class Task(BaseModel):
    id: str = Field(default_factory=_id)
    objective: str
    repository: str = "."
    status: str = "CREATED"
    current_role: Role | None = None
    iteration: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class Agent(BaseModel):
    id: str = Field(default_factory=_id)
    name: str
    runtime: str = "opencode"
    role: Role


class Artifact(BaseModel):
    path: str
    description: str = ""


class Evidence(BaseModel):
    kind: str
    description: str
    command: str | None = None
    exit_code: int | None = None
    output: str | None = None


class Finding(BaseModel):
    summary: str
    severity: str = "info"
    artifacts: list[Artifact] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class Handoff(BaseModel):
    id: str = Field(default_factory=_id)
    task_id: str
    from_agent: str
    to_agent: str
    objective: str
    findings: list[Finding] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    required_action: str
    evidence: list[Evidence] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Message(BaseModel):
    id: str = Field(default_factory=_id)
    task_id: str
    from_agent: str
    to_agent: str | None = None
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Decision(BaseModel):
    id: str = Field(default_factory=_id)
    task_id: str
    stage: str
    outcome: str
    rationale: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VerificationResult(BaseModel):
    task_id: str
    passed: bool
    evidence: list[Evidence] = Field(default_factory=list)
    summary: str
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentResult(BaseModel):
    agent: Agent
    exit_code: int
    output: str
    artifacts: list[Artifact] = Field(default_factory=list)
    duration_seconds: float = 0
    success: bool = False
