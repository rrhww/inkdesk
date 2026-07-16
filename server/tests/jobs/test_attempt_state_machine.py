from inkdesk_server.infrastructure.jobs.domain import AttemptState, AttemptStatus, ReasonCode


def test_attempt_allows_documented_transitions() -> None:
    leased = AttemptState(attempt_number=1, status=AttemptStatus.LEASED)
    running = leased.transition(AttemptStatus.RUNNING)

    assert running.accepted is True
    assert running.state.status is AttemptStatus.RUNNING
    assert running.state.transition(AttemptStatus.SUCCEEDED).state.status is AttemptStatus.SUCCEEDED
    assert running.state.transition(AttemptStatus.FAILED).state.status is AttemptStatus.FAILED
    assert leased.transition(AttemptStatus.ABANDONED).state.status is AttemptStatus.ABANDONED
    assert leased.transition(AttemptStatus.CANCELLED).state.status is AttemptStatus.CANCELLED


def test_terminal_attempt_cannot_be_reactivated_or_rewritten() -> None:
    succeeded = AttemptState(attempt_number=3, status=AttemptStatus.SUCCEEDED)

    result = succeeded.transition(AttemptStatus.RUNNING)

    assert result.accepted is False
    assert result.reason_code is ReasonCode.ATTEMPT_ILLEGAL_TRANSITION
    assert result.state is succeeded
