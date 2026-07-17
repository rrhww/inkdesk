from __future__ import annotations

from inkdesk_server.modules.runs.domain import parse_goal_contract


def valid_contract() -> dict:
    return {
        "purpose": "Create a durable goal contract.",
        "affectedParties": ["Workspace owners"],
        "affectedObjects": [{"kind": "module", "reference": "server/runs", "description": "Run boundary"}],
        "expectedBehaviorChange": "New runs retain a verifiable goal before execution.",
        "technicalSuccessCriteria": [{"name": "persisted", "target": "one", "verification": "automated"}],
        "outcome": {
            "type": "proxy",
            "criteria": [{"name": "adoption", "target": "100%", "verification": "manual"}],
            "proxyRationale": "No direct business metric exists yet.",
        },
        "allowedSideEffects": [],
        "observationWindow": {"durationHours": 24},
        "failureConditions": ["A new run has no contract."],
        "rollbackConditions": ["Legacy runs cannot be read."],
    }


def test_canonical_serialization_trims_text_and_ignores_input_key_order() -> None:
    first = valid_contract()
    first["purpose"] = "  Create a durable goal contract.  "
    reordered = {key: first[key] for key in reversed(list(first))}

    first_contract = parse_goal_contract(first)
    reordered_contract = parse_goal_contract(reordered)

    assert first_contract.canonical_json == reordered_contract.canonical_json
    assert first_contract.hash == reordered_contract.hash
    assert '"purpose":"Create a durable goal contract."' in first_contract.canonical_json


def test_array_order_and_non_ascii_content_are_preserved_in_canonical_form() -> None:
    original = valid_contract()
    original["affectedParties"] = ["产品负责人", "校园用户"]
    changed_order = valid_contract()
    changed_order["affectedParties"] = ["校园用户", "产品负责人"]

    original_contract = parse_goal_contract(original)
    changed_contract = parse_goal_contract(changed_order)

    assert "产品负责人" in original_contract.canonical_json
    assert original_contract.hash != changed_contract.hash
    assert parse_goal_contract(original_contract.as_dict()).as_dict() == original_contract.as_dict()
