from datetime import UTC, datetime, timedelta

import pytest


NOW = datetime(2026, 7, 16, 18, 0, tzinfo=UTC)


@pytest.mark.postgres
def test_postgres_claim_uses_skip_locked_to_prevent_two_active_attempts(temporary_postgres_app_env) -> None:
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.db import get_session_factory
    from inkdesk_server.db_migrations import main
    from inkdesk_server.infrastructure.jobs.policies import JobCommand
    from inkdesk_server.infrastructure.jobs.repository import DurableJobRepository, JobRequest
    from inkdesk_server.modules.spaces.workspace_adapter import require_workspace_context_by_id
    from inkdesk_server.research import get_research_service

    assert main(["upgrade"]) == 0
    factory = get_session_factory()
    with factory() as setup:
        get_research_service(setup, get_settings()).bootstrap_seed_data()
        context = require_workspace_context_by_id(setup, workspace_id="workspace-inkdesk")
        DurableJobRepository(setup).enqueue(
            JobRequest(
                command=JobCommand("test_job", context.organization.id, context.project_space.id, {}),
                idempotency_key="postgres-claim:one",
                deduplication_key=None,
                subject_type="test",
                subject_id="one",
            ),
            now=NOW,
        )
        setup.commit()

    first_session = factory()
    second_session = factory()
    try:
        first = DurableJobRepository(first_session).claim(
            worker_id="worker-one", now=NOW, lease_duration=timedelta(seconds=60)
        )
        assert first is not None
        second = DurableJobRepository(second_session).claim(
            worker_id="worker-two", now=NOW, lease_duration=timedelta(seconds=60)
        )
        assert second is None
    finally:
        first_session.rollback()
        second_session.rollback()
        first_session.close()
        second_session.close()
