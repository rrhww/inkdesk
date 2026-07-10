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


def test_context_pack_creates_stage_event(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    run = client.post("/api/runs", json={
        "type": "PRD",
        "title": "测试上下文生成",
        "goal": "验证 context 阶段能生成上下文包",
    }).json()

    resp = client.post(f"/api/runs/{run['id']}/context-pack")

    assert resp.status_code == 200, f"got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["currentStage"] == "context"
    assert data["stageStatus"] == "awaiting_review"

    events = data["events"]
    assert any(e["eventType"] == "context_pack_generated" for e in events)
    assert any(e["stage"] == "context" for e in events)

    ctx_event = next(e for e in events if e["eventType"] == "context_pack_generated")
    payload = ctx_event["payload"]
    assert payload["wikiPageCount"] == 0, "wikiPageCount 当前始终为 0（wiki 上下文尚未实现）"
    assert payload["askHistoryCount"] == 0, "创建的 run 没有关联 Ask 记录"
    assert payload["wikiPageCount"] != payload.get("askHistoryCount", -1) or payload["askHistoryCount"] == 0


def test_deposit_creates_review_proposal(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    run = client.post("/api/runs", json={
        "type": "PRD",
        "title": "测试沉淀",
        "goal": "验证 deposit 阶段能创建提案",
    }).json()
    run_id = run["id"]

    # 推进到 deposit 阶段：每阶段 add_event + advance
    for stage in ["context", "solution", "review", "coding", "testing"]:
        client.post(f"/api/runs/{run_id}/events", json={
            "stage": stage,
            "eventType": "stage_output",
            "payload": {"summary": f"{stage} done"},
        })
        client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})

    # 确认已到达 deposit 阶段
    run_current = client.get(f"/api/runs/{run_id}").json()
    assert run_current["currentStage"] == "deposit"

    # 调用 deposit
    resp = client.post(f"/api/runs/{run_id}/deposit")
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["currentStage"] == "deposit"
    assert data["stageStatus"] == "awaiting_review"

    # 验证事件
    events = data["events"]
    assert any(e["eventType"] == "deposit_created" for e in events)
    assert any(e["stage"] == "deposit" for e in events)

    # 验证 ingest 队列中有新提案
    reviews = client.get("/api/ingest").json()
    assert any(run["title"] in (r.get("title", "") or r.get("proposedTopicTitle", ""))
               for r in reviews), f"expected review item with title containing '{run['title']}'"


def test_solution_generates_draft(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    run = client.post("/api/runs", json={
        "type": "PRD",
        "title": "测试方案生成",
        "goal": "验证 solution 阶段能生成方案草案",
    }).json()
    run_id = run["id"]

    # 推进到 solution 阶段
    client.post(f"/api/runs/{run_id}/events", json={
        "stage": "context",
        "eventType": "stage_output",
        "payload": {"summary": "context done"},
    })
    client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})

    # 确认到达 solution 阶段
    run_current = client.get(f"/api/runs/{run_id}").json()
    assert run_current["currentStage"] == "solution"

    resp = client.post(f"/api/runs/{run_id}/solution")
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["currentStage"] == "solution"
    assert data["stageStatus"] == "awaiting_review"

    events = data["events"]
    assert any(e["eventType"] == "solution_draft_generated" for e in events)
    assert any(e["stage"] == "solution" for e in events)

    # 验证 payload 包含草案文本
    sol_event = next(e for e in events if e["eventType"] == "solution_draft_generated")
    payload = sol_event["payload"]
    assert "draft" in payload
    assert isinstance(payload["draft"], str)
    assert len(payload["draft"]) > 0


def test_review_generates_checklist(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    run = client.post("/api/runs", json={
        "type": "PRD",
        "title": "测试审阅清单",
        "goal": "验证 review 阶段能生成审阅清单",
    }).json()
    run_id = run["id"]

    # 推进到 review 阶段
    for stage in ["context", "solution"]:
        client.post(f"/api/runs/{run_id}/events", json={
            "stage": stage,
            "eventType": "stage_output",
            "payload": {"summary": f"{stage} done"},
        })
        client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})

    run_current = client.get(f"/api/runs/{run_id}").json()
    assert run_current["currentStage"] == "review"

    resp = client.post(f"/api/runs/{run_id}/review")
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["currentStage"] == "review"
    assert data["stageStatus"] == "awaiting_review"

    events = data["events"]
    assert any(e["eventType"] == "review_checklist_generated" for e in events)
    assert any(e["stage"] == "review" for e in events)

    rev_event = next(e for e in events if e["eventType"] == "review_checklist_generated")
    payload = rev_event["payload"]
    assert "checklist" in payload
    assert isinstance(payload["checklist"], list)
    assert len(payload["checklist"]) > 0


