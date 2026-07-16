"""SQLAlchemy repository for durable Job and JobAttempt state changes."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
import json
from secrets import token_urlsafe
from uuid import uuid4

from sqlalchemy import Select, select, update
from sqlalchemy.orm import Session

from .domain import AttemptStatus, JobStatus, ReasonCode
from .models import Job, JobAttempt
from .policies import JobCommand


class IdempotencyConflictError(RuntimeError):
    code = ReasonCode.JOB_IDEMPOTENCY_CONFLICT


@dataclass(frozen=True)
class JobRequest:
    command: JobCommand
    idempotency_key: str
    deduplication_key: str | None
    subject_type: str
    subject_id: str
    priority: int = 0
    max_attempts: int = 3

    def with_scope(self, organization_id: str, capability_space_id: str) -> JobRequest:
        return replace(
            self,
            command=JobCommand(
                kind=self.command.kind,
                organization_id=organization_id,
                capability_space_id=capability_space_id,
                payload=self.command.payload,
            ),
        )

    def with_idempotency_key(self, idempotency_key: str) -> JobRequest:
        return replace(self, idempotency_key=idempotency_key)


@dataclass(frozen=True)
class ClaimedJob:
    job_id: str
    kind: str
    subject_type: str
    subject_id: str
    payload: dict[str, object]
    attempt_id: str
    attempt_number: int
    lease_token: str

    def with_lease_token(self, lease_token: str) -> ClaimedJob:
        return replace(self, lease_token=lease_token)


class DurableJobRepository:
    def __init__(self, db: Session):
        self.db = db

    def enqueue(self, request: JobRequest, *, now: datetime) -> Job:
        existing = self.db.scalar(select(Job).where(Job.idempotency_key == request.idempotency_key))
        if existing is not None:
            if self._matches_command(existing, request.command):
                return existing
            raise IdempotencyConflictError(ReasonCode.JOB_IDEMPOTENCY_CONFLICT.value)

        if request.deduplication_key is not None:
            duplicate = self.db.scalar(
                select(Job).where(
                    Job.kind == request.command.kind,
                    Job.organization_id == request.command.organization_id,
                    Job.capability_space_id == request.command.capability_space_id,
                    Job.deduplication_key == request.deduplication_key,
                    Job.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value]),
                )
            )
            if duplicate is not None:
                return duplicate

        job = Job(
            id=f"job-{uuid4().hex}",
            organization_id=request.command.organization_id,
            capability_space_id=request.command.capability_space_id,
            kind=request.command.kind,
            subject_type=request.subject_type,
            subject_id=request.subject_id,
            idempotency_key=request.idempotency_key,
            deduplication_key=request.deduplication_key,
            payload_json=json.dumps(request.command.payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
            status=JobStatus.PENDING.value,
            priority=request.priority,
            available_at=now,
            attempt_count=0,
            max_attempts=request.max_attempts,
            created_at=now,
            updated_at=now,
        )
        self.db.add(job)
        self.db.flush()
        return job

    def claim(self, *, worker_id: str, now: datetime, lease_duration: timedelta) -> ClaimedJob | None:
        if lease_duration <= timedelta():
            raise ValueError("lease_duration must be positive")
        query: Select[tuple[Job]] = (
            select(Job)
            .where(Job.status == JobStatus.PENDING.value, Job.available_at <= now)
            .order_by(Job.priority.desc(), Job.available_at, Job.created_at)
            .limit(1)
        )
        if self.db.bind is not None and self.db.bind.dialect.name == "postgresql":
            query = query.with_for_update(skip_locked=True)
        job = self.db.scalar(query)
        if job is None:
            return None

        active_attempt = self.db.scalar(
            select(JobAttempt.id).where(
                JobAttempt.job_id == job.id,
                JobAttempt.status.in_([AttemptStatus.LEASED.value, AttemptStatus.RUNNING.value]),
            )
        )
        if active_attempt is not None:
            return None

        attempt_number = job.attempt_count + 1
        attempt = JobAttempt(
            id=f"attempt-{uuid4().hex}",
            job_id=job.id,
            attempt_number=attempt_number,
            status=AttemptStatus.LEASED.value,
            worker_id=worker_id,
            lease_token=token_urlsafe(32),
            leased_at=now,
            lease_expires_at=now + lease_duration,
            heartbeat_at=now,
            created_at=now,
        )
        job.status = JobStatus.RUNNING.value
        job.attempt_count = attempt_number
        job.updated_at = now
        self.db.add(attempt)
        self.db.add(job)
        self.db.flush()
        return ClaimedJob(
            job_id=job.id,
            kind=job.kind,
            subject_type=job.subject_type,
            subject_id=job.subject_id,
            payload=json.loads(job.payload_json),
            attempt_id=attempt.id,
            attempt_number=attempt.attempt_number,
            lease_token=attempt.lease_token,
        )

    def heartbeat(self, claim: ClaimedJob, *, now: datetime, lease_duration: timedelta) -> bool:
        if lease_duration <= timedelta():
            return False
        result = self.db.execute(
            update(JobAttempt)
            .where(
                JobAttempt.id == claim.attempt_id,
                JobAttempt.job_id == claim.job_id,
                JobAttempt.attempt_number == claim.attempt_number,
                JobAttempt.lease_token == claim.lease_token,
                JobAttempt.status.in_([AttemptStatus.LEASED.value, AttemptStatus.RUNNING.value]),
                JobAttempt.lease_expires_at > now,
            )
            .values(heartbeat_at=now, lease_expires_at=now + lease_duration)
        )
        return result.rowcount == 1

    def finish(
        self,
        claim: ClaimedJob,
        *,
        status: AttemptStatus,
        now: datetime,
        error_code: ReasonCode | None = None,
        error_message: str | None = None,
        result: dict[str, object] | None = None,
    ) -> bool:
        if status not in {AttemptStatus.SUCCEEDED, AttemptStatus.FAILED, AttemptStatus.CANCELLED}:
            raise ValueError("finish status must be terminal")
        job = self.db.scalar(
            select(Job)
            .where(Job.id == claim.job_id, Job.status == JobStatus.RUNNING.value)
            .with_for_update()
        )
        attempt = self.db.scalar(
            select(JobAttempt)
            .where(
                JobAttempt.id == claim.attempt_id,
                JobAttempt.job_id == claim.job_id,
                JobAttempt.attempt_number == claim.attempt_number,
                JobAttempt.lease_token == claim.lease_token,
                JobAttempt.status.in_([AttemptStatus.LEASED.value, AttemptStatus.RUNNING.value]),
                JobAttempt.lease_expires_at > now,
            )
            .with_for_update()
        )
        if job is None or attempt is None:
            return False

        attempt.status = status.value
        attempt.finished_at = now
        attempt.error_code = error_code.value if error_code else None
        attempt.error_message = self._safe_error(error_message)
        attempt.result_json = json.dumps(result, ensure_ascii=True, sort_keys=True) if result is not None else None
        job.status = {
            AttemptStatus.SUCCEEDED: JobStatus.SUCCEEDED.value,
            AttemptStatus.FAILED: JobStatus.FAILED.value,
            AttemptStatus.CANCELLED: JobStatus.CANCELLED.value,
        }[status]
        job.last_error_code = attempt.error_code
        job.last_error_message = attempt.error_message
        job.updated_at = now
        job.completed_at = now if status is AttemptStatus.SUCCEEDED else None
        job.cancelled_at = now if status is AttemptStatus.CANCELLED else None
        self.db.add_all([attempt, job])
        self.db.flush()
        return True

    def recover_expired(self, *, now: datetime) -> int:
        attempts = self.db.scalars(
            select(JobAttempt)
            .where(
                JobAttempt.status.in_([AttemptStatus.LEASED.value, AttemptStatus.RUNNING.value]),
                JobAttempt.lease_expires_at <= now,
            )
            .with_for_update(skip_locked=self.db.bind is not None and self.db.bind.dialect.name == "postgresql")
        ).all()
        recovered = 0
        for attempt in attempts:
            job = self.db.scalar(select(Job).where(Job.id == attempt.job_id).with_for_update())
            if job is None or job.status != JobStatus.RUNNING.value:
                continue
            attempt.status = AttemptStatus.ABANDONED.value
            attempt.finished_at = now
            attempt.error_code = ReasonCode.JOB_LEASE_EXPIRED.value
            attempt.error_message = "Lease expired before completion."
            job.updated_at = now
            if job.attempt_count < job.max_attempts:
                job.status = JobStatus.PENDING.value
                job.last_error_code = ReasonCode.JOB_LEASE_EXPIRED.value
                job.last_error_message = attempt.error_message
            else:
                job.status = JobStatus.FAILED.value
                job.last_error_code = ReasonCode.JOB_MAX_ATTEMPTS_EXCEEDED.value
                job.last_error_message = "Retry budget exhausted after lease expiry."
            self.db.add_all([attempt, job])
            recovered += 1
        self.db.flush()
        return recovered

    def get_job(self, job_id: str) -> Job:
        job = self.db.get(Job, job_id)
        if job is None:
            raise KeyError(job_id)
        return job

    @staticmethod
    def _matches_command(job: Job, command: JobCommand) -> bool:
        try:
            payload = json.loads(job.payload_json)
        except json.JSONDecodeError:
            return False
        existing = JobCommand(job.kind, job.organization_id, job.capability_space_id, payload)
        return existing.canonical_hash() == command.canonical_hash()

    @staticmethod
    def _safe_error(message: str | None) -> str | None:
        if message is None:
            return None
        return message.replace("\n", " ")[:500]
