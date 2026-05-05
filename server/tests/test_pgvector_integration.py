from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skipif(
    not os.getenv("INKVAULT_TEST_PGVECTOR_URL"),
    reason="Set INKVAULT_TEST_PGVECTOR_URL to run the pgvector integration path.",
)
def test_pgvector_health_and_hybrid_ask_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from inkvault_server.core.config import get_settings
    from inkvault_server.db import Base, get_engine, get_session_factory, init_db
    from inkvault_server.main import create_app

    monkeypatch.setenv("INKVAULT_DB_URL", os.environ["INKVAULT_TEST_PGVECTOR_URL"])
    monkeypatch.setenv("INKVAULT_VAULT_ROOT", str(tmp_path / "vault"))
    monkeypatch.setenv("INKVAULT_AUTH_SECRET", "pgvector-test-secret")
    monkeypatch.setenv("INKVAULT_AUTH_ALLOW_LEGACY_OWNER_COOKIE", "true")
    monkeypatch.setenv("INKVAULT_AGENT_RUNTIME", "deterministic")
    monkeypatch.setenv("INKVAULT_ENABLE_WEB_ASSIST", "false")
    monkeypatch.setenv("INKVAULT_ENABLE_LOCAL_SEED", "false")
    monkeypatch.setenv("INKVAULT_EMBEDDING_PROVIDER_PROFILE", "deterministic")

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    init_db()

    client = TestClient(create_app())
    client.cookies.set("inkvault_owner_session", "owner")

    health = client.get("/actuator/health")
    assert health.status_code == 200
    assert health.json()["retrieval"]["pgvectorReady"] is True
    assert health.json()["retrieval"]["retrievalMode"] == "hybrid"

    review_id = client.get("/api/ingest").json()[0]["id"]
    topic_id = client.post(f"/api/ingest/{review_id}/accept").json()["topicId"]
    ask = client.post(
        "/api/ask",
        json={"topicId": topic_id, "question": "这个主题当前最重要的理解是什么？", "mode": "vault"},
    )

    assert ask.status_code == 200
    payload = ask.json()
    assert payload["retrievalMode"] == "hybrid"
    assert payload["usedChunkIds"]
