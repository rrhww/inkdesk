from __future__ import annotations

from datetime import UTC, datetime, timedelta
import multiprocessing
from pathlib import Path
import time

import pytest


NOW = datetime(2026, 7, 16, 20, 0, tzinfo=UTC)


def _crash_handler(db, claim):
    marker = Path(claim.payload["marker_path"])
    marker.write_text("claimed", encoding="utf-8")
    time.sleep(60)
    return {"unreachable": True}


def _run_crashing_worker() -> None:
    from inkdesk_server.db import get_session_factory
    from inkdesk_server.infrastructure.jobs.registry import JobHandlerRegistry
    from inkdesk_server.infrastructure.jobs.worker import DurableWorker

    registry = JobHandlerRegistry()
    registry.register("crash_test", _crash_handler)
    DurableWorker(get_session_factory(), registry, lease_duration=timedelta(seconds=1)).run_once()


@pytest.mark.postgres
def test_process_crash_allows_expired_lease_recovery(temporary_postgres_app_env, tmp_path: Path) -> None:
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.db import get_session_factory
    from inkdesk_server.db_migrations import main
    from inkdesk_server.infrastructure.jobs.policies import JobCommand
    from inkdesk_server.infrastructure.jobs.repository import DurableJobRepository, JobRequest
    from inkdesk_server.modules.spaces.workspace_adapter import require_workspace_context_by_id
    from inkdesk_server.research import get_research_service

    assert main(["upgrade"]) == 0
    factory = get_session_factory()
    marker = tmp_path / "claimed.txt"
    with factory() as db:
        get_research_service(db, get_settings()).bootstrap_seed_data()
        context = require_workspace_context_by_id(db, workspace_id="workspace-inkdesk")
        job = DurableJobRepository(db).enqueue(
            JobRequest(
                command=JobCommand("crash_test", context.organization.id, context.project_space.id, {"marker_path": str(marker)}),
                idempotency_key="crash-test:one",
                deduplication_key=None,
                subject_type="test",
                subject_id="crash-one",
            ),
            now=datetime.now(UTC),
        )
        db.commit()

    process = multiprocessing.get_context("spawn").Process(target=_run_crashing_worker)
    process.start()
    deadline = time.monotonic() + 15
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert marker.exists(), "child worker did not claim the job"
    process.terminate()
    process.join(timeout=10)
    assert process.exitcode is not None

    time.sleep(1.2)
    with factory() as db:
        repository = DurableJobRepository(db)
        assert repository.recover_expired(now=datetime.now(UTC)) == 1
        replacement = repository.claim(worker_id="replacement", now=datetime.now(UTC), lease_duration=timedelta(seconds=30))
        assert replacement is not None
        assert replacement.job_id == job.id
        assert replacement.attempt_number == 2
