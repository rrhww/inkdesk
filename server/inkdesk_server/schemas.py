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
