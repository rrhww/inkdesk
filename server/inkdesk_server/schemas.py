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
