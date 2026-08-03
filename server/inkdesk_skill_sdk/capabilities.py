"""Portable Agent Skill metadata and Inkdesk capability manifests."""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from inkdesk_skill_sdk.contracts import Contract, SkillStatus


class PackageFormat(StrEnum):
    AGENT_SKILL = "agent-skill"
    CAPABILITY = "capability"
    LEGACY_CONTRACT = "legacy-contract"


class AgentSkillFrontmatter(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    description: str = Field(min_length=1, max_length=1024)
    license: str | None = None
    compatibility: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    allowed_tools: list[str] = Field(default_factory=list, alias="allowed-tools")

    @field_validator("allowed_tools", mode="before")
    @classmethod
    def normalize_allowed_tools(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item for item in value.split() if item]
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return value
        raise ValueError("allowed-tools must be a space-delimited string or list of strings")


class CapabilityPermissions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository: Literal["denied", "read-only", "workspace-write"] = "denied"
    vault: Literal["denied", "proposal-only"] = "denied"
    shell: Literal["denied", "allowlisted"] = "denied"
    network: Literal["denied", "allowed"] = "denied"
    external: Literal["denied", "approval-required"] = "denied"


class ExecutorPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed: list[Literal["claude", "codex"]] = Field(default_factory=list)
    default: Literal["claude", "codex"] | None = None
    requires: list[
        Literal["agent-loop", "tool-use", "streaming", "interrupt", "structured-output", "hooks"]
    ] = Field(default_factory=list)

    @model_validator(mode="after")
    def default_must_be_allowed(self) -> "ExecutorPolicy":
        if self.default is not None and self.default not in self.allowed:
            raise ValueError("executorPolicy.default must be included in executorPolicy.allowed")
        return self


class CapabilityGate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    kind: str = Field(min_length=1, max_length=64)
    params: dict[str, Any] = Field(default_factory=dict)


class EvidencePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lanes: list[str] = Field(default_factory=list)


class ArtifactPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1, max_length=64)
    path: str = Field(min_length=1, max_length=256)


class CapabilityManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: Literal["inkdesk.dev/v1alpha1"]
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    version: str = Field(min_length=1, max_length=32)
    status: SkillStatus = SkillStatus.DRAFT
    workflowRef: str = Field(min_length=1, max_length=128)
    inputSchema: dict[str, Any] = Field(default_factory=lambda: {"type": "object"})
    permissions: CapabilityPermissions = Field(default_factory=CapabilityPermissions)
    executorPolicy: ExecutorPolicy = Field(default_factory=ExecutorPolicy)
    gates: list[CapabilityGate] = Field(default_factory=list)
    evidence: EvidencePolicy = Field(default_factory=EvidencePolicy)
    artifacts: list[ArtifactPolicy] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SkillPackage:
    root: Path
    frontmatter: AgentSkillFrontmatter
    package_format: PackageFormat
    executable: bool
    capability: CapabilityManifest | None = None
    legacy_contract: Contract | None = None


def parse_skill_frontmatter(skill_path: Path) -> AgentSkillFrontmatter:
    text = skill_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    normalized = text.replace("\r\n", "\n")
    end = normalized.find("\n---\n", 3)
    if end < 0:
        raise ValueError("SKILL.md frontmatter is not terminated")
    raw = yaml.safe_load(normalized[4:end])
    if not isinstance(raw, dict):
        raise ValueError("SKILL.md frontmatter must be a YAML mapping")
    return AgentSkillFrontmatter.model_validate(raw)


def load_skill_package(package_root: Path, *, warn_legacy: bool = True) -> SkillPackage:
    root = Path(package_root).resolve()
    frontmatter = parse_skill_frontmatter(root / "SKILL.md")
    capability_path = root / "inkdesk.yaml"
    contract_path = root / "contract.json"

    if capability_path.is_file() and contract_path.is_file():
        raise ValueError("Skill package cannot contain both inkdesk.yaml and contract.json")

    if capability_path.is_file():
        raw = yaml.safe_load(capability_path.read_text(encoding="utf-8"))
        capability = CapabilityManifest.model_validate(raw)
        _validate_identity(root, frontmatter, capability.id)
        return SkillPackage(root, frontmatter, PackageFormat.CAPABILITY, True, capability=capability)

    if contract_path.is_file():
        contract = Contract.model_validate(json.loads(contract_path.read_text(encoding="utf-8")))
        _validate_identity(root, frontmatter, contract.id)
        if warn_legacy:
            warnings.warn(
                f"{contract_path} uses deprecated contract.json; migrate to inkdesk.yaml",
                DeprecationWarning,
                stacklevel=2,
            )
        capability = _legacy_capability(contract)
        return SkillPackage(
            root,
            frontmatter,
            PackageFormat.LEGACY_CONTRACT,
            True,
            capability=capability,
            legacy_contract=contract,
        )

    _validate_identity(root, frontmatter, frontmatter.name)
    return SkillPackage(root, frontmatter, PackageFormat.AGENT_SKILL, False)


def _validate_identity(root: Path, frontmatter: AgentSkillFrontmatter, manifest_id: str) -> None:
    if root.name != manifest_id or frontmatter.name != manifest_id:
        raise ValueError(
            f"Skill identity mismatch: directory={root.name!r}, SKILL.md={frontmatter.name!r}, manifest={manifest_id!r}"
        )


def _legacy_capability(contract: Contract) -> CapabilityManifest:
    properties = {
        item.name: {"type": item.type, "description": item.constraints}
        for item in contract.inputs
    }
    required = [item.name for item in contract.inputs if item.required]
    return CapabilityManifest(
        schemaVersion="inkdesk.dev/v1alpha1",
        id=contract.id,
        version=contract.version,
        status=contract.status,
        workflowRef=f"legacy:{contract.id}",
        inputSchema={"type": "object", "properties": properties, "required": required},
        permissions=CapabilityPermissions(
            repository="denied",
            vault=contract.writePolicy.canonicalWiki.value,
        ),
        executorPolicy=ExecutorPolicy(),
        gates=[CapabilityGate(id=gate.id, kind=gate.kind.value, params=gate.params) for gate in contract.hardGates],
        evidence=EvidencePolicy(lanes=[item.name for item in contract.contextRequirements]),
        artifacts=[ArtifactPolicy(kind=item.type, path=item.location) for item in contract.outputs],
    )
