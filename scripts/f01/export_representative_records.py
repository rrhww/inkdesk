"""Generate a checked-in, synthetic representative-record contract through public APIs."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from export_postgres_schema import normalize_representative_records


def capture_representative_records() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="inkdesk-f01-records-") as temporary_directory:
        root = Path(temporary_directory)
        _configure_isolated_app(root)
        from inkdesk_server import compile_worker

        class NoopCompileWorker:
            def start(self) -> None:
                return None

            def stop(self) -> None:
                return None

            def enqueue(self, _task_id: str) -> None:
                return None

        original_worker_factory = compile_worker.get_compile_worker
        original_bootstrap = _install_minimal_workspace_bootstrap()
        try:
            compile_worker.get_compile_worker = lambda _settings: NoopCompileWorker()  # type: ignore[assignment]
            from inkdesk_server.main import create_app

            with TestClient(create_app(), cookies={"inkdesk_owner_session": "owner"}) as client:
                client.post("/api/vault/initialize", json={"vaultType": "general"}).raise_for_status()
                source = client.post("/api/raw", json={
                    "kind": "TEXT",
                    "title": "F01 synthetic source",
                    "locator": "https://example.invalid/f01-source",
                    "excerpt": "Synthetic source excerpt.",
                    "body": "Synthetic source body for F01 contract capture.",
                })
                source.raise_for_status()
                compile_task = client.post(f"/api/raw/{source.json()['id']}/compile")
                compile_task.raise_for_status()
                ask = client.post("/api/ask", json={"question": "What does the synthetic F01 source establish?", "mode": "vault"})
                ask.raise_for_status()
                deposit = client.post("/api/deposits", json={
                    "source": "answer",
                    "askTurnId": ask.json()["id"],
                    "payload": {"title": "F01 synthetic proposal", "understanding": "Synthetic proposed understanding."},
                })
                deposit.raise_for_status()
                review = client.post(f"/api/ingest/{deposit.json()['reviewId']}/accept")
                review.raise_for_status()
                run = client.post("/api/runs", json={
                    "type": "PRD",
                    "title": "F01 synthetic Dev Run",
                    "goal": "Capture a representative completed Dev Run.",
                    "repoContext": "inkdesk",
                })
                run.raise_for_status()
                run_id = run.json()["id"]
                for stage in ("context", "solution", "review", "coding", "testing", "deposit"):
                    client.post(f"/api/runs/{run_id}/events", json={
                        "stage": stage,
                        "eventType": "stage_output",
                        "payload": {"summary": f"Synthetic {stage} output."},
                    }).raise_for_status()
                    if stage != "deposit":
                        client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"}).raise_for_status()
                client.post(f"/api/runs/{run_id}/advance", json={"action": "complete"}).raise_for_status()
                queue = client.get("/api/compile/queue")
                queue.raise_for_status()
                records = {
                    "sources": client.get("/api/raw").json(),
                    "reviews": client.get("/api/ingest").json(),
                    "topics": client.get("/api/wiki").json(),
                    "ask": ask.json(),
                    "deposit": deposit.json(),
                    "run": client.get(f"/api/runs/{run_id}").json(),
                    "compileQueue": queue.json(),
                }
        finally:
            compile_worker.get_compile_worker = original_worker_factory
            _restore_workspace_bootstrap(original_bootstrap)
            _dispose_isolated_app()
    return normalize_representative_records(records)


def _configure_isolated_app(root: Path) -> None:
    os.environ["INKDESK_DB_URL"] = f"sqlite+pysqlite:///{root / 'f01-records.db'}"
    os.environ["INKDESK_VAULT_ROOT"] = str(root / "vault")
    os.environ["INKDESK_AGENT_RUNTIME"] = "deterministic"
    os.environ["INKDESK_EMBEDDING_PROVIDER_PROFILE"] = "deterministic"
    os.environ["INKDESK_ENABLE_LOCAL_SEED"] = "false"
    os.environ["INKDESK_ENABLE_WEB_ASSIST"] = "false"
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.db import get_engine, get_session_factory

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


def _dispose_isolated_app() -> None:
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.db import get_engine, get_session_factory

    get_engine().dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    get_settings.cache_clear()


def _install_minimal_workspace_bootstrap():
    from datetime import UTC, datetime

    from sqlalchemy import select

    from inkdesk_server.models import User, Workspace
    from inkdesk_server.research import DEFAULT_WORKSPACE_SLUG, ResearchWorkspaceService

    def bootstrap_minimal_workspace(service: ResearchWorkspaceService) -> None:
        if service.db.scalar(select(User.id).limit(1)):
            return
        now = datetime.now(UTC)
        owner = User(
            id="f01-owner",
            username="f01-owner",
            email="f01-owner@example.invalid",
            password_hash="not-a-real-password",
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
        service.db.add(Workspace(
            id="f01-workspace",
            owner_user=owner,
            name="F01 synthetic workspace",
            slug=DEFAULT_WORKSPACE_SLUG,
            created_at=now,
            updated_at=now,
        ))
        service.db.commit()

    original_bootstrap = ResearchWorkspaceService.bootstrap_seed_data
    ResearchWorkspaceService.bootstrap_seed_data = bootstrap_minimal_workspace
    return original_bootstrap


def _restore_workspace_bootstrap(original_bootstrap) -> None:
    from inkdesk_server.research import ResearchWorkspaceService

    ResearchWorkspaceService.bootstrap_seed_data = original_bootstrap


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(capture_representative_records(), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
