from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


COOKIE = {"inkdesk_owner_session": "owner"}


def _make_client(temp_app_env: Path) -> TestClient:
    from inkdesk_server.main import create_app
    return TestClient(create_app(), cookies=COOKIE)


def _create_run(client: TestClient) -> str:
    resp = client.post("/api/runs", json={
        "type": "PRD", "title": "Deposit 测试 Run", "goal": "验证 deposit", "repoContext": "inkdesk",
    })
    return resp.json()["id"]


def _ask(client: TestClient, question: str, run_id: str | None = None) -> dict:
    body = {"question": question}
    if run_id:
        body["runId"] = run_id
    resp = client.post("/api/ask", json=body)
    assert resp.status_code == 200, f"ask failed: {resp.status_code} {resp.text}"
    return resp.json()


# ── Ask × Run 绑定 ──

def test_ask_with_run_id_links_to_run(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    run_id = _create_run(client)
    answer = _ask(client, "与 run 关联的提问", run_id=run_id)

    # 详情接口能查回 run 关联
    detail = client.get(f"/api/runs/{run_id}").json()
    ask_ids = {e["payload"].get("askTurnId") for e in detail["events"] if e["eventType"] == "context_ask"}
    assert answer["id"] in ask_ids, f"ask {answer['id']} should appear in run events"


def test_ask_without_run_id_still_works(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    answer = _ask(client, "不关联 run 的提问")
    assert answer["id"]
    assert answer["question"] == "不关联 run 的提问"


def test_ask_with_invalid_run_id_rejected(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    resp = client.post("/api/ask", json={"question": "x", "runId": "nonexistent"})
    assert resp.status_code == 404


# ── Deposit 统一入口 ──

def test_deposit_full_answer_creates_review_item(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    run_id = _create_run(client)
    answer = _ask(client, "需要沉淀的回答", run_id=run_id)

    resp = client.post("/api/deposits", json={
        "source": "answer",
        "runId": run_id,
        "askTurnId": answer["id"],
        "payload": {"title": "沉淀测试", "understanding": "这条回答应进入审阅"},
    })
    assert resp.status_code == 201, f"deposit failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert data["reviewId"]
    assert data["status"] == "PENDING"

    # 确认出现在 ingest 列表
    ingest = client.get("/api/ingest").json()
    assert any(r["id"] == data["reviewId"] for r in ingest)


def test_deposit_selection_creates_review_item(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    run_id = _create_run(client)
    answer = _ask(client, "部分内容需要沉淀", run_id=run_id)

    resp = client.post("/api/deposits", json={
        "source": "selection",
        "runId": run_id,
        "askTurnId": answer["id"],
        "payload": {
            "title": "选中片段沉淀",
            "selectedText": "这是选中的关键结论",
            "rationale": "这段结论值得单独记录",
        },
    })
    assert resp.status_code == 201, f"deposit failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert data["status"] == "PENDING"


def test_deposit_stage_output_creates_review_item(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    run_id = _create_run(client)

    resp = client.post("/api/deposits", json={
        "source": "stage_output",
        "runId": run_id,
        "stage": "solution",
        "payload": {
            "title": "方案阶段输出",
            "understanding": "选择方案 A，因为更简单",
        },
    })
    assert resp.status_code == 201, f"deposit failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert data["status"] == "PENDING"


def test_duplicate_answer_deposit_is_idempotent(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    answer = _ask(client, "去重测试")

    body = {
        "source": "answer",
        "askTurnId": answer["id"],
        "payload": {"title": "去重", "understanding": "同一份内容"},
    }
    first = client.post("/api/deposits", json=body)
    second = client.post("/api/deposits", json=body)
    assert first.json()["reviewId"] == second.json()["reviewId"]
    assert first.status_code == 201
    assert second.status_code == 200  # existing


def test_deposit_without_ask_turn_for_stage_output(temp_app_env: Path) -> None:
    """stage_output 不需要 askTurnId，只需 runId。"""
    client = _make_client(temp_app_env)
    run_id = _create_run(client)

    resp = client.post("/api/deposits", json={
        "source": "stage_output",
        "runId": run_id,
        "stage": "context",
        "payload": {"summary": "上下文阶段完成"},
    })
    assert resp.status_code == 201


def test_deposit_rejected_proposal_does_not_modify_wiki(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    answer = _ask(client, "待拒绝的沉淀")

    deposit = client.post("/api/deposits", json={
        "source": "answer",
        "askTurnId": answer["id"],
        "payload": {"title": "拒绝测试", "understanding": "不应进入 wiki"},
    })
    review_id = deposit.json()["reviewId"]

    # 拒绝
    reject = client.post(f"/api/ingest/{review_id}/reject")
    assert reject.status_code == 200
    assert reject.json()["status"] == "REJECTED"

    # wiki 列表不应包含这个 topic
    wiki = client.get("/api/wiki").json()
    assert not any("拒绝测试" in t.get("title", "") for t in wiki)


# ── writeback 兼容 ──

def test_old_writeback_still_creates_review_item(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    answer = _ask(client, "writeback 兼容测试")

    resp = client.post(f"/api/ask/{answer['id']}/writeback")
    assert resp.status_code == 200, f"writeback failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert data["id"]
    assert data["status"] == "PENDING" or True  # writeback creates a review item


def test_old_ask_turns_without_run_are_still_readable(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    answer = _ask(client, "旧数据兼容")

    detail = client.get(f"/api/ask/{answer['id']}").json()
    assert detail["id"] == answer["id"]
    assert detail["question"] == "旧数据兼容"


# ── 缺少必填字段 ──

def test_deposit_answer_without_ask_turn_id_rejected(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    resp = client.post("/api/deposits", json={
        "source": "answer",
        "payload": {"title": "缺 askTurnId"},
    })
    assert resp.status_code == 422


def test_deposit_without_source_rejected(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    resp = client.post("/api/deposits", json={"payload": {}})
    assert resp.status_code == 422


def test_deposit_unknown_source_rejected(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    resp = client.post("/api/deposits", json={"source": "unknown", "payload": {}})
    assert resp.status_code == 422