def test_coding_execute_prepares_briefing(temp_app_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # mock claude CLI 不可用，避免测试中真的调 claude
    from inkdesk_server.stage_actions import StageActionService
    monkeypatch.setattr(StageActionService, "_claude_available", staticmethod(lambda: False))

    client = _make_client(temp_app_env)

    run = client.post("/api/runs", json={
        "type": "PRD",
        "title": "测试 coding 执行",
        "goal": "验证 coding 阶段能组装 Briefing",
        "repoContext": ".",
    }).json()
    run_id = run["id"]

    # 推进到 coding 阶段
    for stage in ["context", "solution", "review"]:
        client.post(f"/api/runs/{run_id}/events", json={
            "stage": stage,
            "eventType": "stage_output",
            "payload": {"summary": f"{stage} done", "draft": f"## {stage} draft"},
        })
        client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})

    run_current = client.get(f"/api/runs/{run_id}").json()
    assert run_current["currentStage"] == "coding"

    resp = client.post(f"/api/runs/{run_id}/coding/execute")
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.text}"
    data = resp.json()

    events = data["events"]
    # 必须有 briefing_prepared 事件
    assert any(e["eventType"] == "coding_briefing_prepared" for e in events)
    assert any(e["stage"] == "coding" for e in events)

    briefing_event = next(e for e in events if e["eventType"] == "coding_briefing_prepared")
    payload = briefing_event["payload"]
    assert "briefing" in payload
    assert isinstance(payload["briefing"], str)
    assert len(payload["briefing"]) > 0
    # briefing 应包含任务标题
    assert "测试 coding 执行" in payload["briefing"]

    # 因为 claude 不可用，应有 result_submitted 事件标记失败
    result_event = next(e for e in events if e["eventType"] == "coding_result_submitted")
    assert result_event["payload"]["success"] is False


