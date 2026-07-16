from datetime import UTC, datetime, timedelta

from inkdesk_server.infrastructure.jobs.domain import AttemptState, AttemptStatus, ReasonCode
from inkdesk_server.infrastructure.jobs.policies import LeaseSnapshot, heartbeat, recover_expired_lease


NOW = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)


def _leased_snapshot(*, lease_expires_at: datetime = NOW + timedelta(seconds=60)) -> LeaseSnapshot:
    return LeaseSnapshot(
        attempt=AttemptState(attempt_number=2, status=AttemptStatus.RUNNING),
        lease_token="current-token",
        lease_expires_at=lease_expires_at,
    )


def test_heartbeat_extends_matching_active_lease() -> None:
    result = heartbeat(
        _leased_snapshot(),
        attempt_number=2,
        lease_token="current-token",
        now=NOW,
        lease_duration=timedelta(seconds=60),
    )

    assert result.accepted is True
    assert result.snapshot.lease_expires_at == NOW + timedelta(seconds=60)


def test_heartbeat_rejects_stale_token_number_and_terminal_attempt() -> None:
    snapshot = _leased_snapshot()

    for attempt_number, token in ((1, "current-token"), (2, "old-token")):
        result = heartbeat(snapshot, attempt_number=attempt_number, lease_token=token, now=NOW, lease_duration=timedelta(seconds=60))
        assert result.accepted is False
        assert result.reason_code is ReasonCode.JOB_HEARTBEAT_REJECTED

    terminal = LeaseSnapshot(
        attempt=AttemptState(attempt_number=2, status=AttemptStatus.SUCCEEDED),
        lease_token="current-token",
        lease_expires_at=NOW + timedelta(seconds=60),
    )
    assert heartbeat(terminal, attempt_number=2, lease_token="current-token", now=NOW, lease_duration=timedelta(seconds=60)).accepted is False


def test_expired_lease_abandons_attempt_and_applies_budget() -> None:
    recoverable = recover_expired_lease(
        _leased_snapshot(lease_expires_at=NOW - timedelta(seconds=1)), now=NOW, attempt_count=2, max_attempts=3
    )
    exhausted = recover_expired_lease(
        _leased_snapshot(lease_expires_at=NOW - timedelta(seconds=1)), now=NOW, attempt_count=3, max_attempts=3
    )

    assert recoverable.reason_code is ReasonCode.JOB_LEASE_EXPIRED
    assert recoverable.attempt.status is AttemptStatus.ABANDONED
    assert recoverable.job_status.value == "pending"
    assert exhausted.job_status.value == "failed"
    assert exhausted.reason_code is ReasonCode.JOB_MAX_ATTEMPTS_EXCEEDED
