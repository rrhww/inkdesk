from __future__ import annotations

import json
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from fastapi.testclient import TestClient


COOKIE = {"inkdesk_owner_session": "owner"}
CONTRACT_PATH = Path(__file__).resolve().parents[3] / "docs" / "delivery" / "baselines" / "f01" / "contracts" / "behavior-contracts.json"


def _contract_ids() -> set[str]:
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    return {contract["id"] for contract in document["invariants"]}


def _assert_contract_id(contract_id: str) -> None:
    assert contract_id in _contract_ids(), f"missing F01 behavior contract: {contract_id}"


@contextmanager
def _client(temp_app_env: Path) -> Iterator[TestClient]:
    from inkdesk_server.main import create_app

    with TestClient(create_app(), cookies=COOKIE) as client:
        yield client


def _create_run(client: TestClient, title: str = "F01 行为契约") -> str:
    response = client.post("/api/runs", json={
        "type": "PRD",
        "title": title,
        "goal": "F01 当前行为基线",
        "repoContext": "inkdesk",
    })
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _mcp_request(client: TestClient, method: str, params: dict | None = None) -> dict:
    payload: dict[str, object] = {"jsonrpc": "2.0", "method": method, "id": 1}
    if params is not None:
        payload["params"] = params
    response = client.post(
        "/mcp",
        json=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
    )
    match = re.search(r"data:\s*(\{.*\})", response.text, re.DOTALL)
    return json.loads(match.group(1)) if match else response.json()


def test_review_first_write_creates_only_a_pending_proposal(temp_app_env: Path) -> None:
    _assert_contract_id("knowledge.review_first_write")
    with _client(temp_app_env) as client:
        ask = client.post("/api/ask", json={"question": "F01 的 Review-first 规则是什么？"})
        assert ask.status_code == 200, ask.text
        deposited = client.post("/api/deposits", json={
            "source": "answer",
            "askTurnId": ask.json()["id"],
            "payload": {"title": "F01 Review-first", "understanding": "必须先经审阅后才进入 Canonical Wiki。"},
        })

        assert deposited.status_code == 201, deposited.text
        review_id = deposited.json()["reviewId"]
        reviews = client.get("/api/ingest").json()
        assert any(item["id"] == review_id and item["status"] == "PENDING" for item in reviews)
        assert all(item.get("title") != "F01 Review-first" for item in client.get("/api/wiki").json())


def test_illegal_run_transition_returns_a_conflict_with_reason(temp_app_env: Path) -> None:
    _assert_contract_id("runs.illegal_transition")
    with _client(temp_app_env) as client:
        run_id = _create_run(client)
        response = client.post(f"/api/runs/{run_id}/advance", json={"action": "approve"})

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "STAGE_NOT_AWAITING_REVIEW"
    assert isinstance(body["message"], str) and body["message"]


def test_repeated_deposit_is_idempotent(temp_app_env: Path) -> None:
    _assert_contract_id("runs.deposit_idempotency")
    with _client(temp_app_env) as client:
        ask = client.post("/api/ask", json={"question": "这条沉淀只能生成一个 Review。"}).json()
        body = {
            "source": "answer",
            "askTurnId": ask["id"],
            "payload": {"title": "F01 幂等", "understanding": "相同输入不重复产生副作用。"},
        }
        first = client.post("/api/deposits", json=body)
        second = client.post("/api/deposits", json=body)

    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert first.json()["reviewId"] == second.json()["reviewId"]


def test_vault_rejects_absolute_and_escaping_paths(temp_app_env: Path) -> None:
    _assert_contract_id("vault.relative_path_only")
    import pytest
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.vault import VaultService

    vault = VaultService(get_settings())
    with pytest.raises(ValueError):
        vault.resolve("C:/outside.md")
    with pytest.raises(ValueError):
        vault.resolve("../outside.md")


def test_agent_fallback_is_repeatable_without_external_model(temp_app_env: Path) -> None:
    _assert_contract_id("agent.deterministic_fallback")
    from inkdesk_server.agents import AgentRuntime, AskRequestModel
    from inkdesk_server.core.config import get_settings

    runtime = AgentRuntime(get_settings())
    request = AskRequestModel(question="当前最值得先确认什么？", mode="vault", pendingReviewCount=0)

    assert runtime.answer(request).model_dump() == runtime.answer(request).model_dump()


def test_mcp_public_tool_contract_has_names_and_input_error_boundary(temp_app_env: Path) -> None:
    _assert_contract_id("mcp.public_tool_contract")
    with _client(temp_app_env) as client:
        _mcp_request(client, "notifications/initialized", {})
        listed = _mcp_request(client, "tools/list")
        bad_search = _mcp_request(client, "tools/call", {"name": "search", "arguments": {"query": ""}})

    names = {tool["name"] for tool in listed["result"]["tools"]}
    assert names >= {"context_pack", "search", "deposit", "health_check"}
    error_body = json.loads(bad_search["result"]["content"][0]["text"])
    assert "error" in error_body