def test_coding_uses_repo_root_not_repo_context(
    temp_app_env: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """repoContext 是标签字符串（如 'inkdesk'），不能作为子进程 cwd。

    execute_coding 应使用 settings.repo_root 作为 Claude Agent SDK 的 cwd，
    而不是把 repoContext 标签当路径用。
    同时验证非交互模式 SDK 选项：setting_sources=[] 禁用 CLAUDE.md、permission_mode=bypassPermissions。
    """
    from inkdesk_server.core.config import get_settings
    from inkdesk_server import stage_actions as stage_actions_module
    from inkdesk_server.stage_actions import StageActionService

    # 准备一个真实存在的 repo_root 目录
    repo_root = tmp_path / "repo-root"
    repo_root.mkdir()
    monkeypatch.setenv("INKDESK_REPO_ROOT", str(repo_root))
    # 用默认值覆盖 .env 里可能存在的覆盖，保证测试可复现
    monkeypatch.setenv("INKDESK_CLAUDE_MAX_TURNS", "20")
    monkeypatch.setenv("INKDESK_CLAUDE_MAX_BUDGET_USD", "1.0")
    # 禁用交互模式，走同步路径（bypassPermissions，无 SSE）
    monkeypatch.setenv("INKDESK_CLAUDE_INTERACTIVE_MODE", "false")
    get_settings.cache_clear()

    # mock claude 可用 + SDK 已安装
    monkeypatch.setattr(StageActionService, "_claude_available", staticmethod(lambda: True))
    monkeypatch.setattr(stage_actions_module, "_CLAUDE_SDK_AVAILABLE", True)

    # 捕获传给 claude_query 的参数
    captured: dict = {}

    async def _fake_query(*, prompt, options):
        captured["prompt"] = prompt
        captured["cwd"] = options.cwd
        captured["setting_sources"] = options.setting_sources
        captured["permission_mode"] = options.permission_mode
        captured["max_turns"] = options.max_turns
        captured["max_budget_usd"] = options.max_budget_usd

        # 模拟 SDK 流式输出：一个 AssistantMessage + 一个 ResultMessage
        from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

        yield AssistantMessage(content=[TextBlock(text="mock claude output")], model="claude-sonnet-4-5")
        yield ResultMessage(
            subtype="success",
            duration_ms=1500,
            duration_api_ms=1200,
            is_error=False,
            num_turns=3,
            session_id="test-session-id",
            total_cost_usd=0.02,
            result="mock claude output",
        )

    monkeypatch.setattr(stage_actions_module, "claude_query", _fake_query)

    client = _make_client(temp_app_env)

    run = client.post("/api/runs", json={
        "type": "PRD",
        "title": "cwd 测试",
        "goal": "验证 coding 用 repo_root 而不是 repoContext",
        "repoContext": "inkdesk",  # 标签字符串，不是路径
    }).json()
    run_id = run["id"]

    # 推进到 coding 阶段
    for stage in ["context", "solution", "review"]:
        client.post(f"/api/runs/{run_id}/events", json={
            "stage": stage,
            "eventType": "stage_output",
            "payload": {"summary": f"{stage} done"},
        })
        client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})

    resp = client.post(f"/api/runs/{run_id}/coding/execute")
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.text}"

    # 断言 cwd 等于 repo_root，而不是 "inkdesk"
    assert captured.get("cwd") == str(repo_root), (
        f"cwd 应等于 repo_root ({repo_root})，实际是 {captured.get('cwd')!r}"
    )

    # 断言 SDK 选项正确
    assert captured.get("setting_sources") == [], "setting_sources 应为空（禁用 CLAUDE.md）"
    assert captured.get("permission_mode") == "bypassPermissions"
    assert captured.get("max_turns") == 20  # 默认值
    assert captured.get("max_budget_usd") == 1.0  # 默认值

    # 子进程应成功执行（mock）
    data = resp.json()
    result_event = next(e for e in data["events"] if e["eventType"] == "coding_result_submitted")
    assert result_event["payload"]["success"] is True
    assert result_event["payload"]["result"] == "mock claude output"
    assert result_event["payload"]["cost_usd"] == 0.02
    assert result_event["payload"]["session_id"] == "test-session-id"
    assert result_event["payload"]["num_turns"] == 3
    assert result_event["payload"]["tool_uses"] == []


def test_coding_interactive_mode_non_blocking(
    temp_app_env: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """交互模式：execute_coding 非阻塞返回，后台 task 启动，SDK 用 default 权限 + can_use_tool。"""
    from inkdesk_server.core.config import get_settings
    from inkdesk_server import stage_actions as stage_actions_module
    from inkdesk_server.stage_actions import StageActionService
    from inkdesk_server.coding_session import get_session_manager

    repo_root = tmp_path / "repo-root"
    repo_root.mkdir()
    monkeypatch.setenv("INKDESK_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("INKDESK_CLAUDE_MAX_TURNS", "20")
    monkeypatch.setenv("INKDESK_CLAUDE_MAX_BUDGET_USD", "1.0")
    # 交互模式默认开启，但显式设置确保可复现
    monkeypatch.setenv("INKDESK_CLAUDE_INTERACTIVE_MODE", "true")
    get_settings.cache_clear()

    monkeypatch.setattr(StageActionService, "_claude_available", staticmethod(lambda: True))
    monkeypatch.setattr(stage_actions_module, "_CLAUDE_SDK_AVAILABLE", True)

    captured: dict = {}

    async def _fake_query(*, prompt, options):
        captured["permission_mode"] = options.permission_mode
        captured["can_use_tool"] = options.can_use_tool
        captured["include_partial_messages"] = options.include_partial_messages
        captured["setting_sources"] = options.setting_sources
        # 模拟一个简单的对话
        from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock
        yield AssistantMessage(content=[TextBlock(text="interactive mock")], model="claude-sonnet-4-5")
        yield ResultMessage(
            subtype="success", duration_ms=100, duration_api_ms=80,
            is_error=False, num_turns=1, session_id="interactive-session",
            total_cost_usd=0.01, result="interactive mock",
        )

    monkeypatch.setattr(stage_actions_module, "claude_query", _fake_query)

    # 清理 session manager 状态
    manager = get_session_manager()
    manager._sessions.clear()

    client = _make_client(temp_app_env)
    run = client.post("/api/runs", json={
        "type": "PRD", "title": "交互模式测试", "goal": "验证非阻塞 + SSE",
        "repoContext": ".",
    }).json()
    run_id = run["id"]

    for stage in ["context", "solution", "review"]:
        client.post(f"/api/runs/{run_id}/events", json={
            "stage": stage, "eventType": "stage_output", "payload": {"summary": f"{stage}"},
        })
        client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})

    resp = client.post(f"/api/runs/{run_id}/coding/execute")
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.text}"
    data = resp.json()

    # 非阻塞：响应里不应有 coding_result_submitted（后台 task 异步持久化）
    result_events = [e for e in data["events"] if e["eventType"] == "coding_result_submitted"]
    assert len(result_events) == 0, "交互模式不应同步返回结果"

    # session manager 应有 session（task 可能已完成或仍在运行）
    assert manager.get(run_id) is not None, "应有 coding session"

    # 验证 SDK 选项：交互模式用 default 权限 + can_use_tool + include_partial_messages
    # 后台 task 在 portal 的事件循环中运行，需要轮询等待 captured 被填充
    import time
    for _ in range(50):
        if "permission_mode" in captured:
            break
        time.sleep(0.1)

    assert captured.get("permission_mode") == "default", "交互模式应用 default 权限"
    assert captured.get("can_use_tool") is not None, "应设置 can_use_tool 回调"
    assert captured.get("include_partial_messages") is True, "应开启 partial messages"
    assert captured.get("setting_sources") == []

    # 清理：等待 task 完成或取消
    session = manager.get(run_id)
    if session and session.task and not session.task.done():
        session.task.cancel()
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            loop.run_until_complete(asyncio.wait_for(session.task, timeout=2.0))
        except Exception:
            pass
    manager.remove(run_id)


