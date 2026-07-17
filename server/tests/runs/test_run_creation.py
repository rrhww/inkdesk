from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


COOKIE = {"inkdesk_owner_session": "owner"}


def _contract() -> dict:
    return {
        "purpose": "Create a Run with a fixed Goal Contract.",
        "affectedParties": ["Workspace owners"],
        "affectedObjects": [{"kind": "module", "reference": "server/runs", "description": "Run boundary"}],
        "expectedBehaviorChange": "The Run stores a structured goal before execution.",
        "technicalSuccessCriteria": [{"name": "atomic", "target": "one contract", "verification": "automated"}],
        "outcome": {"type": "proxy", "criteria": [{"name": "coverage", "target": "100%", "verification": "automated"}], "proxyRationale": "No direct outcome source exists."},
        "allowedSideEffects": [],
        "observationWindow": {"durationHours": 24},
        "failureConditions": ["A new Run has no contract."],
        "rollbackConditions": ["Legacy Run reads fail."],
    }


def _client(temp_app_env: Path) -> TestClient:
    from inkdesk_server.main import create_app

    return TestClient(create_app(), cookies=COOKIE)


def test_new_run_persists_structured_contract_scope_and_created_event(temp_app_env: Path) -> None:
    response = _client(temp_app_env).post(
        "/api/runs",
        json={"type": "PRD", "title": "Structured run", "repoContext": "inkdesk", "goalContract": _contract()},
    )

    assert response.status_code == 201, response.text
    run = response.json()
    assert run["goal"] == "Create a Run with a fixed Goal Contract."
    assert run["goalContractState"] == "structured"
    assert run["goalContract"]["schemaVersion"] == 1
    assert len(run["goalContract"]["hash"]) == 64
    assert run["organizationId"] == "organization-default"
    assert run["capabilitySpaceId"]
    assert run["createdByMembershipId"]
    assert run["events"][0]["payload"]["goalContractId"] == run["goalContract"]["id"]


def test_new_run_rejects_missing_contract_with_domain_code(temp_app_env: Path) -> None:
    response = _client(temp_app_env).post("/api/runs", json={"type": "PRD", "title": "Incomplete"})

    assert response.status_code == 422
    assert response.json()["code"] == "GOAL_CONTRACT_REQUIRED"
