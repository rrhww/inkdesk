from __future__ import annotations

from pathlib import Path
from time import sleep

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def task_client(temp_app_env: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    wiki_root = temp_app_env / "wiki"
    wiki_root.mkdir(parents=True)
    (wiki_root / "authentication.md").write_text(
        "---\ntitle: Authentication\ntype: concept\nstatus: stable\n---\n"
        "# Authentication\nThe API uses signed access tokens.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("INKDESK_DATABASE_PATH", str(tmp_path / "inkdesk.sqlite"))

    from inkdesk_server.core.config import get_settings
    from inkdesk_server.main import create_app

    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()


def create_task(client: TestClient, **overrides):
    payload = {
        "title": "Implement token refresh",
        "goal": "Add refresh handling to the authentication API",
        "originType": "realtime_requirement",
        "priority": "high",
        "risk": "medium",
    }
    payload.update(overrides)
    response = client.post("/api/tasks", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_filter_tasks_from_multiple_origins(task_client: TestClient) -> None:
    realtime = create_task(task_client)
    manual = create_task(
        task_client,
        title="Clean up retry policy",
        goal="Remove duplicate retry configuration",
        originType="manual",
        priority="low",
        risk="low",
    )

    assert realtime["status"] == "backlog"
    assert realtime["contextStatus"] == "pending"
    assert realtime["version"] == 1
    assert manual["originType"] == "manual"

    filtered = task_client.get(
        "/api/tasks", params={"status": "backlog", "originType": "realtime_requirement"}
    )
    assert filtered.status_code == 200
    assert [task["id"] for task in filtered.json()["tasks"]] == [realtime["id"]]

    detail = task_client.get(f"/api/tasks/{realtime['id']}")
    assert detail.status_code == 200
    assert detail.json()["goal"] == realtime["goal"]


def test_task_creation_schedules_context_assembly(task_client: TestClient) -> None:
    task = create_task(
        task_client,
        title="Review authentication behavior",
        goal="Confirm how the authentication API validates tokens",
    )

    for _ in range(20):
        detail = task_client.get(f"/api/tasks/{task['id']}").json()
        if detail["contextStatus"] in {"ready", "gap", "failed"}:
            break
        sleep(0.02)

    assert detail["contextStatus"] == "ready"


def test_context_assembly_finds_knowledge_and_unlocks_execution(task_client: TestClient) -> None:
    graph = task_client.get("/api/graph", params={"source": "vault"}).json()
    topic_id = next(node["id"] for node in graph["nodes"] if node["label"] == "Authentication")
    task = create_task(task_client, knowledgeTopicIds=[topic_id])

    blocked = task_client.post(
        f"/api/tasks/{task['id']}/transition",
        json={"status": "ready", "ifVersion": task["version"]},
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "TASK_CONTEXT_NOT_READY"

    assembled = task_client.post(f"/api/tasks/{task['id']}/context")
    assert assembled.status_code == 200
    assembled_task = assembled.json()
    assert assembled_task["contextStatus"] == "ready"
    assert assembled_task["contextPack"]["topics"][0]["id"] == topic_id
    assert assembled_task["knowledgeGap"] is None

    ready = task_client.post(
        f"/api/tasks/{task['id']}/transition",
        json={"status": "ready", "ifVersion": assembled_task["version"]},
    )
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"

    doing = task_client.post(
        f"/api/tasks/{task['id']}/transition",
        json={"status": "doing", "ifVersion": ready.json()["version"]},
    )
    assert doing.status_code == 200
    assert doing.json()["status"] == "doing"


def test_context_gap_is_recorded_and_is_a_valid_execution_gate(task_client: TestClient) -> None:
    task = create_task(
        task_client,
        title="Upgrade an undocumented subsystem",
        goal="Change behavior for which the repository has no knowledge source",
    )
    assembled = task_client.post(f"/api/tasks/{task['id']}/context").json()

    assert assembled["contextStatus"] == "gap"
    assert assembled["contextPack"] is None
    assert assembled["knowledgeGap"]["reason"] == "no_relevant_knowledge"

    ready = task_client.post(
        f"/api/tasks/{task['id']}/transition",
        json={"status": "ready", "ifVersion": assembled["version"]},
    )
    assert ready.status_code == 200


def test_transition_rejects_stale_versions_and_invalid_state_changes(task_client: TestClient) -> None:
    task = create_task(task_client)
    assembled = task_client.post(f"/api/tasks/{task['id']}/context").json()

    stale = task_client.post(
        f"/api/tasks/{task['id']}/transition",
        json={"status": "ready", "ifVersion": task["version"]},
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "VERSION_CONFLICT"

    invalid = task_client.post(
        f"/api/tasks/{task['id']}/transition",
        json={"status": "done", "ifVersion": assembled["version"]},
    )
    assert invalid.status_code == 409
    assert invalid.json()["code"] == "INVALID_TASK_TRANSITION"


def test_knowledge_signal_requires_a_traceable_origin(task_client: TestClient) -> None:
    response = task_client.post(
        "/api/tasks",
        json={
            "title": "Resolve conflicting authentication guidance",
            "goal": "Choose the supported token validation approach",
            "originType": "knowledge_signal",
        },
    )

    assert response.status_code == 422


def test_task_storage_survives_app_restart(
    temp_app_env: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "persistent.sqlite"
    monkeypatch.setenv("INKDESK_DATABASE_PATH", str(database_path))

    from inkdesk_server.core.config import get_settings
    from inkdesk_server.main import create_app

    get_settings.cache_clear()
    with TestClient(create_app()) as first_client:
        task = create_task(first_client, originType="manual")

    get_settings.cache_clear()
    with TestClient(create_app()) as second_client:
        restored = second_client.get(f"/api/tasks/{task['id']}")
        assert restored.status_code == 200
        assert restored.json()["id"] == task["id"]


def test_task_stream_exposes_invalidation_only_events(task_client: TestClient) -> None:
    response = task_client.get("/api/tasks/stream", params={"once": "true"})
    assert response.status_code == 200
    assert "event: tasks.updated" in response.text
    assert '"taskId": null' in response.text