def test_coding_stream_returns_404_when_no_session(temp_app_env: Path) -> None:
    """SSE 端点在没有活跃 session 时返回 404。"""
    from inkdesk_server.coding_session import get_session_manager
    get_session_manager()._sessions.clear()

    client = _make_client(temp_app_env)
    run = client.post("/api/runs", json={
        "type": "PRD", "title": "SSE 404", "goal": "test",
    }).json()
    resp = client.get(f"/api/runs/{run['id']}/coding/stream")
    assert resp.status_code == 404


def test_coding_permission_respond_returns_409_when_no_pending(temp_app_env: Path) -> None:
    """权限回应端点在没有 pending permission 时返回 409。"""
    from inkdesk_server.coding_session import get_session_manager, CodingSession
    manager = get_session_manager()
    manager._sessions.clear()

    client = _make_client(temp_app_env)
    run = client.post("/api/runs", json={
        "type": "PRD", "title": "permission 409", "goal": "test",
    }).json()
    run_id = run["id"]

    # 手动创建一个 session（没有 pending permission）
    manager.get_or_create(run_id)
    resp = client.post(f"/api/runs/{run_id}/coding/permission/respond", json={
        "request_id": "fake-id", "allow": True,
    })
    assert resp.status_code == 409
    manager.remove(run_id)


def test_coding_abort_returns_404_when_no_session(temp_app_env: Path) -> None:
    """中断端点在没有 session 时返回 404。"""
    from inkdesk_server.coding_session import get_session_manager
    get_session_manager()._sessions.clear()

    client = _make_client(temp_app_env)
    run = client.post("/api/runs", json={
        "type": "PRD", "title": "abort 404", "goal": "test",
    }).json()
    resp = client.post(f"/api/runs/{run['id']}/coding/abort")
    assert resp.status_code == 404


def test_coding_session_manager_permission_flow() -> None:
    """单元测试：CodingSessionManager 的权限回路（request → respond → resume）。"""
    import asyncio
    from inkdesk_server.coding_session import get_session_manager, PermissionResponse

    manager = get_session_manager()
    manager._sessions.clear()
    run_id = "test-run-perm"

    session = manager.get_or_create(run_id, permission_timeout=2.0)

    # 启动一个协程模拟 can_use_tool 回调
    async def _simulate_callback():
        response = await manager.request_permission(run_id, "Write", {"file_path": "/tmp/test.txt"})
        return response

    async def _simulate_frontend():
        # 等待 permission request 出现
        await asyncio.sleep(0.1)
        assert session.pending_permission is not None
        request_id = session.pending_permission.request_id
        # 前端回应：拒绝
        ok = manager.respond_permission(run_id, PermissionResponse(
            request_id=request_id, allow=False, reason="test deny",
        ))
        assert ok

    async def _run():
        callback_task = asyncio.create_task(_simulate_callback())
        frontend_task = asyncio.create_task(_simulate_frontend())
        response = await callback_task
        await frontend_task
        return response

    response = asyncio.run(_run())
    assert response.allow is False
    assert response.reason == "test deny"
    manager.remove(run_id)


