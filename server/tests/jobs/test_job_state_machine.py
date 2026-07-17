from inkdesk_server.infrastructure.jobs.domain import JobState, JobStatus, ReasonCode


def test_job_allows_documented_transitions() -> None:
    pending = JobState(status=JobStatus.PENDING)

    assert pending.transition(JobStatus.RUNNING).state.status is JobStatus.RUNNING
    assert pending.transition(JobStatus.CANCELLED).state.status is JobStatus.CANCELLED
    assert JobState(status=JobStatus.RUNNING).transition(JobStatus.SUCCEEDED).state.status is JobStatus.SUCCEEDED
    assert JobState(status=JobStatus.RUNNING).transition(JobStatus.FAILED).state.status is JobStatus.FAILED
    assert JobState(status=JobStatus.RUNNING).transition(JobStatus.PENDING).state.status is JobStatus.PENDING
    assert JobState(status=JobStatus.RUNNING).transition(JobStatus.CANCELLED).state.status is JobStatus.CANCELLED


def test_job_rejects_terminal_and_invalid_transitions() -> None:
    result = JobState(status=JobStatus.SUCCEEDED).transition(JobStatus.RUNNING)

    assert result.accepted is False
    assert result.reason_code is ReasonCode.JOB_ILLEGAL_TRANSITION
    assert result.state.status is JobStatus.SUCCEEDED


def test_failed_job_only_returns_to_pending_via_explicit_retry() -> None:
    failed = JobState(status=JobStatus.FAILED)

    rejected = failed.transition(JobStatus.PENDING)
    accepted = failed.transition(JobStatus.PENDING, explicit_retry=True)

    assert rejected.accepted is False
    assert rejected.reason_code is ReasonCode.JOB_ILLEGAL_TRANSITION
    assert accepted.accepted is True
    assert accepted.state.status is JobStatus.PENDING
