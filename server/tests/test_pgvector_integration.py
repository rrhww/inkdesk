from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_pgvector_health_and_hybrid_ask_path(temporary_postgres_app_env, tmp_path: Path, monkeypatch):
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.db import get_engine, get_session_factory
    from inkdesk_server.db_migrations import main

    monkeypatch.setenv("INKDESK_VAULT_ROOT", str(tmp_path / "vault"))
    monkeypatch.setenv("INKDESK_AUTH_SECRET", "pgvector-test-secret")
    monkeypatch.setenv("INKDESK_AUTH_ALLOW_LEGACY_OWNER_COOKIE", "true")
    monkeypatch.setenv("INKDESK_AGENT_RUNTIME", "deterministic")
    monkeypatch.setenv("INKDESK_ENABLE_WEB_ASSIST", "false")
    monkeypatch.setenv("INKDESK_ENABLE_LOCAL_SEED", "false")
    monkeypatch.setenv("INKDESK_EMBEDDING_PROVIDER_PROFILE", "deterministic")

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    engine = get_engine()
    assert main(["upgrade"]) == 0

    from inkdesk_server.main import create_app

    client = TestClient(create_app())
    client.cookies.set("inkdesk_owner_session", "owner")

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
