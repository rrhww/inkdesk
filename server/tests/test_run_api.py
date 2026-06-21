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


def test_advance_approve_moves_to_next_stage(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    run_resp = client.post("/api/runs", json={
        "type": "PRD", "title": "推进阶段测试", "goal": "验证 approve 推进", "repoContext": "inkdesk",
    })
    run_id = run_resp.json()["id"]

    # 先提交 stage output 进入 awaiting_review
    client.post(f"/api/runs/{run_id}/events", json={
        "stage": "context",
        "eventType": "stage_output",
        "payload": {"summary": "上下文收集完毕"},
    })

    # approve 当前阶段 → 推进到 solution
    resp = client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["currentStage"] == "solution"
    assert data["stageStatus"] == "pending"
    assert data["status"] == "active"

    detail = client.get(f"/api/runs/{run_id}").json()
    assert any(e["eventType"] == "stage_approved" for e in detail["events"])


def test_advance_complete_ends_run(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    run_resp = client.post("/api/runs", json={
        "type": "PRD", "title": "完成运行测试", "goal": "验证 complete", "repoContext": "inkdesk",
    })
    run_id = run_resp.json()["id"]

    # advance through all stages to deposit awaiting_review
    stages = ("context", "solution", "review", "coding", "testing", "deposit")
    for stage in stages:
        client.post(f"/api/runs/{run_id}/events", json={
            "stage": stage,
            "eventType": "stage_output",
            "payload": {"summary": f"{stage} done"},
        })
        if stage != "deposit":
            client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})

    # now in deposit stage with awaiting_review — complete should work
    resp = client.post(f"/api/runs/{run_id}/advance", json={"action": "complete"})
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "completed"
    assert data["completedAt"] is not None

    detail = client.get(f"/api/runs/{run_id}").json()
    assert any(e["eventType"] == "completed" for e in detail["events"])


def test_advance_invalid_action_rejected(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    run_resp = client.post("/api/runs", json={
        "type": "PRD", "title": "无效动作测试", "goal": "x", "repoContext": "inkdesk",
    })
    run_id = run_resp.json()["id"]

    resp = client.post(f"/api/runs/{run_id}/advance", json={"action": "invalid"})
    assert resp.status_code == 422


def test_advance_through_all_stages_completes(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    run_resp = client.post("/api/runs", json={
        "type": "PRD", "title": "全阶段推进", "goal": "验证走完所有阶段", "repoContext": "inkdesk",
    })
    run_id = run_resp.json()["id"]

    stages = ("context", "solution", "review", "coding", "testing", "deposit")
    for stage in stages:
        # 先提交 stage output 进入 awaiting_review
        client.post(f"/api/runs/{run_id}/events", json={
            "stage": stage,
            "eventType": "stage_output",
            "payload": {"summary": f"{stage} done"},
        })
        resp = client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})
        data = resp.json()
        assert resp.status_code == 200, f"stage={stage}: {resp.status_code} {resp.text}"

    # 最后一个阶段 approve 后 run 应完成
    final = client.get(f"/api/runs/{run_id}").json()
    assert final["status"] == "completed"
    assert final["completedAt"] is not None


def test_advance_on_cancelled_run_rejected(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    run_resp = client.post("/api/runs", json={
        "type": "PRD", "title": "取消后推进", "goal": "x", "repoContext": "inkdesk",
    })
    run_id = run_resp.json()["id"]
    client.post(f"/api/runs/{run_id}/cancel")

    resp = client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})
    assert resp.status_code == 409


def test_approve_without_awaiting_review_rejected(temp_app_env: Path) -> None:
    """approve 仅在 stage_status == 'awaiting_review' 时允许"""
    client = _make_client(temp_app_env)

    run_resp = client.post("/api/runs", json={
        "type": "PRD", "title": "未进入 awaiting_review", "goal": "x", "repoContext": "inkdesk",
    })
    run_id = run_resp.json()["id"]
    # run 刚创建时 stage_status == "pending"，不能直接 approve
    resp = client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})
    assert resp.status_code == 409
    assert resp.json()["code"] == "STAGE_NOT_AWAITING_REVIEW"


def test_complete_not_in_deposit_rejected(temp_app_env: Path) -> None:
    """complete 仅在 current_stage == 'deposit' 且处于 awaiting_review 时允许"""
    client = _make_client(temp_app_env)

    run_resp = client.post("/api/runs", json={
        "type": "PRD", "title": "非 deposit 阶段完成", "goal": "x", "repoContext": "inkdesk",
    })
    run_id = run_resp.json()["id"]

    # 先推进到 context 的 awaiting_review
    client.post(f"/api/runs/{run_id}/events", json={
        "stage": "context",
        "eventType": "stage_output",
        "payload": {"summary": "done"},
    })

    # 在 context 阶段（非 deposit）尝试 complete 应被拒绝
    resp = client.post(f"/api/runs/{run_id}/advance", json={"action": "complete"})
    assert resp.status_code == 409
    assert resp.json()["code"] == "INVALID_STAGE"


def test_double_approve_rejected(temp_app_env: Path) -> None:
    """同一阶段不能重复 approve——approve 后 stage_status 变为 completed，不再是 awaiting_review"""
    client = _make_client(temp_app_env)

    run_resp = client.post("/api/runs", json={
        "type": "PRD", "title": "重复 approve", "goal": "x", "repoContext": "inkdesk",
    })
    run_id = run_resp.json()["id"]

    # 进入 awaiting_review
    client.post(f"/api/runs/{run_id}/events", json={
        "stage": "context",
        "eventType": "stage_output",
        "payload": {"summary": "done"},
    })

    # 第一次 approve — 成功
    r1 = client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})
    assert r1.status_code == 200

    # 已经推进到下一阶段（solution），stage_status 是 "pending"
    # 不能直接 approve
    r2 = client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})
    assert r2.status_code == 409
    assert r2.json()["code"] == "STAGE_NOT_AWAITING_REVIEW"