def test_coding_session_manager_abort() -> None:
    """单元测试：abort 取消 task 并拒绝 pending permission。"""
    import asyncio
    from inkdesk_server.coding_session import get_session_manager, PermissionResponse

    manager = get_session_manager()
    manager._sessions.clear()
    run_id = "test-run-abort"

    session = manager.get_or_create(run_id)

    async def _simulate_callback():
        # 模拟 can_use_tool 等待权限
        response = await manager.request_permission(run_id, "Bash", {"command": "rm -rf /"})
        return response

    async def _run():
        callback_task = asyncio.create_task(_simulate_callback())
        await asyncio.sleep(0.1)
        # 用户中断
        ok = await manager.abort(run_id)
        assert ok
        response = await callback_task
        return response

    response = asyncio.run(_run())
    assert response.allow is False, "中断后权限应被拒绝"
    assert "abort" in (response.reason or "").lower()
    manager.remove(run_id)


def test_coding_session_manager_permission_timeout() -> None:
    """单元测试：权限请求超时后返回 deny。"""
    import asyncio
    from inkdesk_server.coding_session import get_session_manager

    manager = get_session_manager()
    manager._sessions.clear()
    run_id = "test-run-timeout"

    manager.get_or_create(run_id, permission_timeout=0.3)

    async def _run():
        response = await manager.request_permission(run_id, "Write", {"file_path": "x"})
        return response

    response = asyncio.run(_run())
    assert response.allow is False, "超时应返回 deny"
    assert "timeout" in (response.reason or "").lower()
    manager.remove(run_id)


def test_is_dangerous_tool() -> None:
    """单元测试：危险工具判断。"""
    from inkdesk_server.coding_session import is_dangerous_tool

    # 危险工具
    assert is_dangerous_tool("Write")
    assert is_dangerous_tool("Edit")
    assert is_dangerous_tool("Bash")
    assert is_dangerous_tool("PowerShell")
    assert is_dangerous_tool("WebFetch")

    # MCP 危险工具
    assert is_dangerous_tool("mcp__filesystem__write_file")
    assert is_dangerous_tool("mcp__filesystem__delete_file")

    # 只读工具
    assert not is_dangerous_tool("Read")
    assert not is_dangerous_tool("Glob")
    assert not is_dangerous_tool("Grep")
    assert not is_dangerous_tool("mcp__filesystem__read_file")
    assert not is_dangerous_tool("mcp__memory__search")


def test_testing_generates_checklist(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)

    run = client.post("/api/runs", json={
        "type": "PRD",
        "title": "测试 testing 清单",
        "goal": "验证 testing 阶段能生成测试清单",
    }).json()
    run_id = run["id"]

    # 推进到 testing 阶段
    for stage in ["context", "solution", "review", "coding"]:
        client.post(f"/api/runs/{run_id}/events", json={
            "stage": stage,
            "eventType": "stage_output",
            "payload": {"summary": f"{stage} done"},
        })
        client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})

    run_current = client.get(f"/api/runs/{run_id}").json()
    assert run_current["currentStage"] == "testing"

    resp = client.post(f"/api/runs/{run_id}/testing")
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["currentStage"] == "testing"
    assert data["stageStatus"] == "awaiting_review"

    events = data["events"]
    assert any(e["eventType"] == "testing_checklist_generated" for e in events)
    assert any(e["stage"] == "testing" for e in events)

    test_event = next(e for e in events if e["eventType"] == "testing_checklist_generated")
    payload = test_event["payload"]
    assert "checklist" in payload
    assert isinstance(payload["checklist"], list)
    assert len(payload["checklist"]) > 0
    assert "summary" in payload

