from datetime import UTC, datetime, timedelta

from inkdesk_server.infrastructure.jobs.domain import JobStatus, ReasonCode
from inkdesk_server.infrastructure.jobs.policies import JobCommand


NOW = datetime(2026, 7, 16, 16, 0, tzinfo=UTC)


def _enqueue_test_job(db) -> str:
    from inkdesk_server.infrastructure.jobs.repository import DurableJobRepository, JobRequest
    from inkdesk_server.modules.spaces.workspace_adapter import require_workspace_context_by_id

    context = require_workspace_context_by_id(db, workspace_id="workspace-inkdesk")
    job = DurableJobRepository(db).enqueue(
        JobRequest(
            command=JobCommand("test_job", context.organization.id, context.project_space.id, {"value": "ok"}),
            idempotency_key="test-job:one",
            deduplication_key=None,
            subject_type="test",
            subject_id="one",
        ),
        now=NOW,
    )
    db.commit()
    return job.id


def test_durable_worker_claims_registered_handler_and_completes(temp_app_env) -> None:
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.db import get_session_factory
    from inkdesk_server.infrastructure.jobs.registry import JobHandlerRegistry
    from inkdesk_server.infrastructure.jobs.repository import DurableJobRepository
    from inkdesk_server.infrastructure.jobs.worker import DurableWorker
    from inkdesk_server.research import get_research_service

    factory = get_session_factory()
    with factory() as db:
        get_research_service(db, get_settings()).bootstrap_seed_data()
        job_id = _enqueue_test_job(db)

    handled: list[str] = []
    registry = JobHandlerRegistry()
    registry.register("test_job", lambda db, claim: handled.append(claim.job_id) or {"handled": True})
    worker = DurableWorker(factory, registry, worker_id="test-worker", lease_duration=timedelta(seconds=30))

    assert worker.run_once(now=NOW)
    with factory() as db:
        assert DurableJobRepository(db).get_job(job_id).status == JobStatus.SUCCEEDED.value
    assert handled == [job_id]


def test_durable_worker_marks_unregistered_kind_failed_without_payload_logging(temp_app_env) -> None:
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.db import get_session_factory
    from inkdesk_server.infrastructure.jobs.registry import JobHandlerRegistry
    from inkdesk_server.infrastructure.jobs.repository import DurableJobRepository
    from inkdesk_server.infrastructure.jobs.worker import DurableWorker
    from inkdesk_server.research import get_research_service

    factory = get_session_factory()
    with factory() as db:
        get_research_service(db, get_settings()).bootstrap_seed_data()
        job_id = _enqueue_test_job(db)

    worker = DurableWorker(factory, JobHandlerRegistry(), worker_id="test-worker", lease_duration=timedelta(seconds=30))
    assert worker.run_once(now=NOW)

    with factory() as db:
        job = DurableJobRepository(db).get_job(job_id)
        assert job.status == JobStatus.FAILED.value
        assert job.last_error_code == ReasonCode.JOB_HANDLER_NOT_REGISTERED.value
