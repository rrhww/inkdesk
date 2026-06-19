from __future__ import annotations

import json
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from fastapi.testclient import TestClient


COOKIE = {"inkdesk_owner_session": "owner"}


@contextmanager
def _make_client(temp_app_env: Path) -> Iterator[TestClient]:
    from inkdesk_server.main import create_app
    app = create_app()
    app.router.on_startup = None
    app.router.on_shutdown = None
    with TestClient(app, cookies=COOKIE) as client:
        yield client


def _init_vault(client: TestClient) -> None:
    resp = client.post("/api/vault/initialize", json={"vaultType": "general"})
    assert resp.status_code == 200, f"vault init failed: {resp.text}"


def _create_run(client: TestClient) -> str:
    resp = client.post("/api/runs", json={
        "type": "PRD", "title": "MCP 测试 Run", "goal": "验证 MCP 工具",
    })
    assert resp.status_code == 201, f"run create failed: {resp.text}"
    return resp.json()["id"]


def _ask(client: TestClient, question: str, run_id: str | None = None) -> dict:
    body = {"question": question}
    if run_id:
        body["runId"] = run_id
    resp = client.post("/api/ask", json=body)
    assert resp.status_code == 200, f"ask failed: {resp.status_code} {resp.text}"
    return resp.json()


