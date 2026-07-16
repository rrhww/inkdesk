from inkdesk_server.infrastructure.jobs.domain import JobStatus, ReasonCode
from inkdesk_server.infrastructure.jobs.policies import RetryCause, decide_retry


def test_lease_loss_retries_within_budget_and_returns_next_attempt_number() -> None:
    decision = decide_retry(
        job_status=JobStatus.RUNNING,
        attempt_count=2,
        max_attempts=3,
        cause=RetryCause.LEASE_EXPIRED,
    )

    assert decision.retry is True
    assert decision.job_status is JobStatus.PENDING
    assert decision.next_attempt_number == 3


def test_lease_loss_fails_when_budget_is_exhausted() -> None:
    decision = decide_retry(
        job_status=JobStatus.RUNNING,
        attempt_count=3,
        max_attempts=3,
        cause=RetryCause.LEASE_EXPIRED,
    )

    assert decision.retry is False
    assert decision.job_status is JobStatus.FAILED
    assert decision.reason_code is ReasonCode.JOB_MAX_ATTEMPTS_EXCEEDED


def test_business_errors_do_not_automatically_retry() -> None:
    decision = decide_retry(
        job_status=JobStatus.RUNNING,
        attempt_count=1,
        max_attempts=3,
        cause=RetryCause.HANDLER_FAILED,
    )

    assert decision.retry is False
    assert decision.job_status is JobStatus.FAILED
    assert decision.reason_code is ReasonCode.JOB_HANDLER_FAILED


def test_manual_retry_grants_one_new_attempt_without_erasing_history() -> None:
    decision = decide_retry(
        job_status=JobStatus.FAILED,
        attempt_count=3,
        max_attempts=3,
        cause=RetryCause.MANUAL,
    )

    assert decision.retry is True
    assert decision.job_status is JobStatus.PENDING
    assert decision.next_attempt_number == 4
    assert decision.max_attempts == 4
