from datetime import UTC, datetime, timedelta

from inkdesk_server.infrastructure.jobs.domain import AttemptStatus, JobStatus
from inkdesk_server.infrastructure.jobs.policies import JobCommand


NOW = datetime(2026, 7, 16, 15, 0, tzinfo=UTC)


def _request(*, suffix: str = "one"):
    from inkdesk_server.infrastructure.jobs.repository import JobRequest

    return JobRequest(
        command=JobCommand("compile_source", "organization-default", "space", {"source_id": suffix}),
        idempotency_key=f"compile-task:{suffix}",
        deduplication_key=f"compile:workspace:{suffix}",
        subject_type="compile_task",
        subject_id=f"ct-{suffix}",
    )


def test_enqueue_reuses_identical_idempotency_command_and_rejects_conflict(temp_app_env) -> None:
    from inkdesk_server.db import get_session_factory
    from inkdesk_server.infrastructure.jobs.repository import DurableJobRepository, IdempotencyConflictError
    from inkdesk_server.modules.spaces.workspace_adapter import require_workspace_context_by_id
    from inkdesk_server.research import get_research_service
    from inkdesk_server.core.config import get_settings

    with get_session_factory()() as db:
        get_research_service(db, get_settings()).bootstrap_seed_data()
        context = require_workspace_context_by_id(db, workspace_id="workspace-inkdesk")
        request = _request()
        request = request.with_scope(context.organization.id, context.project_space.id)
        repository = DurableJobRepository(db)
        first = repository.enqueue(request, now=NOW)
        second = repository.enqueue(request, now=NOW)
        assert first.id == second.id

        conflict = _request(suffix="other").with_scope(context.organization.id, context.project_space.id)
        conflict = conflict.with_idempotency_key(request.idempotency_key)
        try:
            repository.enqueue(conflict, now=NOW)
        except IdempotencyConflictError:
            pass
        else:
            raise AssertionError("different command with the same idempotency key must fail closed")


def test_claim_heartbeat_fencing_and_expiry_recovery(temp_app_env) -> None:
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.db import get_session_factory
    from inkdesk_server.infrastructure.jobs.repository import DurableJobRepository
    from inkdesk_server.modules.spaces.workspace_adapter import require_workspace_context_by_id
    from inkdesk_server.research import get_research_service

    with get_session_factory()() as db:
        get_research_service(db, get_settings()).bootstrap_seed_data()
        context = require_workspace_context_by_id(db, workspace_id="workspace-inkdesk")
        repository = DurableJobRepository(db)
        repository.enqueue(_request().with_scope(context.organization.id, context.project_space.id), now=NOW)
        db.commit()

        claim = repository.claim(worker_id="worker-a", now=NOW, lease_duration=timedelta(seconds=30))
        assert claim is not None
        assert claim.attempt_number == 1
        assert repository.heartbeat(claim, now=NOW + timedelta(seconds=10), lease_duration=timedelta(seconds=30))
        assert not repository.finish(claim.with_lease_token("stale"), status=AttemptStatus.SUCCEEDED, now=NOW + timedelta(seconds=11))
        assert repository.finish(claim, status=AttemptStatus.SUCCEEDED, now=NOW + timedelta(seconds=11))
        assert repository.get_job(claim.job_id).status == JobStatus.SUCCEEDED.value

        second = repository.enqueue(_request(suffix="expired").with_scope(context.organization.id, context.project_space.id), now=NOW)
        db.commit()
        expired_claim = repository.claim(worker_id="worker-a", now=NOW, lease_duration=timedelta(seconds=1))
        assert expired_claim is not None and expired_claim.job_id == second.id
        recovered = repository.recover_expired(now=NOW + timedelta(seconds=2))
        assert recovered == 1
        assert repository.get_job(second.id).status == JobStatus.PENDING.value


def test_manual_retry_requeues_failed_job_and_grants_a_new_attempt(temp_app_env) -> None:
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.db import get_session_factory
    from inkdesk_server.infrastructure.jobs.repository import DurableJobRepository
    from inkdesk_server.modules.spaces.workspace_adapter import require_workspace_context_by_id
    from inkdesk_server.research import get_research_service

    with get_session_factory()() as db:
        get_research_service(db, get_settings()).bootstrap_seed_data()
        context = require_workspace_context_by_id(db, workspace_id="workspace-inkdesk")
        repository = DurableJobRepository(db)
        job = repository.enqueue(_request().with_scope(context.organization.id, context.project_space.id), now=NOW)
        claim = repository.claim(worker_id="worker-a", now=NOW, lease_duration=timedelta(seconds=30))
        assert claim is not None
        assert repository.finish(claim, status=AttemptStatus.FAILED, now=NOW + timedelta(seconds=1))

        assert repository.manual_retry(job.id, now=NOW + timedelta(seconds=2))
        retried = repository.get_job(job.id)
        assert retried.status == JobStatus.PENDING.value
        assert retried.max_attempts >= 2
        next_claim = repository.claim(worker_id="worker-b", now=NOW + timedelta(seconds=3), lease_duration=timedelta(seconds=30))
        assert next_claim is not None
        assert next_claim.attempt_number == 2
