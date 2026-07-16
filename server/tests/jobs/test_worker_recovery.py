from datetime import UTC, datetime, timedelta

from inkdesk_server.infrastructure.jobs.domain import AttemptStatus, JobStatus
from inkdesk_server.infrastructure.jobs.policies import JobCommand


NOW = datetime(2026, 7, 16, 19, 0, tzinfo=UTC)


def test_expired_attempt_is_abandoned_and_stale_worker_cannot_finish(temp_app_env) -> None:
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.db import get_session_factory
    from inkdesk_server.infrastructure.jobs.repository import DurableJobRepository, JobRequest
    from inkdesk_server.modules.spaces.workspace_adapter import require_workspace_context_by_id
    from inkdesk_server.research import get_research_service

    factory = get_session_factory()
    with factory() as db:
        get_research_service(db, get_settings()).bootstrap_seed_data()
        context = require_workspace_context_by_id(db, workspace_id="workspace-inkdesk")
        job = DurableJobRepository(db).enqueue(
            JobRequest(
                command=JobCommand("test_job", context.organization.id, context.project_space.id, {}),
                idempotency_key="recovery:one",
                deduplication_key=None,
                subject_type="test",
                subject_id="one",
            ),
            now=NOW,
        )
        first = DurableJobRepository(db).claim(worker_id="crashed-worker", now=NOW, lease_duration=timedelta(seconds=1))
        assert first is not None
        db.commit()

    with factory() as db:
        repository = DurableJobRepository(db)
        assert repository.recover_expired(now=NOW + timedelta(seconds=2)) == 1
        assert not repository.finish(first, status=AttemptStatus.SUCCEEDED, now=NOW + timedelta(seconds=2))
        second = repository.claim(worker_id="replacement-worker", now=NOW + timedelta(seconds=2), lease_duration=timedelta(seconds=30))
        assert second is not None
        assert second.attempt_number == 2
        assert repository.finish(second, status=AttemptStatus.SUCCEEDED, now=NOW + timedelta(seconds=3))
        assert repository.get_job(job.id).status == JobStatus.SUCCEEDED.value
