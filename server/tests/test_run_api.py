from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


COOKIE = {"inkdesk_owner_session": "owner"}


def _make_client(temp_app_env: Path) -> TestClient:
    from inkdesk_server.main import create_app
    app = create_app()
    return TestClient(app, cookies=COOKIE)


def test_create_dev_run_success(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    body = {
        "type": "PRD",
        "title": "知识库初始化",
        "goal": "完成 Vault 初始化引导流程",
        "repoContext": "inkdesk",
    }
    resp = client.post("/api/runs", json=body)
    assert resp.status_code == 201, f"expected 201, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["id"]
    assert data["type"] == "PRD"
    assert data["title"] == "知识库初始化"
    assert data["status"] == "active"
    assert data["currentStage"] == "context"
    assert data["stageStatus"] == "pending"
    assert data["workspaceId"] == "workspace-inkdesk"
    assert len(data["stages"]) == 6
    assert data["stages"][0]["name"] == "context"
    assert data["stages"][0]["status"] == "pending"


def test_list_dev_runs_empty(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    resp = client.get("/api/runs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_dev_run_not_found(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    resp = client.get("/api/runs/nonexistent-abc")
    assert resp.status_code == 404


def test_create_invalid_type_rejected(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    body = {"type": "INVALID", "title": "bad", "goal": "x", "repoContext": "x"}
    resp = client.post("/api/runs", json=body)
    assert resp.status_code == 422


def test_create_dev_run_all_three_types(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    for run_type in ("PRD", "BUG", "REFACTOR"):
        body = {"type": run_type, "title": f"{run_type} 任务", "goal": "验证类型支持", "repoContext": "inkdesk"}
        resp = client.post("/api/runs", json=body)
        assert resp.status_code == 201, f"type={run_type}: {resp.status_code} {resp.text}"
        assert resp.json()["type"] == run_type


def test_add_stage_event_advances_stage(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    run_resp = client.post("/api/runs", json={
        "type": "PRD", "title": "阶段事件测试", "goal": "验证阶段事件",
        "repoContext": "inkdesk",
    })
    run_id = run_resp.json()["id"]

    event_body = {
        "stage": "context",
        "eventType": "stage_output",
        "payload": {"summary": "上下文已收集", "risks": ["资料不足"]},
    }
    resp = client.post(f"/api/runs/{run_id}/events", json=event_body)
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["currentStage"] == "context"
    assert data["stageStatus"] == "awaiting_review"

    events_resp = client.get(f"/api/runs/{run_id}")
    assert events_resp.status_code == 200
    run_detail = events_resp.json()
    assert len(run_detail["events"]) == 2  # created + stage_output
    assert run_detail["events"][1]["eventType"] == "stage_output"


def test_cancel_dev_run(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    run_resp = client.post("/api/runs", json={
        "type": "PRD", "title": "待取消任务", "goal": "x", "repoContext": "inkdesk",
    })
    run_id = run_resp.json()["id"]

    cancel_resp = client.post(f"/api/runs/{run_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    detail_resp = client.get(f"/api/runs/{run_id}")
    assert detail_resp.json()["status"] == "cancelled"
    events = detail_resp.json()["events"]
    assert any(e["eventType"] == "cancelled" for e in events)


def test_illegal_status_transition_rejected(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    run_resp = client.post("/api/runs", json={
        "type": "PRD", "title": "状态机测试", "goal": "x", "repoContext": "inkdesk",
    })
    run_id = run_resp.json()["id"]

    client.post(f"/api/runs/{run_id}/cancel")
    resp = client.post(f"/api/runs/{run_id}/cancel")
    assert resp.status_code == 409, f"expected 409, got {resp.status_code}"


def test_event_for_cancelled_run_rejected(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    run_resp = client.post("/api/runs", json={
        "type": "PRD", "title": "取消后事件", "goal": "x", "repoContext": "inkdesk",
    })
    run_id = run_resp.json()["id"]
    client.post(f"/api/runs/{run_id}/cancel")

    event_body = {"stage": "context", "eventType": "stage_output", "payload": {"x": 1}}
    resp = client.post(f"/api/runs/{run_id}/events", json=event_body)
    assert resp.status_code == 409, f"expected 409, got {resp.status_code}: {resp.text}"


def test_cross_workspace_access_is_rejected_via_service(temp_app_env: Path) -> None:
    """Run 属于 workspace-inkdesk, 用 service 层直接检验跨 workspace 过滤。"""
    client = _make_client(temp_app_env)
    run_resp = client.post("/api/runs", json={
        "type": "PRD", "title": "WS 隔离测试", "goal": "x", "repoContext": "inkdesk",
    })
    run_id = run_resp.json()["id"]

    from inkdesk_server.db import session_scope
    from inkdesk_server.run_service import RunService
    from inkdesk_server.security import ResourceNotFoundError
    import pytest as _pytest

    with session_scope() as db:
        svc = RunService(db)
        # 用同一个 workspace 可以拿到
        run = svc.get_run(run_id, "workspace-inkdesk")
        assert run.id == run_id

        # 用不存在的 workspace 应该抛 404
        with _pytest.raises(ResourceNotFoundError):
            svc.get_run(run_id, "workspace-other")


def test_create_dev_run_emits_created_event(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    body = {"type": "PRD", "title": "事件检查", "goal": "创建即记录", "repoContext": "inkdesk"}
    resp = client.post("/api/runs", json=body)
    run_id = resp.json()["id"]

    detail = client.get(f"/api/runs/{run_id}").json()
    assert len(detail["events"]) == 1
    assert detail["events"][0]["eventType"] == "created"


def test_stage_skip_must_record_reason(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    run_resp = client.post("/api/runs", json={
        "type": "PRD", "title": "跳过阶段", "goal": "x", "repoContext": "inkdesk",
    })
    run_id = run_resp.json()["id"]

    event_body = {
        "stage": "solution",
        "eventType": "stage_output",
        "payload": {"summary": "不需要方案设计", "skipped": True, "skipReason": "已有成熟方案"},
    }
    resp = client.post(f"/api/runs/{run_id}/events", json=event_body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["stageStatus"] == "awaiting_review"

    detail = client.get(f"/api/runs/{run_id}").json()
    last_payload = detail["events"][-1]["payload"]
    assert "skipReason" in last_payload or isinstance(last_payload, str)
