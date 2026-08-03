from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ApiErrorResponse(BaseModel):
    code: str
    message: str


class EngineTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    dependencies: list[str] = Field(default_factory=list)
    kind: str = "agent"
    prompt: str = ""
    metadata: dict = Field(default_factory=dict)


class EngineCommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str
    tasks: list[EngineTaskRequest] = Field(default_factory=list)
    maxConcurrency: int = Field(default=8, ge=1, le=32)


class SkillRunInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement: str = Field(min_length=1)
    sourcePath: str = Field(min_length=1)
    sourceTitle: str = Field(min_length=1)


class SkillRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inputs: SkillRunInputs
    maxConcurrency: int = Field(default=4, ge=1, le=4)


class HarnessRunInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str = "repository"
    depth: str = "quick"
    repoPath: str | None = None


class HarnessRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capabilityId: str
    inputs: HarnessRunInputs = Field(default_factory=HarnessRunInputs)
    executor: str = "claude"


class PermissionDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern=r"^(allow_once|deny)$")
    reason: str | None = Field(default=None, max_length=500)