def _mcp_jsonrpc(client: TestClient, method: str, params: dict | None = None) -> dict:
    payload: dict = {"jsonrpc": "2.0", "method": method, "id": 1}
    if params is not None:
        payload["params"] = params

    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    resp = client.post("/mcp", json=payload, headers=headers)
    text = resp.text
    # SSE 格式: event: message\ndata: <json>\n\n
    match = re.search(r"data:\s*(\{.*\})", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    if text.strip():
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return {"_raw": text[:500], "_status": resp.status_code}


def _mcp_initialize(client: TestClient) -> None:
    _mcp_jsonrpc(client, "notifications/initialized", {})


# ── Context Pack ──

def test_context_pack_returns_run_summary(temp_app_env: Path) -> None:
    with _make_client(temp_app_env) as client:
        _init_vault(client)
        _mcp_initialize(client)
        run_id = _create_run(client)
        _ask(client, "这是什么项目？", run_id=run_id)

        result = _mcp_jsonrpc(client, "tools/call", {
            "name": "context_pack",
            "arguments": {"runId": run_id},
        })

        assert "error" not in result, f"unexpected error: {result}"
        content = result["result"]["content"]
        assert len(content) >= 1
        text = content[0]["text"]
        assert run_id in text


def test_context_pack_run_not_found(temp_app_env: Path) -> None:
    with _make_client(temp_app_env) as client:
        _init_vault(client)
        _mcp_initialize(client)

        result = _mcp_jsonrpc(client, "tools/call", {
            "name": "context_pack",
            "arguments": {"runId": "nonexistent"},
        })

        text = result["result"]["content"][0]["text"]
        assert "error" in json.loads(text)


# ── Search ──

def test_search_returns_wiki_and_raw_results(temp_app_env: Path) -> None:
    with _make_client(temp_app_env) as client:
        _init_vault(client)
        _mcp_initialize(client)

        result = _mcp_jsonrpc(client, "tools/call", {
            "name": "search",
            "arguments": {"query": "知识库"},
        })

        assert "error" not in result, f"unexpected error: {result}"
        content = result["result"]["content"]
        assert len(content) >= 1
        text = content[0]["text"]
        assert "知识库" in text or "index" in text.lower()


def test_search_empty_query_rejected(temp_app_env: Path) -> None:
    with _make_client(temp_app_env) as client:
        _init_vault(client)
        _mcp_initialize(client)

        result = _mcp_jsonrpc(client, "tools/call", {
            "name": "search",
            "arguments": {"query": ""},
        })

        text = result["result"]["content"][0]["text"]
        assert "error" in json.loads(text)


# ── Deposit ──

def test_mcp_deposit_creates_review_item(temp_app_env: Path) -> None:
    with _make_client(temp_app_env) as client:
        _init_vault(client)
        _mcp_initialize(client)
        run_id = _create_run(client)

        result = _mcp_jsonrpc(client, "tools/call", {
            "name": "deposit",
            "arguments": {
                "source": "stage_output",
                "runId": run_id,
                "stage": "solution",
                "payload": {
                    "title": "MCP 沉淀测试",
                    "understanding": "外部 Agent 提交的阶段输出",
                },
            },
        })

        assert "error" not in result, f"unexpected error: {result}"
        content = result["result"]["content"]
        text = content[0]["text"]
        assert "review" in text.lower() or "PENDING" in text


def test_mcp_deposit_does_not_directly_write_wiki(temp_app_env: Path) -> None:
    with _make_client(temp_app_env) as client:
        _init_vault(client)
        _mcp_initialize(client)
        run_id = _create_run(client)

        _mcp_jsonrpc(client, "tools/call", {
            "name": "deposit",
            "arguments": {
                "source": "stage_output",
                "runId": run_id,
                "stage": "solution",
                "payload": {
                    "title": "不应直接写入 wiki",
                    "understanding": "这条 deposit 必须走审阅",
                },
            },
        })

        wiki = client.get("/api/wiki").json()
        titles = {t.get("title", "") for t in wiki}
        assert "不应直接写入 wiki" not in titles, "MCP deposit should not directly write to wiki"


def test_mcp_deposit_idempotent(temp_app_env: Path) -> None:
    with _make_client(temp_app_env) as client:
        _init_vault(client)
        _mcp_initialize(client)

        args = {
            "source": "stage_output",
            "payload": {"title": "幂等测试", "understanding": "同一份内容"},
        }

        first = _mcp_jsonrpc(client, "tools/call", {"name": "deposit", "arguments": args})
        second = _mcp_jsonrpc(client, "tools/call", {"name": "deposit", "arguments": args})

        r1 = json.loads(first["result"]["content"][0]["text"])
        r2 = json.loads(second["result"]["content"][0]["text"])
        assert r1["reviewId"] == r2["reviewId"]
        assert r1["isNew"] is True
        assert r2["isNew"] is False


# ── Health Check ──

def test_mcp_health_check_returns_summary(temp_app_env: Path) -> None:
    with _make_client(temp_app_env) as client:
        _init_vault(client)
        _mcp_initialize(client)

        result = _mcp_jsonrpc(client, "tools/call", {
            "name": "health_check",
            "arguments": {},
        })

        assert "error" not in result, f"unexpected error: {result}"
        content = result["result"]["content"]
        text = content[0]["text"]
        assert "totalPages" in text.lower() or "broken" in text.lower() or "total" in text.lower()


# ── tools/list ──

def test_mcp_tools_list_returns_tools(temp_app_env: Path) -> None:
    with _make_client(temp_app_env) as client:
        _init_vault(client)
        _mcp_initialize(client)

        result = _mcp_jsonrpc(client, "tools/list")

        assert "error" not in result, f"unexpected error: {result}"
        tool_names = {t["name"] for t in result["result"]["tools"]}
        assert tool_names >= {"context_pack", "search", "deposit", "health_check"}, f"missing tools: {tool_names}"


# ── 输入验证 ──

def test_search_long_query_rejected(temp_app_env: Path) -> None:
    with _make_client(temp_app_env) as client:
        _init_vault(client)
        _mcp_initialize(client)

        result = _mcp_jsonrpc(client, "tools/call", {
            "name": "search",
            "arguments": {"query": "x" * 2000},
        })

        text = result["result"]["content"][0]["text"]
        assert "error" in json.loads(text)


def test_context_pack_missing_run_id(temp_app_env: Path) -> None:
    with _make_client(temp_app_env) as client:
        _init_vault(client)
        _mcp_initialize(client)

        result = _mcp_jsonrpc(client, "tools/call", {
            "name": "context_pack",
            "arguments": {},
        })

        # FastMCP validates required args before calling tool → isError=true
        assert result["result"]["isError"] is True
