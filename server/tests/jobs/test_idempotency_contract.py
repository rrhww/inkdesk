from inkdesk_server.infrastructure.jobs.domain import ReasonCode
from inkdesk_server.infrastructure.jobs.policies import JobCommand, decide_idempotency


def test_same_key_and_equivalent_canonical_command_reuses_existing_job() -> None:
    command = JobCommand(
        kind="compile_source",
        organization_id="org-1",
        capability_space_id="space-1",
        payload={"source_id": "source-1", "options": {"force": False, "tags": ["a", "b"]}},
    )
    reordered = JobCommand(
        kind="compile_source",
        organization_id="org-1",
        capability_space_id="space-1",
        payload={"options": {"tags": ["a", "b"], "force": False}, "source_id": "source-1"},
    )

    decision = decide_idempotency(existing_command=command, incoming_command=reordered)

    assert decision.reuse_existing is True
    assert decision.reason_code is None


def test_same_key_with_different_immutable_command_fails_closed() -> None:
    existing = JobCommand("compile_source", "org-1", "space-1", {"source_id": "source-1"})
    incoming = JobCommand("compile_source", "org-1", "space-1", {"source_id": "source-2"})

    decision = decide_idempotency(existing_command=existing, incoming_command=incoming)

    assert decision.reuse_existing is False
    assert decision.reason_code is ReasonCode.JOB_IDEMPOTENCY_CONFLICT
