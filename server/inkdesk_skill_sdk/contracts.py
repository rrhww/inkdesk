"""
Inkdesk Skill contract models — the single source of truth for contract.json schema.

All enums, Pydantic models, and JSON Schema generation live here.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator


class SchemaVersion(StrEnum):
    V1_0 = "1.0"


class SkillStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class SkillCategory(StrEnum):
    KNOWLEDGE = "knowledge"
    ENGINEERING = "engineering"
    ROUTING = "routing"
    DISCIPLINE = "discipline"


class SkillKind(StrEnum):
    PRODUCER = "producer"
    REVIEWER = "reviewer"
    ROUTER = "router"
    DIAGNOSTIC = "diagnostic"


class CanonicalWikiPolicy(StrEnum):
    DENIED = "denied"
    PROPOSAL_ONLY = "proposal-only"


class ArtifactPolicy(StrEnum):
    DENIED = "denied"
    ALLOWED = "allowed"


class CodeRepoPolicy(StrEnum):
    DENIED = "denied"
    DELEGATED = "delegated"


class GateKind(StrEnum):
    REQUIRED_INPUT = "required_input"
    VAULT_INITIALIZED = "vault_initialized"
    SCHEMA_GATE_PASSED = "schema_gate_passed"
    DEV_RUN_EXISTS = "dev_run_exists"
    RUN_STAGE_IS = "run_stage_is"
    REVIEW_APPROVED = "review_approved"
    ARTIFACT_EXISTS = "artifact_exists"
    REAL_FAILURE_SIGNAL = "real_failure_signal_present"
    HUMAN_CONFIRMATION = "human_confirmation"


class HardGate(BaseModel):
    id: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    kind: GateKind
    params: dict[str, str] = Field(default_factory=dict)
    on_failure: Annotated[str, StringConstraints(min_length=1, max_length=256)]


class SkillInput(BaseModel):
    name: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    type: Annotated[str, StringConstraints(min_length=1, max_length=32)] = "string"
    required: bool = False
    constraints: Annotated[str, StringConstraints(max_length=256)] = ""


class ContextRequirement(BaseModel):
    name: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    description: Annotated[str, StringConstraints(max_length=256)] = ""


class SkillOutput(BaseModel):
    type: Annotated[str, StringConstraints(min_length=1, max_length=32)]
    location: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    needsReview: bool = True


class WritePolicy(BaseModel):
    canonicalWiki: CanonicalWikiPolicy = CanonicalWikiPolicy.PROPOSAL_ONLY
    runArtifacts: ArtifactPolicy = ArtifactPolicy.ALLOWED
    codeRepository: CodeRepoPolicy = CodeRepoPolicy.DENIED

    @model_validator(mode="after")
    def canonical_wiki_never_direct(self) -> "WritePolicy":
        if self.canonicalWiki not in (CanonicalWikiPolicy.DENIED, CanonicalWikiPolicy.PROPOSAL_ONLY):
            raise ValueError(f"canonicalWiki must be denied or proposal-only, got {self.canonicalWiki}")
        return self


class VerificationRequirement(BaseModel):
    kind: Annotated[str, StringConstraints(min_length=1, max_length=32)]
    description: Annotated[str, StringConstraints(max_length=256)] = ""


class NextSkillRef(BaseModel):
    skillId: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    entryCondition: Annotated[str, StringConstraints(max_length=256)] = ""


class Contract(BaseModel):
    """Full contract.json model — single source of truth."""

    schemaVersion: Literal["1.0"] = "1.0"
    id: Annotated[str, StringConstraints(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")]
    version: Annotated[str, StringConstraints(min_length=1, max_length=32)] = "0.1.0"
    status: SkillStatus = SkillStatus.DRAFT
    category: SkillCategory
    kind: SkillKind

    summary: Annotated[str, StringConstraints(min_length=1, max_length=256)]

    inputs: list[SkillInput] = Field(default_factory=list, max_length=16)
    contextRequirements: list[ContextRequirement] = Field(default_factory=list, max_length=32)
    outputs: list[SkillOutput] = Field(default_factory=list, max_length=16)

    hardGates: list[HardGate] = Field(default_factory=list, max_length=16)
    capabilities: Annotated[list[str], Field(default_factory=list, max_length=32)]

    writePolicy: WritePolicy = Field(default_factory=WritePolicy)

    verification: list[VerificationRequirement] = Field(default_factory=list, max_length=16)
    nextSkills: list[NextSkillRef] = Field(default_factory=list, max_length=16)
    supportedRuntimes: Annotated[list[str], Field(default_factory=list, max_length=16)] = Field(
        default_factory=lambda: ["inkdesk"]
    )

    @model_validator(mode="after")
    def next_skills_no_self_ref(self) -> "Contract":
        for ref in self.nextSkills:
            if ref.skillId == self.id:
                raise ValueError(f"nextSkills must not reference self: {ref.skillId}")
        return self


# ———— YAML models ————


class OpenAIAgentInterface(BaseModel):
    display_name: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    short_description: Annotated[str, StringConstraints(min_length=1, max_length=256)]
    default_prompt: Annotated[str, StringConstraints(min_length=1, max_length=1024)]


class OpenAIAgentPolicy(BaseModel):
    allow_implicit_invocation: bool = False


class OpenAIAgentYaml(BaseModel):
    interface: OpenAIAgentInterface
    policy: OpenAIAgentPolicy = Field(default_factory=OpenAIAgentPolicy)


# ———— JSON Schema export ————


def generate_contract_json_schema() -> dict[str, Any]:
    """Generate a stable JSON Schema for contract.json from the Pydantic model."""
    schema = Contract.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "Inkdesk Skill Contract"
    return schema


# ———— Well-known constants ————


DIR_NAME_RE = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$"
DIR_NAME_MAX_LEN = 63

REQUIRED_FILES = ["SKILL.md", "contract.json"]
REQUIRED_DIRS = ["agents"]
ALLOWED_OPTIONAL_DIRS = ["references", "prompts", "templates", "scripts", "assets"]
AGENTS_REQUIRED_FILES = ["openai.yaml"]
