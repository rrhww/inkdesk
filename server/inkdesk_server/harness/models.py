from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class StageStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class StageEffect(StrEnum):
    READ_ONLY = "read_only"
    WORKSPACE_WRITE = "workspace_write"
    VAULT_WRITE = "vault_write"
    EXTERNAL = "external"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"
    STALE = "stale"


class EvidenceStatus(StrEnum):
    AVAILABLE = "available"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class FindingDimension(StrEnum):
    TASK_UNDERSTANDING = "Task Understanding"
    CONTROLLED_EXECUTION = "Controlled Execution"
    CHANGE_VALIDATION = "Change Validation"
    RELIABLE_DELIVERY = "Reliable Delivery"
    LEARNING_CAPTURE = "Learning Capture"


class FindingSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FindingStatus(StrEnum):
    OPEN = "open"
    DEFERRED = "deferred"
    VERIFIED = "verified"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    contentHash: str
    capturedAt: str
    repoHead: str
    excerpt: str
    collector: str = "deterministic"
    stageId: str | None = None
    sessionId: str | None = None
    toolUseId: str | None = None
    toolName: str | None = None


class EvidenceEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: EvidenceStatus
    summaryFacts: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)


class EvidenceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: str = "inkdesk.evidence/v1alpha1"
    runId: str
    target: str
    depth: str
    repoHead: str
    capturedAt: str
    sessionEvidenceStatus: EvidenceStatus = EvidenceStatus.UNAVAILABLE
    envelopes: dict[str, EvidenceEnvelope]

    @property
    def evidence_ids(self) -> set[str]:
        return {
            item.id
            for envelope in self.envelopes.values()
            for item in envelope.evidence
        }


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^F-[0-9]{3,}$")
    dimension: FindingDimension
    severity: FindingSeverity
    confidence: FindingConfidence
    title: str = Field(min_length=1)
    consequence: str = Field(min_length=1)
    causeChain: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    expectedArtifact: str = Field(min_length=1)
    repairScope: str = Field(min_length=1)
    verifiers: list[str] = Field(min_length=1)
    status: FindingStatus = FindingStatus.OPEN

    def validate_evidence_ids(self, available: set[str]) -> list[str]:
        return sorted(set(self.evidence) - available)


class AuditReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: str = "inkdesk.findings/v1alpha1"
    runId: str
    repoHead: str
    generatedAt: str
    supportTrack: str = "Undetermined"
    dimensionScores: dict[FindingDimension, int] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)


class RunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    capabilityId: str
    executor: str
    inputs: dict[str, Any]
    status: RunStatus = RunStatus.QUEUED
    sourceHead: str
    sourceDirty: bool = False
    createdAt: str = Field(default_factory=utc_now)
    updatedAt: str = Field(default_factory=utc_now)
    stageStates: dict[str, StageStatus] = Field(default_factory=dict)
    reportPath: str | None = None
    error: dict[str, Any] | None = None
    sessionSummaries: list[dict[str, Any]] = Field(default_factory=list)


class PermissionStatus(StrEnum):
    PENDING = "pending"
    ALLOWED = "allowed"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PermissionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    runId: str
    stageId: str
    sessionId: str
    toolUseId: str
    tool: str
    inputPreview: dict[str, Any] = Field(default_factory=dict)
    status: PermissionStatus = PermissionStatus.PENDING
    createdAt: str = Field(default_factory=utc_now)
    expiresAt: str
    resolvedAt: str | None = None
    reason: str | None = None


class RunEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int
    type: str
    timestamp: str = Field(default_factory=utc_now)
    data: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkflowStage:
    id: str
    dependencies: tuple[str, ...] = ()
    kind: str = "stage"
    prompt: str = ""
    effect: StageEffect = StageEffect.READ_ONLY
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkflowStageResult:
    stage_id: str
    output: Any
    duration_ms: float


@dataclass(frozen=True, slots=True)
class WorkflowExecutionEvent:
    sequence: int
    type: str
    stage_id: str | None
    timestamp: str
    data: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class WorkflowExecutionResult:
    results: Mapping[str, WorkflowStageResult]
    completed_order: tuple[str, ...]
    stage_states: Mapping[str, StageStatus]
    duration_ms: float
