"""Pure Goal Contract v1 value objects and canonical serialization."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping


SCHEMA_VERSION = 1
OBJECT_KINDS = frozenset({"repository", "service", "module", "api", "data", "workflow", "documentation", "infrastructure", "other"})
VERIFICATION_METHODS = frozenset({"automated", "manual"})
OUTCOME_TYPES = frozenset({"direct", "proxy"})


class GoalContractValidationError(ValueError):
    """Stable, transport-independent validation failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class AffectedObject:
    kind: str
    reference: str
    description: str

    def as_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "reference": self.reference, "description": self.description}


@dataclass(frozen=True)
class Criterion:
    name: str
    target: str
    verification: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "target": self.target, "verification": self.verification}


@dataclass(frozen=True)
class Outcome:
    type: str
    criteria: tuple[Criterion, ...]
    proxy_rationale: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "criteria": [criterion.as_dict() for criterion in self.criteria],
            "proxyRationale": self.proxy_rationale,
        }


@dataclass(frozen=True)
class ObservationWindow:
    duration_hours: int

    def as_dict(self) -> dict[str, int]:
        return {"durationHours": self.duration_hours}


@dataclass(frozen=True)
class GoalContract:
    purpose: str
    affected_parties: tuple[str, ...]
    affected_objects: tuple[AffectedObject, ...]
    expected_behavior_change: str
    technical_success_criteria: tuple[Criterion, ...]
    outcome: Outcome
    allowed_side_effects: tuple[str, ...]
    observation_window: ObservationWindow
    failure_conditions: tuple[str, ...]
    rollback_conditions: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "purpose": self.purpose,
            "affectedParties": list(self.affected_parties),
            "affectedObjects": [item.as_dict() for item in self.affected_objects],
            "expectedBehaviorChange": self.expected_behavior_change,
            "technicalSuccessCriteria": [criterion.as_dict() for criterion in self.technical_success_criteria],
            "outcome": self.outcome.as_dict(),
            "allowedSideEffects": list(self.allowed_side_effects),
            "observationWindow": self.observation_window.as_dict(),
            "failureConditions": list(self.failure_conditions),
            "rollbackConditions": list(self.rollback_conditions),
        }

    @property
    def canonical_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @property
    def canonical_bytes(self) -> bytes:
        return self.canonical_json.encode("utf-8")

    @property
    def hash(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()


def parse_goal_contract(payload: Mapping[str, Any] | None) -> GoalContract:
    if payload is None:
        raise GoalContractValidationError("GOAL_CONTRACT_REQUIRED")
    if not isinstance(payload, Mapping):
        raise GoalContractValidationError("GOAL_CONTRACT_REQUIRED")

    outcome_payload = _mapping(payload.get("outcome"), "GOAL_CONTRACT_INVALID_TEXT")
    outcome_type = _enum(outcome_payload.get("type"), OUTCOME_TYPES, "GOAL_CONTRACT_INVALID_TEXT")
    proxy_rationale = _optional_text(outcome_payload.get("proxyRationale"), 2000)
    if outcome_type == "proxy" and proxy_rationale is None:
        raise GoalContractValidationError("GOAL_CONTRACT_PROXY_RATIONALE_REQUIRED")
    if outcome_type == "direct" and proxy_rationale is not None:
        raise GoalContractValidationError("GOAL_CONTRACT_DIRECT_RATIONALE_FORBIDDEN")

    return GoalContract(
        purpose=_text(payload.get("purpose"), 2000),
        affected_parties=_text_list(payload.get("affectedParties"), minimum=1, maximum=20, max_length=240),
        affected_objects=_affected_objects(payload.get("affectedObjects")),
        expected_behavior_change=_text(payload.get("expectedBehaviorChange"), 4000),
        technical_success_criteria=_criteria(payload.get("technicalSuccessCriteria")),
        outcome=Outcome(
            type=outcome_type,
            criteria=_criteria(outcome_payload.get("criteria")),
            proxy_rationale=proxy_rationale,
        ),
        allowed_side_effects=_text_list(payload.get("allowedSideEffects"), minimum=0, maximum=20, max_length=1000),
        observation_window=_observation_window(payload.get("observationWindow")),
        failure_conditions=_text_list(payload.get("failureConditions"), minimum=1, maximum=20, max_length=1000),
        rollback_conditions=_text_list(payload.get("rollbackConditions"), minimum=1, maximum=20, max_length=1000),
    )


def _text(value: Any, maximum: int) -> str:
    if not isinstance(value, str):
        raise GoalContractValidationError("GOAL_CONTRACT_INVALID_TEXT")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise GoalContractValidationError("GOAL_CONTRACT_INVALID_TEXT")
    return normalized


def _optional_text(value: Any, maximum: int) -> str | None:
    if value is None:
        return None
    return _text(value, maximum)


def _text_list(value: Any, *, minimum: int, maximum: int, max_length: int) -> tuple[str, ...]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise GoalContractValidationError("GOAL_CONTRACT_INVALID_CARDINALITY")
    return tuple(_text(item, max_length) for item in value)


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GoalContractValidationError(code)
    return value


def _enum(value: Any, allowed: frozenset[str], code: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise GoalContractValidationError(code)
    return value


def _affected_objects(value: Any) -> tuple[AffectedObject, ...]:
    if not isinstance(value, list) or not 1 <= len(value) <= 50:
        raise GoalContractValidationError("GOAL_CONTRACT_INVALID_CARDINALITY")
    objects: list[AffectedObject] = []
    for item in value:
        mapping = _mapping(item, "GOAL_CONTRACT_INVALID_TEXT")
        kind = _enum(mapping.get("kind"), OBJECT_KINDS, "GOAL_CONTRACT_INVALID_OBJECT_KIND")
        reference = _optional_text(mapping.get("reference"), 1000) or ""
        objects.append(AffectedObject(kind=kind, reference=reference, description=_text(mapping.get("description"), 2000)))
    return tuple(objects)


def _criteria(value: Any) -> tuple[Criterion, ...]:
    if not isinstance(value, list) or not 1 <= len(value) <= 20:
        raise GoalContractValidationError("GOAL_CONTRACT_INVALID_CARDINALITY")
    criteria: list[Criterion] = []
    for item in value:
        mapping = _mapping(item, "GOAL_CONTRACT_INVALID_TEXT")
        criteria.append(
            Criterion(
                name=_text(mapping.get("name"), 500),
                target=_text(mapping.get("target"), 1000),
                verification=_enum(mapping.get("verification"), VERIFICATION_METHODS, "GOAL_CONTRACT_INVALID_VERIFICATION"),
            )
        )
    return tuple(criteria)


def _observation_window(value: Any) -> ObservationWindow:
    mapping = _mapping(value, "GOAL_CONTRACT_INVALID_OBSERVATION_WINDOW")
    hours = mapping.get("durationHours")
    if isinstance(hours, bool) or not isinstance(hours, int) or not 0 <= hours <= 8760:
        raise GoalContractValidationError("GOAL_CONTRACT_INVALID_OBSERVATION_WINDOW")
    return ObservationWindow(duration_hours=hours)
