"""Dependency-free ports implemented by the later durable repository and worker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol

from .domain import AttemptState, JobState
from .policies import JobCommand


class Clock(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True)
class ClaimedJob:
    job_id: str
    command: JobCommand
    job: JobState
    attempt_id: str
    attempt: AttemptState
    lease_token: str


class JobHandler(Protocol):
    def __call__(self, claim: ClaimedJob) -> Mapping[str, Any] | None: ...


class JobRepository(Protocol):
    def enqueue(self, command: JobCommand, *, idempotency_key: str) -> str: ...

    def claim(self, *, worker_id: str, now: datetime) -> ClaimedJob | None: ...
