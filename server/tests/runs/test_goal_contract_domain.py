from __future__ import annotations

import pytest

from inkdesk_server.modules.runs.domain import GoalContractValidationError, parse_goal_contract


def valid_contract(*, outcome_type: str = "proxy") -> dict:
    outcome = {
        "type": outcome_type,
        "criteria": [{"name": "adoption", "target": "100%", "verification": "manual"}],
    }
    if outcome_type == "proxy":
        outcome["proxyRationale"] = "W01 does not collect direct business metrics."

    return {
        "purpose": "Create a durable goal contract.",
        "affectedParties": ["Workspace owners"],
        "affectedObjects": [
            {
                "kind": "module",
                "reference": "server/inkdesk_server/modules/runs",
                "description": "Run creation boundary",
            }
        ],
        "expectedBehaviorChange": "New runs retain a verifiable goal before execution.",
        "technicalSuccessCriteria": [
            {"name": "contract persisted", "target": "one per run", "verification": "automated"}
        ],
        "outcome": outcome,
        "allowedSideEffects": [],
        "observationWindow": {"durationHours": 24},
        "failureConditions": ["A newly created run has no goal contract."],
        "rollbackConditions": ["The migration prevents legacy runs from being read."],
    }


def test_accepts_minimal_direct_and_proxy_contracts() -> None:
    direct = parse_goal_contract(valid_contract(outcome_type="direct"))
    proxy = parse_goal_contract(valid_contract())

    assert direct.outcome.type == "direct"
    assert direct.outcome.proxy_rationale is None
    assert proxy.outcome.type == "proxy"
    assert proxy.outcome.proxy_rationale == "W01 does not collect direct business metrics."


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda payload: payload.__setitem__("purpose", "   "), "GOAL_CONTRACT_INVALID_TEXT"),
        (lambda payload: payload.__setitem__("affectedParties", []), "GOAL_CONTRACT_INVALID_CARDINALITY"),
        (lambda payload: payload["affectedObjects"][0].__setitem__("kind", "widget"), "GOAL_CONTRACT_INVALID_OBJECT_KIND"),
        (lambda payload: payload["technicalSuccessCriteria"][0].__setitem__("verification", "agent"), "GOAL_CONTRACT_INVALID_VERIFICATION"),
        (lambda payload: payload["outcome"].pop("proxyRationale"), "GOAL_CONTRACT_PROXY_RATIONALE_REQUIRED"),
        (lambda payload: payload.__setitem__("observationWindow", {"durationHours": -1}), "GOAL_CONTRACT_INVALID_OBSERVATION_WINDOW"),
    ],
)
def test_rejects_invalid_contracts_with_stable_codes(mutate, code: str) -> None:
    payload = valid_contract()
    mutate(payload)

    with pytest.raises(GoalContractValidationError) as error:
        parse_goal_contract(payload)

    assert error.value.code == code


def test_direct_contract_rejects_proxy_rationale() -> None:
    payload = valid_contract(outcome_type="direct")
    payload["outcome"]["proxyRationale"] = "not allowed"

    with pytest.raises(GoalContractValidationError) as error:
        parse_goal_contract(payload)

    assert error.value.code == "GOAL_CONTRACT_DIRECT_RATIONALE_FORBIDDEN"
