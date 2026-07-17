"""Pure idempotency, lease, and retry decisions for durable jobs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any, Mapping

from .domain import AttemptState, AttemptStatus, JobStatus, ReasonCode


@dataclass(frozen=True)
class JobCommand:
    kind: str
    organization_id: str
    capability_space_id: str
    payload: Mapping[str, Any]

    def canonical_hash(self) -> str:
        canonical = json.dumps(
            {
                "capability_space_id": self.capability_space_id,
                "kind": self.kind,
                "organization_id": self.organization_id,
                "payload": self.payload,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class IdempotencyDecision:
    reuse_existing: bool
    reason_code: ReasonCode | None = None


def decide_idempotency(*, existing_command: JobCommand, incoming_command: JobCommand) -> IdempotencyDecision:
    if existing_command.canonical_hash() == incoming_command.canonical_hash():
        return IdempotencyDecision(reuse_existing=True)
    return IdempotencyDecision(reuse_existing=False, reason_code=ReasonCode.JOB_IDEMPOTENCY_CONFLICT)


@dataclass(frozen=True)
class LeaseSnapshot:
    attempt: AttemptState
    lease_token: str
    lease_expires_at: datetime


@dataclass(frozen=True)
class HeartbeatDecision:
    snapshot: LeaseSnapshot
    accepted: bool
    reason_code: ReasonCode | None = None


def heartbeat(
    snapshot: LeaseSnapshot,
    *,
    attempt_number: int,
    lease_token: str,
    now: datetime,
    lease_duration: timedelta,
) -> HeartbeatDecision:
    valid = (
        snapshot.attempt.is_active
        and snapshot.attempt.attempt_number == attempt_number
        and snapshot.lease_token == lease_token
        and snapshot.lease_expires_at > now
        and lease_duration > timedelta()
    )
    if not valid:
        return HeartbeatDecision(snapshot=snapshot, accepted=False, reason_code=ReasonCode.JOB_HEARTBEAT_REJECTED)
    renewed = LeaseSnapshot(
        attempt=snapshot.attempt,
        lease_token=snapshot.lease_token,
        lease_expires_at=now + lease_duration,
    )
    return HeartbeatDecision(snapshot=renewed, accepted=True)


@dataclass(frozen=True)
class LeaseRecoveryDecision:
    attempt: AttemptState
    job_status: JobStatus
    reason_code: ReasonCode


def recover_expired_lease(
    snapshot: LeaseSnapshot,
    *,
    now: datetime,
    attempt_count: int,
    max_attempts: int,
) -> LeaseRecoveryDecision:
    if not snapshot.attempt.is_active or snapshot.lease_expires_at > now:
        return LeaseRecoveryDecision(snapshot.attempt, JobStatus.RUNNING, ReasonCode.JOB_NOT_CLAIMABLE)

    abandoned = snapshot.attempt.transition(AttemptStatus.ABANDONED).state
    if attempt_count < max_attempts:
        return LeaseRecoveryDecision(abandoned, JobStatus.PENDING, ReasonCode.JOB_LEASE_EXPIRED)
    return LeaseRecoveryDecision(abandoned, JobStatus.FAILED, ReasonCode.JOB_MAX_ATTEMPTS_EXCEEDED)


class RetryCause(StrEnum):
    LEASE_EXPIRED = "lease_expired"
    HANDLER_FAILED = "handler_failed"
    MANUAL = "manual"


@dataclass(frozen=True)
class RetryDecision:
    retry: bool
    job_status: JobStatus
    next_attempt_number: int | None
    max_attempts: int
    reason_code: ReasonCode | None


def decide_retry(
    *,
    job_status: JobStatus,
    attempt_count: int,
    max_attempts: int,
    cause: RetryCause,
) -> RetryDecision:
    if attempt_count < 0 or max_attempts < 0:
        raise ValueError("attempt counts cannot be negative")

    if cause is RetryCause.MANUAL and job_status is JobStatus.FAILED:
        adjusted_max_attempts = max(max_attempts, attempt_count + 1)
        return RetryDecision(True, JobStatus.PENDING, attempt_count + 1, adjusted_max_attempts, None)

    if cause is RetryCause.LEASE_EXPIRED and job_status is JobStatus.RUNNING:
        if attempt_count < max_attempts:
            return RetryDecision(True, JobStatus.PENDING, attempt_count + 1, max_attempts, ReasonCode.JOB_LEASE_EXPIRED)
        return RetryDecision(False, JobStatus.FAILED, None, max_attempts, ReasonCode.JOB_MAX_ATTEMPTS_EXCEEDED)

    if cause is RetryCause.HANDLER_FAILED:
        return RetryDecision(False, JobStatus.FAILED, None, max_attempts, ReasonCode.JOB_HANDLER_FAILED)

    return RetryDecision(False, job_status, None, max_attempts, ReasonCode.JOB_NOT_CLAIMABLE)
