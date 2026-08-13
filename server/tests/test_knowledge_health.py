from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient


def _health_client(temp_app_env: Path, tmp_path: Path, monkeypatch):
    wiki = temp_app_env / "wiki"
    wiki.mkdir(parents=True)
    topic = wiki / "authentication.md"
    topic.write_text(
        """---
title: Authentication
type: topic
claims:
  - text: Access tokens are signed.
    evidence:
      - path: wiki/token-evidence.md
        stance: supports
        excerpt: The signing test verifies the token.
  - text: Refresh tokens never expire.
---
# Authentication

## Open Questions
- How should key rotation work?
""",
        encoding="utf-8",
    )
    (wiki / "token-evidence.md").write_text(
        "---\ntitle: Token Evidence\ntype: source\n---\n# Token Evidence\nThe signing test passes.\n",
        encoding="utf-8",
    )
    database = tmp_path / "health.sqlite"
    monkeypatch.setenv("INKDESK_DATABASE_PATH", str(database))

    from inkdesk_server.core.config import get_settings
    from inkdesk_server.main import create_app

    get_settings.cache_clear()
    return TestClient(create_app()), topic, database


def test_claim_evidence_projection_and_review_do_not_mutate_markdown(
    temp_app_env: Path, tmp_path: Path, monkeypatch
) -> None:
    client, topic_path, database = _health_client(temp_app_env, tmp_path, monkeypatch)
    original = topic_path.read_text(encoding="utf-8")

    with client:
        topics = client.get("/api/knowledge/topics").json()["topics"]
        topic_id = next(item["id"] for item in topics if item["title"] == "Authentication")
        claims = client.get(f"/api/knowledge/topics/{topic_id}/claims")
        assert claims.status_code == 200
        assert len(claims.json()["claims"]) == 2
        supported = next(item for item in claims.json()["claims"] if item["text"].startswith("Access"))
        assert supported["evidence"][0]["stance"] == "supports"

        signals = client.get("/api/knowledge/signals", params={"type": "unsupported"}).json()["signals"]
        signal = next(item for item in signals if item["topicId"] == topic_id)
        acknowledged = client.post(
            f"/api/knowledge/signals/{signal['id']}/actions",
            json={"action": "acknowledge", "ifVersion": signal["version"]},
        )
        assert acknowledged.status_code == 200
        assert acknowledged.json()["status"] == "acknowledged"

        missing_note = client.post(
            f"/api/knowledge/signals/{signal['id']}/actions",
            json={"action": "resolve", "ifVersion": acknowledged.json()["version"]},
        )
        assert missing_note.status_code == 400

        resolved = client.post(
            f"/api/knowledge/signals/{signal['id']}/actions",
            json={"action": "resolve", "ifVersion": acknowledged.json()["version"], "note": "Owner accepted the follow-up."},
        )
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "resolved"

    assert topic_path.read_text(encoding="utf-8") == original
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2


def test_signal_action_uses_optimistic_lock(temp_app_env: Path, tmp_path: Path, monkeypatch) -> None:
    client, _, _ = _health_client(temp_app_env, tmp_path, monkeypatch)
    with client:
        signal = client.get("/api/knowledge/signals", params={"type": "unsupported"}).json()["signals"][0]
        response = client.post(
            f"/api/knowledge/signals/{signal['id']}/actions",
            json={"action": "acknowledge", "ifVersion": signal["version"] + 1},
        )
    assert response.status_code == 409
    assert response.json()["code"] == "VERSION_CONFLICT"
