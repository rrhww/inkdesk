"""
Structural, semantic, and safety validation for Skill packages.

Returns stable findings with code/path/message/severity.
Does not modify packages — read-only.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import yaml

from inkdesk_skill_sdk.contracts import (
    AGENTS_REQUIRED_FILES,
    ALLOWED_OPTIONAL_DIRS,
    DIR_NAME_MAX_LEN,
    DIR_NAME_RE,
    REQUIRED_DIRS,
    REQUIRED_FILES,
    CanonicalWikiPolicy,
    Contract,
    OpenAIAgentYaml,
)
from inkdesk_skill_sdk.capabilities import CapabilityManifest, parse_skill_frontmatter

PACKAGE_NAME_RE = re.compile(DIR_NAME_RE)


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Finding:
    code: str
    path: str
    message: str
    severity: Severity


@dataclass(frozen=True, slots=True)
class ValidationResult:
    package_name: str
    findings: tuple[Finding, ...]
    passed: bool

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == Severity.WARNING]


# ——— helpers ———


def _read_text(package_root: Path, rel: str) -> str | None:
    fpath = package_root / rel
    if not fpath.is_file():
        return None
    return fpath.read_text(encoding="utf-8")


def _make_abs_path_finder() -> re.Pattern[str]:
    """Build a regex matching Windows and Unix absolute paths.

    Catches patterns like:
      C:\\Users\\..., D:/projects/..., /home/user/..., ~/something
    """
    return re.compile(
        r"(?:[A-Za-z]:[\\/])"    # Windows drive letter
        r"|(?:^/[a-zA-Z])"       # Unix absolute
        r"|(?:^~[/\\])"          # home-relative absolute
        r"|(?:%[A-Za-z_][A-Za-z0-9_]*%)"  # env var like %APPDATA%
        r"|(?:\\\\)"             # UNC
    )


_ABS_PATH_RE = _make_abs_path_finder()

_BYPASS_PATTERNS = [
    re.compile(r"绕过.*review", re.IGNORECASE),
    re.compile(r"bypass.*review", re.IGNORECASE),
    re.compile(r"skip.*review", re.IGNORECASE),
    re.compile(r"without.*review", re.IGNORECASE),
    re.compile(r"直接写.*wiki", re.IGNORECASE),
    re.compile(r"direct.*write.*wiki", re.IGNORECASE),
    re.compile(r"绕过.*schema", re.IGNORECASE),
    re.compile(r"bypass.*schema", re.IGNORECASE),
    re.compile(r"绕过.*确认", re.IGNORECASE),
    re.compile(r"bypass.*confirm", re.IGNORECASE),
]

_SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),          # OpenAI-style
    re.compile(r"ghp_[a-zA-Z0-9]{20,}"),          # GitHub classic
    re.compile(r"github_pat_[a-zA-Z0-9_]{20,}"),  # GitHub fine-grained
    re.compile(r"(?:api[_-]?key\s*[:=]\s*)(?!\s*<)([^\s]{8,})", re.IGNORECASE),
]


def _check_abs_paths(text: str, path_in_pkg: str) -> list[Finding]:
    findings: list[Finding] = []
    for m in _ABS_PATH_RE.finditer(text):
        findings.append(
            Finding(
                code="SAFETY_ABSOLUTE_PATH",
                path=path_in_pkg,
                message=f"Absolute path detected: {m.group()!r}",
                severity=Severity.ERROR,
            )
        )
    return findings


_NEGATION_PREFIX = re.compile(
    r"(?:\*\*)?(?:不做|不[得应能可允许]|禁止|严禁|不应|不可|不能)(?:\*\*)?\s*[：:\-—]",
    re.IGNORECASE,
)

_IMMEDIATE_NEGATION = re.compile(r"(?:不|not?)\s*$", re.IGNORECASE)


def _check_bypass(text: str, path_in_pkg: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()
    for lineno, line in enumerate(lines, 1):
        for pat in _BYPASS_PATTERNS:
            m = pat.search(line)
            if not m:
                continue
            before = line[: m.start()]
            if _NEGATION_PREFIX.search(before):
                continue
            if _IMMEDIATE_NEGATION.search(before):
                continue
            findings.append(
                Finding(
                    code="SAFETY_BYPASS_CLAIM",
                    path=f"{path_in_pkg}:{lineno}",
                    message=f"Claims to bypass review/schema/confirmation: matched {pat.pattern!r}",
                    severity=Severity.ERROR,
                )
            )
    return findings


def _check_secrets(text: str, path_in_pkg: str) -> list[Finding]:
    findings: list[Finding] = []
    for pat in _SECRET_PATTERNS:
        m = pat.search(text)
        if m:
            findings.append(
                Finding(
                    code="SAFETY_SECRET_PATTERN",
                    path=path_in_pkg,
                    message=f"Potential secret pattern detected: {m.group()!r}",
                    severity=Severity.ERROR,
                )
            )
    return findings


def _is_duplicate_text(a: str, b: str) -> bool:
    """Check if `b` is essentially a duplicate/substring of `a`."""
    a_norm = a.strip().lower()
    b_norm = b.strip().lower()
    if not a_norm or not b_norm:
        return False
    return a_norm == b_norm or b_norm in a_norm or a_norm in b_norm


# ——— structural ———


def validate_structural(package_root: Path) -> list[Finding]:
    """Validate directory name, required files, and allowed directories."""
    findings: list[Finding] = []

    dir_name = package_root.name

    # Directory name
    if not PACKAGE_NAME_RE.fullmatch(dir_name):
        findings.append(
            Finding(
                code="STRUCT_DIR_NAME",
                path=str(package_root),
                message=f"Package directory name {dir_name!r} must match {DIR_NAME_RE}",
                severity=Severity.ERROR,
            )
        )
    if len(dir_name) > DIR_NAME_MAX_LEN:
        findings.append(
            Finding(
                code="STRUCT_DIR_NAME_LEN",
                path=str(package_root),
                message=f"Package directory name {dir_name!r} exceeds {DIR_NAME_MAX_LEN} chars",
                severity=Severity.ERROR,
            )
        )

    # Agent Skills require only SKILL.md.
    for req_file in REQUIRED_FILES:
        if not (package_root / req_file).is_file():
            findings.append(
                Finding(
                    code="STRUCT_MISSING_FILE",
                    path=f"{dir_name}/{req_file}",
                    message=f"Required file {req_file!r} is missing",
                    severity=Severity.ERROR,
                )
            )

    # Required directories
    for req_dir in REQUIRED_DIRS:
        if not (package_root / req_dir).is_dir():
            findings.append(
                Finding(
                    code="STRUCT_MISSING_DIR",
                    path=f"{dir_name}/{req_dir}",
                    message=f"Required directory {req_dir!r} is missing",
                    severity=Severity.ERROR,
                )
            )

    if (package_root / "inkdesk.yaml").is_file() and (package_root / "contract.json").is_file():
        findings.append(
            Finding(
                code="STRUCT_MULTIPLE_MANIFESTS",
                path=dir_name,
                message="Skill package cannot contain both inkdesk.yaml and contract.json",
                severity=Severity.ERROR,
            )
        )

    # Only allowed optional directories
    if package_root.is_dir():
        for item in package_root.iterdir():
            if item.is_dir() and item.name not in REQUIRED_DIRS and item.name not in ALLOWED_OPTIONAL_DIRS:
                if not item.name.startswith("."):
                    findings.append(
                        Finding(
                            code="STRUCT_UNKNOWN_DIR",
                            path=f"{dir_name}/{item.name}",
                            message=f"Unknown directory {item.name!r}; allowed: {ALLOWED_OPTIONAL_DIRS}",
                            severity=Severity.WARNING,
                        )
                    )

    return findings


# ——— semantic ———


def validate_semantic(package_root: Path) -> list[Finding]:
    """Validate cross-file consistency: name/id/frontmatter/contract/openai alignment."""
    findings: list[Finding] = []
    dir_name = package_root.name

    # --- Parse SKILL.md frontmatter ---
    skill_md = _read_text(package_root, "SKILL.md")
    skill_frontmatter_name: str | None = None
    skill_frontmatter_desc: str | None = None
    skill_extra_frontmatter: list[str] = []
    skill_body: str = ""

    if skill_md is not None:
        fm = _parse_frontmatter(skill_md)
        if fm is None:
            findings.append(
                Finding(
                    code="SEMANTIC_SKILL_NO_FRONTMATTER",
                    path=f"{dir_name}/SKILL.md",
                    message="SKILL.md has no parsable YAML frontmatter",
                    severity=Severity.ERROR,
                )
            )
        else:
            skill_frontmatter_name = fm.get("name")
            skill_frontmatter_desc = fm.get("description")
            extra = [
                k
                for k in fm
                if k not in ("name", "description", "license", "compatibility", "metadata", "allowed-tools")
            ]
            if extra:
                skill_extra_frontmatter = extra
                findings.append(
                    Finding(
                        code="SEMANTIC_EXTRA_FRONTMATTER",
                        path=f"{dir_name}/SKILL.md",
                        message=f"Unsupported Agent Skills frontmatter fields: {extra}",
                        severity=Severity.ERROR,
                    )
                )
            if skill_frontmatter_name is None:
                findings.append(
                    Finding(
                        code="SEMANTIC_MISSING_NAME",
                        path=f"{dir_name}/SKILL.md",
                        message="SKILL.md frontmatter is missing required 'name' field",
                        severity=Severity.ERROR,
                    )
                )
            if skill_frontmatter_desc is None:
                findings.append(
                    Finding(
                        code="SEMANTIC_MISSING_DESC",
                        path=f"{dir_name}/SKILL.md",
                        message="SKILL.md frontmatter is missing required 'description' field",
                        severity=Severity.ERROR,
                    )
                )
        # body starts after frontmatter
        parts = _split_frontmatter(skill_md)
        if parts is not None:
            skill_body = parts[1]

    # --- Parse execution manifest (new capability or legacy contract) ---
    capability_raw = _read_text(package_root, "inkdesk.yaml")
    capability: CapabilityManifest | None = None
    if capability_raw is not None:
        try:
            capability = CapabilityManifest.model_validate(yaml.safe_load(capability_raw))
        except Exception as e:
            findings.append(
                Finding(
                    code="SEMANTIC_CAPABILITY_PARSE",
                    path=f"{dir_name}/inkdesk.yaml",
                    message=f"Capability validation failed: {e}",
                    severity=Severity.ERROR,
                )
            )

    contract_raw = _read_text(package_root, "contract.json")
    contract: Contract | None = None
    contract_parse_error: str | None = None

    if contract_raw is not None:
        try:
            data = json.loads(contract_raw)
            contract = Contract.model_validate(data)
        except json.JSONDecodeError as e:
            contract_parse_error = f"Invalid JSON: {e}"
            findings.append(
                Finding(
                    code="SEMANTIC_CONTRACT_JSON",
                    path=f"{dir_name}/contract.json",
                    message=contract_parse_error,
                    severity=Severity.ERROR,
                )
            )
        except Exception as e:
            contract_parse_error = str(e)
            findings.append(
                Finding(
                    code="SEMANTIC_CONTRACT_PARSE",
                    path=f"{dir_name}/contract.json",
                    message=f"Contract validation failed: {contract_parse_error}",
                    severity=Severity.ERROR,
                )
            )

    # --- Parse agents/openai.yaml ---
    openai_raw = _read_text(package_root, "agents/openai.yaml")
    openai_yaml: OpenAIAgentYaml | None = None
    openai_error: str | None = None

    if openai_raw is not None:
        try:
            parsed = yaml.safe_load(openai_raw)
            openai_yaml = OpenAIAgentYaml.model_validate(parsed)
        except Exception as e:
            openai_error = str(e)
            findings.append(
                Finding(
                    code="SEMANTIC_OPENAI_YAML",
                    path=f"{dir_name}/agents/openai.yaml",
                    message=f"openai.yaml validation failed: {openai_error}",
                    severity=Severity.ERROR,
                )
            )

    if contract is None and capability is None:
        return findings

    # --- Three-way name consistency ---
    names: dict[str, str] = {}
    names["dir"] = dir_name
    if contract is not None:
        names["contract.id"] = contract.id
    elif capability is not None:
        names["inkdesk.yaml id"] = capability.id
    if skill_frontmatter_name:
        names["SKILL.md name"] = skill_frontmatter_name

    canonical = contract.id if contract is not None else capability.id
    for src, val in names.items():
        if val != canonical:
            findings.append(
                Finding(
                    code="SEMANTIC_NAME_MISMATCH",
                    path=(
                        f"{dir_name}/SKILL.md"
                        if "SKILL" in src
                        else f"{dir_name}/contract.json" if contract is not None else f"{dir_name}/inkdesk.yaml"
                    ),
                    message=f"Name mismatch: {src}={val!r} != manifest id={canonical!r}",
                    severity=Severity.ERROR,
                )
            )

    # --- Version: valid SemVer ---
    version = contract.version if contract is not None else capability.version
    if not _is_semver(version):
        findings.append(
            Finding(
                code="SEMANTIC_BAD_SEMVER",
                path=f"{dir_name}/contract.json" if contract is not None else f"{dir_name}/inkdesk.yaml",
                message=f"Invalid SemVer version: {version!r}",
                severity=Severity.ERROR,
            )
        )

    # --- Description quality ---
    if skill_frontmatter_desc:
        summary = contract.summary if contract is not None else skill_frontmatter_desc
        if _is_duplicate_text(skill_frontmatter_desc, summary):
            pass  # description and summary can naturally overlap
        if _is_duplicate_text(skill_frontmatter_name or "", skill_frontmatter_desc):
            findings.append(
                Finding(
                    code="SEMANTIC_DESC_DUPLICATE",
                    path=f"{dir_name}/SKILL.md",
                    message="description duplicates name — should describe trigger/non-trigger boundaries",
                    severity=Severity.WARNING,
                )
            )

    if contract is None:
        return findings

    # --- inputs referenced in hardGates ---
    input_names = {i.name for i in contract.inputs}
    for g in contract.hardGates:
        if g.kind.value == "required_input":
            field = g.params.get("field", "")
            if field and field not in input_names:
                findings.append(
                    Finding(
                        code="SEMANTIC_GATE_INPUT_MISMATCH",
                        path=f"{dir_name}/contract.json",
                        message=f"HardGate {g.id!r} references input {field!r} not declared in inputs",
                        severity=Severity.ERROR,
                    )
                )

    # --- outputs / writePolicy consistency ---
    for o in contract.outputs:
        if o.needsReview and contract.writePolicy.canonicalWiki == CanonicalWikiPolicy.PROPOSAL_ONLY:
            pass  # consistent
        # If outputs don't need review but wiki is proposal-only, that's fine — review happens upstream.

    # --- nextSkills existence (placeholder — checked by graph) ---
    seen_ids: set[str] = set()
    for ref in contract.nextSkills:
        if ref.skillId == contract.id:
            findings.append(
                Finding(
                    code="SEMANTIC_NEXT_SELF_REF",
                    path=f"{dir_name}/contract.json",
                    message=f"nextSkills self-reference: {ref.skillId!r}",
                    severity=Severity.ERROR,
                )
            )
        if ref.skillId in seen_ids:
            findings.append(
                Finding(
                    code="SEMANTIC_NEXT_DUPLICATE",
                    path=f"{dir_name}/contract.json",
                    message=f"Duplicate nextSkills entry: {ref.skillId!r}",
                    severity=Severity.WARNING,
                )
            )
        seen_ids.add(ref.skillId)

    # --- SKILL.md body checks ---
    if skill_body:
        # Don't reference absolute paths in body
        findings.extend(_check_abs_paths(skill_body, f"{dir_name}/SKILL.md"))
        findings.extend(_check_bypass(skill_body, f"{dir_name}/SKILL.md"))

    # --- openai.yaml consistency ---
    if openai_yaml and contract:
        # display_name should be related to contract.id (human-readable form)
        slug_from_display = _slugify(openai_yaml.interface.display_name)
        if slug_from_display != contract.id and openai_yaml.interface.display_name.lower() != contract.id:
            findings.append(
                Finding(
                    code="SEMANTIC_OPENAI_NAME_MISMATCH",
                    path=f"{dir_name}/agents/openai.yaml",
                    message=f"display_name {openai_yaml.interface.display_name!r} inconsistent with contract.id {contract.id!r}",
                    severity=Severity.ERROR,
                )
            )

    return findings


# ——— safety ———


def validate_safety(package_root: Path) -> list[Finding]:
    """Validate write policies, path safety, secrets, and bypass claims."""
    findings: list[Finding] = []
    dir_name = package_root.name

    # --- contract.json safety ---
    contract_raw = _read_text(package_root, "contract.json")
    contract: Contract | None = None
    if contract_raw:
        # Catch "direct" write policy even if Pydantic parse fails
        try:
            raw_data = json.loads(contract_raw)
            wp = raw_data.get("writePolicy", {})
            cw = wp.get("canonicalWiki", "")
            if cw not in ("denied", "proposal-only", ""):
                findings.append(
                    Finding(
                        code="SAFETY_WRITE_POLICY",
                        path=f"{dir_name}/contract.json",
                        message=f"canonicalWiki is {cw!r}; must be denied or proposal-only",
                        severity=Severity.ERROR,
                    )
                )
        except json.JSONDecodeError:
            pass

        try:
            contract = Contract.model_validate(raw_data)
        except Exception:
            pass  # already reported by semantic validator

    if contract is not None:
        # canonicalWiki must be denied or proposal-only
        if contract.writePolicy.canonicalWiki not in (
            CanonicalWikiPolicy.DENIED,
            CanonicalWikiPolicy.PROPOSAL_ONLY,
        ):
            findings.append(
                Finding(
                    code="SAFETY_WRITE_POLICY",
                    path=f"{dir_name}/contract.json",
                    message=f"canonicalWiki is {contract.writePolicy.canonicalWiki.value!r}; must be denied or proposal-only",
                    severity=Severity.ERROR,
                )
            )

        # No script capabilities can claim to bypass gates
        for cap in contract.capabilities:
            if "bypass" in cap.lower() or "sudo" in cap.lower() or "admin" in cap.lower():
                findings.append(
                    Finding(
                        code="SAFETY_SUSPICIOUS_CAPABILITY",
                        path=f"{dir_name}/contract.json",
                        message=f"Suspicious capability: {cap!r}",
                        severity=Severity.ERROR,
                    )
                )

        # Scripts cannot reference undeclared capabilities
        declared = set(contract.capabilities)
        for g in contract.hardGates:
            if g.kind.value == "required_input":
                ref = g.params.get("field", "")
            else:
                ref = ""
            if ref and ref not in {i.name for i in contract.inputs}:
                pass  # already caught by semantic

    # --- Scan all text files for safety issues ---
    for fpath in package_root.rglob("*"):
        if fpath.is_dir():
            continue
        if fpath.suffix in (".pyc", ".db", ".sqlite"):
            continue
        rel = str(fpath.relative_to(package_root))
        try:
            text = fpath.read_text(encoding="utf-8")
        except Exception:
            continue

        findings.extend(_check_abs_paths(text, rel))
        findings.extend(_check_bypass(text, rel))
        findings.extend(_check_secrets(text, rel))

        # Path escape: references that go outside package root
        for line_no, line in enumerate(text.splitlines(), 1):
            if "../" in line and not line.strip().startswith("#"):
                # ignore '..' in natural language (like "..and then")
                if re.search(r"(?:file|path|read|load|import|include|require|source|open)\s*[=:]\s*", line):
                    findings.append(
                        Finding(
                            code="SAFETY_PATH_ESCAPE",
                            path=f"{dir_name}/{rel}:{line_no}",
                            message=f"Possible path escape: {line.strip()!r}",
                            severity=Severity.ERROR,
                        )
                    )

    return findings


# ——— frontmatter parsing ———


def _split_frontmatter(text: str) -> tuple[dict[str, object], str] | None:
    """Split SKILL.md into (frontmatter_dict, body) or None if no frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return None
    fm_text = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1:])
    try:
        fm = yaml.safe_load(fm_text)
    except yaml.YAMLError:
        return None
    if not isinstance(fm, dict):
        return None
    return {str(k): v for k, v in fm.items()}, body


def _parse_frontmatter(text: str) -> dict[str, object] | None:
    """Parse frontmatter from a SKILL.md text; returns dict or None."""
    parts = _split_frontmatter(text)
    if parts is None:
        return None
    return parts[0]


_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$")


def _is_semver(v: str) -> bool:
    return bool(_SEMVER_RE.fullmatch(v))


def _slugify(s: str) -> str:
    """Convert a human-readable name to a slug: 'Minimal Producer' -> 'minimal-producer'."""
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
