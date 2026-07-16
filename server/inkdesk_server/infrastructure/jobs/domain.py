"""Pure state and transition rules for durable jobs and their attempts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AttemptStatus(StrEnum):
    LEASED = "leased"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ABANDONED = "abandoned"
    CANCELLED = "cancelled"


class ReasonCode(StrEnum):
    JOB_NOT_CLAIMABLE = "JOB_NOT_CLAIMABLE"
    JOB_ACTIVE_ATTEMPT_EXISTS = "JOB_ACTIVE_ATTEMPT_EXISTS"
    JOB_LEASE_EXPIRED = "JOB_LEASE_EXPIRED"
    JOB_LEASE_LOST = "JOB_LEASE_LOST"
    JOB_HEARTBEAT_REJECTED = "JOB_HEARTBEAT_REJECTED"
    JOB_HANDLER_NOT_REGISTERED = "JOB_HANDLER_NOT_REGISTERED"
    JOB_HANDLER_FAILED = "JOB_HANDLER_FAILED"
    JOB_MAX_ATTEMPTS_EXCEEDED = "JOB_MAX_ATTEMPTS_EXCEEDED"
    JOB_IDEMPOTENCY_CONFLICT = "JOB_IDEMPOTENCY_CONFLICT"
    JOB_CANCELLED = "JOB_CANCELLED"
    JOB_ILLEGAL_TRANSITION = "JOB_ILLEGAL_TRANSITION"
    ATTEMPT_ILLEGAL_TRANSITION = "ATTEMPT_ILLEGAL_TRANSITION"


StateT = TypeVar("StateT")


@dataclass(frozen=True)
class TransitionResult(Generic[StateT]):
    """Result of a state transition without persistence-specific exceptions."""

    state: StateT
    accepted: bool
    reason_code: ReasonCode | None = None


@dataclass(frozen=True)
class JobState:
    status: JobStatus

    def transition(self, target: JobStatus, *, explicit_retry: bool = False) -> TransitionResult[JobState]:
        allowed = {
            JobStatus.PENDING: {JobStatus.RUNNING, JobStatus.CANCELLED},
            JobStatus.RUNNING: {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.PENDING, JobStatus.CANCELLED},
            JobStatus.FAILED: {JobStatus.PENDING} if explicit_retry else set(),
            JobStatus.SUCCEEDED: set(),
            JobStatus.CANCELLED: set(),
        }
        if target not in allowed[self.status]:
            return TransitionResult(self, accepted=False, reason_code=ReasonCode.JOB_ILLEGAL_TRANSITION)
        return TransitionResult(JobState(status=target), accepted=True)


@dataclass(frozen=True)
class AttemptState:
    attempt_number: int
    status: AttemptStatus

    def __post_init__(self) -> None:
        if self.attempt_number < 1:
            raise ValueError("attempt_number must be positive")

    @property
    def is_active(self) -> bool:
        return self.status in {AttemptStatus.LEASED, AttemptStatus.RUNNING}

    def transition(self, target: AttemptStatus) -> TransitionResult[AttemptState]:
        allowed = {
            AttemptStatus.LEASED: {AttemptStatus.RUNNING, AttemptStatus.ABANDONED, AttemptStatus.CANCELLED},
            AttemptStatus.RUNNING: {AttemptStatus.SUCCEEDED, AttemptStatus.FAILED, AttemptStatus.ABANDONED, AttemptStatus.CANCELLED},
            AttemptStatus.SUCCEEDED: set(),
            AttemptStatus.FAILED: set(),
            AttemptStatus.ABANDONED: set(),
            AttemptStatus.CANCELLED: set(),
        }
        if target not in allowed[self.status]:
            return TransitionResult(self, accepted=False, reason_code=ReasonCode.ATTEMPT_ILLEGAL_TRANSITION)
        return TransitionResult(
            AttemptState(attempt_number=self.attempt_number, status=target),
            accepted=True,
        )
