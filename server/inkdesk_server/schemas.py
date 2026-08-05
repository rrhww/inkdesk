from __future__ import annotations

<<<<<<< HEAD
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
=======
from pydantic import BaseModel, ConfigDict, Field
>>>>>>> origin/main


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
<<<<<<< HEAD


class EngineCommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str
    tasks: list[EngineTaskRequest] = Field(default_factory=list)
    maxConcurrency: int = Field(default=8, ge=1, le=32)


TASK_ORIGINS = {
    "realtime_requirement",
    "knowledge_signal",
    "execution_finding",
    "manual",
}
TASK_STATUSES = {"backlog", "ready", "doing", "review", "blocked", "done"}
CONTEXT_STATUSES = {"pending", "searching", "ready", "gap", "failed"}


class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=240)
    goal: str = Field(min_length=1, max_length=10000)
    originType: Literal["realtime_requirement", "knowledge_signal", "execution_finding", "manual"]
    originRef: str | None = Field(default=None, max_length=2000)
    priority: str = Field(default="medium", max_length=32)
    risk: str = Field(default="medium", max_length=32)
    knowledgeTopicIds: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_knowledge_origin(self):
        if self.originType == "knowledge_signal" and (
            not self.originRef or not self.knowledgeTopicIds
        ):
            raise ValueError(
                "Knowledge-signal tasks require originRef and at least one knowledgeTopicId."
            )
        return self


class TaskTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["backlog", "ready", "doing", "review", "blocked", "done"]
    ifVersion: int = Field(ge=1)


class TaskSummary(BaseModel):
    id: str
    title: str
    goal: str
    status: str
    originType: str
    originRef: str | None = None
    priority: str
    risk: str
    contextStatus: str
    knowledgeTopicIds: list[str] = Field(default_factory=list)
    version: int
    createdAt: str
    updatedAt: str


class TaskDetail(TaskSummary):
    contextPack: dict | None = None
    knowledgeGap: dict | None = None


class TaskListResponse(BaseModel):
    tasks: list[TaskSummary]


class KnowledgeSignal(BaseModel):
    id: str
    type: str
    severity: str
    title: str
    detail: str
    sourcePath: str | None = None


class KnowledgeSource(BaseModel):
    id: str
    documentId: str
    title: str
    path: str
    source: str
    kind: str
    summary: str
    updatedAt: str
    href: str | None = None
    locator: dict[str, str | int] | None = None
    excerpt: str = ""
    contentHash: str | None = None
    sourceCoverage: Literal["supported", "partial", "none", "unknown"] = "unknown"
    provenanceStatus: Literal["supported", "partial", "unsupported", "unknown"] = "unknown"


class KnowledgeRelatedTopic(BaseModel):
    id: str
    title: str
    kind: str


class KnowledgeTopicSummary(BaseModel):
    id: str
    title: str
    summary: str
    kind: str
    path: str
    source: str
    status: str
    updatedAt: str
    sourceCount: int
    openQuestionCount: int
    signalCount: int
    signals: list[KnowledgeSignal]
    healthSignals: list[KnowledgeSignal]
    vaultPath: str | None = None
    sourceCoverage: Literal["supported", "partial", "none", "unknown"] = "unknown"
    provenanceStatus: Literal["supported", "partial", "unsupported", "unknown"] = "unknown"
=======


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
>>>>>>> origin/main

    capabilityId: str
    inputs: HarnessRunInputs = Field(default_factory=HarnessRunInputs)
    executor: str = "claude"

<<<<<<< HEAD
class KnowledgeTopicStats(BaseModel):
    topicCount: int
    sourceCount: int
    signalCount: int
    attentionCount: int


class KnowledgeTopicList(BaseModel):
    topics: list[KnowledgeTopicSummary]
    stats: KnowledgeTopicStats


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeTopicSummary]


class KnowledgeSourcesResponse(BaseModel):
    topicId: str
    sources: list[KnowledgeSource]


class KnowledgeBriefing(BaseModel):
    topicId: str
    title: str
    summary: str
    kind: str
    path: str
    source: str
    status: str
    sourceCount: int
    openQuestionCount: int
    signalCount: int
    currentUnderstanding: list[str]
    keyDecisions: list[str]
    openQuestions: list[str]
    sources: list[KnowledgeSource]
    codePaths: list[str]
    relatedTopics: list[KnowledgeRelatedTopic]
    signals: list[KnowledgeSignal]
    healthSignals: list[KnowledgeSignal]
    documentId: str
    updatedAt: str
    confidence: float = Field(ge=0.0, le=1.0)
    sourceCoverage: Literal["supported", "partial", "none", "unknown"] = "unknown"
    provenanceStatus: Literal["supported", "partial", "unsupported", "unknown"] = "unknown"


class KnowledgeDocument(BaseModel):
    """A controlled, read-only document payload for topic/source provenance links."""

    documentId: str
    title: str
    source: str
    path: str
    content: str
    contentHash: str


class KnowledgeSignalActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["acknowledge", "resolve", "dismiss", "reopen"]
    ifVersion: int = Field(ge=1)
    note: str | None = Field(default=None, max_length=2000)


class KnowledgeReviewCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signalId: str | None = None
    topicId: str
    action: str = Field(min_length=1, max_length=64)
    proposal: dict = Field(default_factory=dict)
    note: str | None = Field(default=None, max_length=2000)


class KnowledgeReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["accepted", "rejected", "cancelled"]
    note: str | None = Field(default=None, max_length=2000)
=======

class PermissionDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern=r"^(allow_once|deny)$")
    reason: str | None = Field(default=None, max_length=500)
>>>>>>> origin/main
