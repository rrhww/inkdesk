from __future__ import annotations

import json
from pathlib import Path

import pytest

from inkdesk_skill_sdk.capabilities import PackageFormat, load_skill_package
from inkdesk_skill_sdk.registry import SkillRegistry
from inkdesk_skill_sdk.validation import Severity, validate_semantic, validate_structural


def write_skill(root: Path, frontmatter: str) -> Path:
    root.mkdir()
    (root / "SKILL.md").write_text(
        f"---\n{frontmatter}\n---\n\n# {root.name}\n",
        encoding="utf-8",
    )
    return root


def test_portable_agent_skill_needs_only_skill_md(tmp_path: Path) -> None:
    package = write_skill(
        tmp_path / "portable-review",
        """name: portable-review
description: Review a repository without changing it.
license: MIT
compatibility: Requires Git.
metadata:
  owner: inkdesk
allowed-tools: Read Grep Glob""",
    )

    findings = validate_structural(package) + validate_semantic(package)
    assert not [finding for finding in findings if finding.severity == Severity.ERROR]

    resolved = SkillRegistry([tmp_path]).resolve(package)
    assert resolved is not None
    assert resolved.package_format == PackageFormat.AGENT_SKILL
    assert resolved.executable is False
    assert resolved.summary == "Review a repository without changing it."


def test_inkdesk_manifest_makes_skill_executable(tmp_path: Path) -> None:
    package = write_skill(
        tmp_path / "harness-audit",
        "name: harness-audit\ndescription: Audit the coding-agent harness from bounded evidence.",
    )
    (package / "inkdesk.yaml").write_text(
        """schemaVersion: inkdesk.dev/v1alpha1
id: harness-audit
version: 0.2.0
status: active
workflowRef: harness-audit-v1
inputSchema:
  type: object
permissions:
  repository: read-only
  vault: proposal-only
  shell: allowlisted
  network: denied
  external: denied
executorPolicy:
  allowed: [claude, codex]
  default: claude
gates:
  - id: repository-exists
    kind: repository_exists
evidence:
  lanes: [projectHarness, agentCustomize, deliveryEvidence, lead]
artifacts:
  - kind: findings
    path: .inkdesk/runs/{runId}/findings.json
""",
        encoding="utf-8",
    )

    loaded = load_skill_package(package)
    assert loaded.package_format == PackageFormat.CAPABILITY
    assert loaded.executable is True
    assert loaded.capability is not None
    assert loaded.capability.permissions.repository == "read-only"
    assert loaded.capability.executorPolicy.default == "claude"


def test_legacy_contract_is_loaded_with_deprecation_warning(tmp_path: Path) -> None:
    package = write_skill(
        tmp_path / "legacy-skill",
        "name: legacy-skill\ndescription: A legacy Inkdesk skill.",
    )
    (package / "contract.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "id": "legacy-skill",
                "version": "0.1.0",
                "status": "active",
                "category": "engineering",
                "kind": "reviewer",
                "summary": "A legacy Inkdesk skill.",
            }
        ),
        encoding="utf-8",
    )

    with pytest.warns(DeprecationWarning, match="contract.json"):
        loaded = load_skill_package(package)

    assert loaded.package_format == PackageFormat.LEGACY_CONTRACT
    assert loaded.executable is True
    assert loaded.capability is not None
    assert loaded.capability.workflowRef == "legacy:legacy-skill"


def test_package_rejects_two_execution_manifests(tmp_path: Path) -> None:
    package = write_skill(
        tmp_path / "ambiguous",
        "name: ambiguous\ndescription: Invalid dual-manifest package.",
    )
    (package / "inkdesk.yaml").write_text("id: ambiguous\n", encoding="utf-8")
    (package / "contract.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="both inkdesk.yaml and contract.json"):
        load_skill_package(package)