def test_hard_gate_blocks_solution_when_requirement_empty(temp_app_env: Path) -> None:
    """当 Skill contract 定义 required_input(requirement) gate 且 run.goal 为空时，
    /api/runs/{run_id}/solution 应返回 409 HARD_GATE_FAILED。"""
    import json
    client = _make_client(temp_app_env)

    # 创建 run，goal 为空字符串
    run = client.post("/api/runs", json={
        "type": "PRD",
        "title": "gate 测试",
        "goal": "",
    }).json()
    run_id = run["id"]

    # 推进到 solution 阶段
    client.post(f"/api/runs/{run_id}/events", json={
        "stage": "context",
        "eventType": "stage_output",
        "payload": {"summary": "context done"},
    })
    client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})

    # 在 temp vault 下创建 tech-solution skill package（含 required_input gate）
    skills_dir = temp_app_env / "skills" / "tech-solution"
    skills_dir.mkdir(parents=True, exist_ok=True)
    contract = {
        "schemaVersion": "1.0",
        "id": "tech-solution",
        "version": "0.1.0",
        "status": "draft",
        "category": "engineering",
        "kind": "producer",
        "summary": "测试用 solution skill",
        "inputs": [{"name": "requirement", "type": "string", "required": True, "constraints": "min_length:1"}],
        "contextRequirements": [],
        "outputs": [{"type": "solution_doc", "location": "runs/<run_id>/tech-solution.md", "needsReview": True}],
        "hardGates": [
            {"id": "g-req", "kind": "required_input", "params": {"field": "requirement"}, "on_failure": "需求描述不得为空"},
        ],
        "capabilities": ["read_vault"],
        "writePolicy": {"canonicalWiki": "denied", "runArtifacts": "allowed", "codeRepository": "delegated"},
        "verification": [{"kind": "lint", "description": "lint pass"}],
        "nextSkills": [{"skillId": "tech-review"}],
        "supportedRuntimes": ["inkdesk"],
    }
    (skills_dir / "contract.json").write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
    (skills_dir / "SKILL.md").write_text("# tech-solution\n\n测试用。\n", encoding="utf-8")

    # 清除 SkillLoader 缓存（可能在 app 启动时已缓存 None）
    from inkdesk_server.skill_loader import get_skill_loader
    get_skill_loader(str(temp_app_env)).clear_cache()

    # 调用 solution API，应返回 409
    resp = client.post(f"/api/runs/{run_id}/solution")
    assert resp.status_code == 409, f"expected 409, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["code"] == "HARD_GATE_FAILED"
    assert "需求描述" in body["message"]


def test_hard_gate_passes_when_requirement_present(temp_app_env: Path) -> None:
    """当 required_input(requirement) gate 检查通过时，solution 正常执行。"""
    import json
    client = _make_client(temp_app_env)

    run = client.post("/api/runs", json={
        "type": "PRD",
        "title": "gate 通过测试",
        "goal": "有明确目标",
    }).json()
    run_id = run["id"]

    # 推进到 solution 阶段
    client.post(f"/api/runs/{run_id}/events", json={
        "stage": "context",
        "eventType": "stage_output",
        "payload": {"summary": "context done"},
    })
    client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})

    # 创建 tech-solution skill package
    skills_dir = temp_app_env / "skills" / "tech-solution"
    skills_dir.mkdir(parents=True, exist_ok=True)
    contract = {
        "schemaVersion": "1.0", "id": "tech-solution", "version": "0.1.0", "status": "draft",
        "category": "engineering", "kind": "producer",
        "summary": "测试用 solution skill",
        "inputs": [{"name": "requirement", "type": "string", "required": True, "constraints": "min_length:1"}],
        "contextRequirements": [],
        "outputs": [{"type": "solution_doc", "location": "runs/<run_id>/tech-solution.md", "needsReview": True}],
        "hardGates": [
            {"id": "g-req", "kind": "required_input", "params": {"field": "requirement"}, "on_failure": "需求描述不得为空"},
        ],
        "capabilities": ["read_vault"],
        "writePolicy": {"canonicalWiki": "denied", "runArtifacts": "allowed", "codeRepository": "delegated"},
        "verification": [{"kind": "lint", "description": "lint pass"}],
        "nextSkills": [{"skillId": "tech-review"}],
        "supportedRuntimes": ["inkdesk"],
    }
    (skills_dir / "contract.json").write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
    (skills_dir / "SKILL.md").write_text("# tech-solution\n\n测试用。\n", encoding="utf-8")

    from inkdesk_server.skill_loader import get_skill_loader
    get_skill_loader(str(temp_app_env)).clear_cache()

    # 调用 solution API，应正常执行
    resp = client.post(f"/api/runs/{run_id}/solution")
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"


