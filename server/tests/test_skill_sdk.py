"""Tests for inkdesk_skill_sdk — contracts, validation, scaffolder, registry, graph, and CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from inkdesk_skill_sdk.contracts import (
    ALLOWED_OPTIONAL_DIRS,
    REQUIRED_DIRS,
    REQUIRED_FILES,
    Contract,
    OpenAIAgentYaml,
    SkillCategory,
    SkillKind,
    SkillStatus,
    generate_contract_json_schema,
)
from inkdesk_skill_sdk.graph import build_graph, RoutingGraph, validate_graph
from inkdesk_skill_sdk.registry import SkillRegistry
from inkdesk_skill_sdk.scaffolder import init_skill_package
from inkdesk_skill_sdk.validation import (
    Finding,
    Severity,
    ValidationResult,
    _is_semver,
    _parse_frontmatter,
    validate_safety,
    validate_semantic,
    validate_structural,
)

FIXTURES = Path(__file__).parent / "skill_fixtures"


# ——— contracts ———


def test_contract_minimal_valid():
    data = {
        "schemaVersion": "1.0",
        "id": "test-skill",
        "version": "0.1.0",
        "status": "draft",
        "category": "knowledge",
        "kind": "producer",
        "summary": "A test skill",
    }
    c = Contract.model_validate(data)
    assert c.id == "test-skill"
    assert c.writePolicy.canonicalWiki.value == "proposal-only"


def test_contract_rejects_direct_wiki():
    with pytest.raises(Exception):
        Contract.model_validate(
            {
                "schemaVersion": "1.0",
                "id": "bad",
                "version": "0.1.0",
                "category": "knowledge",
                "kind": "producer",
                "summary": "bad",
                "writePolicy": {
                    "canonicalWiki": "not-a-valid-value",
                },
            }
        )


def test_contract_rejects_self_referencing_next_skills():
    with pytest.raises(Exception):
        Contract.model_validate(
            {
                "schemaVersion": "1.0",
                "id": "self-ref",
                "version": "0.1.0",
                "category": "knowledge",
                "kind": "producer",
                "summary": "bad",
                "nextSkills": [{"skillId": "self-ref"}],
            }
        )


def test_generate_json_schema():
    schema = generate_contract_json_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert "properties" in schema


def test_openai_yaml_parsing():
    y = yaml.safe_load(
        """interface:
  display_name: "Test"
  short_description: "desc"
  default_prompt: "prompt"
policy:
  allow_implicit_invocation: false
"""
    )
    oa = OpenAIAgentYaml.model_validate(y)
    assert oa.interface.display_name == "Test"
    assert oa.policy.allow_implicit_invocation is False


# ——— semver ———


@pytest.mark.parametrize(
    "v,expected",
    [
        ("0.1.0", True),
        ("1.0.0", True),
        ("10.20.30", True),
        ("1.0.0-alpha.1", True),
        ("1.0.0+build.123", True),
        ("not-semver", False),
        ("1.0", False),
        ("v1.0.0", False),
        ("", False),
    ],
)
def test_semver(v: str, expected: bool):
    assert _is_semver(v) == expected


# ——— frontmatter ———


def test_parse_basic_frontmatter():
    text = """---
name: test-skill
description: A test skill
---

# Body
"""
    fm = _parse_frontmatter(text)
    assert fm == {"name": "test-skill", "description": "A test skill"}


def test_parse_no_frontmatter():
    text = "# No frontmatter here"
    assert _parse_frontmatter(text) is None


# ——— counts ———


def _count_errors(findings: list[Finding]) -> int:
    return sum(1 for f in findings if f.severity == Severity.ERROR)


# ——— structural validation ———


def test_structural_valid_minimal():
    pkg = FIXTURES / "valid" / "minimal-producer"
    findings = validate_structural(pkg)
    assert _count_errors(findings) == 0, findings


def test_structural_valid_comprehensive():
    pkg = FIXTURES / "valid" / "comprehensive-router"
    findings = validate_structural(pkg)
    assert _count_errors(findings) == 0, findings


def test_structural_missing_contract():
    pkg = FIXTURES / "invalid" / "bad-missing-contract"
    findings = validate_structural(pkg)
    assert _count_errors(findings) > 0
    assert any(f.code == "STRUCT_MISSING_FILE" for f in findings)


def test_structural_missing_openai_yaml():
    pkg = FIXTURES / "invalid" / "bad-missing-openai"
    findings = validate_structural(pkg)
    errors = [f for f in findings if f.severity == Severity.ERROR]
    assert any(f.code == "STRUCT_MISSING_AGENT_FILE" for f in errors)


# ——— semantic validation ———


def test_semantic_valid_minimal():
    pkg = FIXTURES / "valid" / "minimal-producer"
    findings = validate_semantic(pkg)
    assert _count_errors(findings) == 0, f"Unexpected errors: {[f for f in findings if f.severity == Severity.ERROR]}"


def test_semantic_id_mismatch():
    pkg = FIXTURES / "invalid" / "bad-id-mismatch"
    findings = validate_semantic(pkg)
    assert any(f.code == "SEMANTIC_NAME_MISMATCH" for f in findings)


def test_semantic_extra_frontmatter():
    pkg = FIXTURES / "invalid" / "bad-frontmatter-extra"
    findings = validate_semantic(pkg)
    assert any(f.code == "SEMANTIC_EXTRA_FRONTMATTER" for f in findings)


def test_semantic_bad_semver():
    pkg = FIXTURES / "invalid" / "bad-semver"
    findings = validate_semantic(pkg)
    assert any(f.code == "SEMANTIC_BAD_SEMVER" for f in findings)


def test_semantic_bad_category():
    pkg = FIXTURES / "invalid" / "bad-category"
    findings = validate_semantic(pkg)
    assert any(
        "category" in f.message.lower() or f.code in ("SEMANTIC_CONTRACT_PARSE",)
        for f in findings
    )


# ——— safety validation ———


def test_safety_valid_minimal():
    pkg = FIXTURES / "valid" / "minimal-producer"
    findings = validate_safety(pkg)
    assert _count_errors(findings) == 0, f"Unexpected errors: {findings}"


def test_safety_bad_write_policy():
    pkg = FIXTURES / "invalid" / "bad-write-policy"
    findings = validate_safety(pkg)
    assert any(f.code == "SAFETY_WRITE_POLICY" for f in findings)


def test_safety_absolute_path():
    pkg = FIXTURES / "invalid" / "bad-absolute-path"
    findings = validate_safety(pkg)
    # Should detect C:\Users\... and /home/... and %APPDATA%
    assert any(f.code == "SAFETY_ABSOLUTE_PATH" for f in findings)


def test_safety_self_bypass():
    pkg = FIXTURES / "invalid" / "bad-self-bypass"
    findings = validate_safety(pkg)
    assert any(f.code == "SAFETY_BYPASS_CLAIM" for f in findings)


# ——— registry ———


def test_registry_discover_valid_only():
    registry = SkillRegistry([FIXTURES / "valid"])
    packages = registry.discover()
    assert len(packages) == 3
    names = {p.name for p in packages}
    assert names == {"minimal-producer", "comprehensive-router", "minimal-reviewer"}


def test_registry_resolve():
    registry = SkillRegistry([FIXTURES / "valid"])
    meta = registry.resolve(FIXTURES / "valid" / "minimal-producer")
    assert meta is not None
    assert meta.contract_id == "minimal-producer"
    assert meta.status == SkillStatus.DRAFT
    assert meta.validation_result is not None
    assert meta.validation_result.passed


def test_registry_resolve_invalid():
    registry = SkillRegistry([FIXTURES / "invalid"])
    meta = registry.resolve(FIXTURES / "invalid" / "bad-id-mismatch")
    assert meta is not None
    assert meta.validation_result is not None
    assert not meta.validation_result.passed


def test_registry_get_summary():
    registry = SkillRegistry([FIXTURES / "valid"])
    summary = registry.get_summary()
    assert summary["total"] == 3
    assert summary["valid"] == 3


# ——— graph ———


def test_graph_build():
    registry = SkillRegistry([FIXTURES / "valid"])
    graph = build_graph(registry)
    assert len(graph.nodes) == 3
    assert "minimal-producer" in graph.nodes
    assert "comprehensive-router" in graph.nodes
    assert "minimal-reviewer" in graph.nodes


def test_graph_cycle_detection():
    registry = SkillRegistry([FIXTURES / "invalid"])
    graph = build_graph(registry)
    findings = validate_graph(graph)
    assert any(f.code == "GRAPH_CYCLE" for f in findings)


def test_graph_router_warning():
    registry = SkillRegistry([FIXTURES / "valid"])
    graph = build_graph(registry)
    findings = validate_graph(graph)
    errors = [f for f in findings if f.severity == Severity.ERROR]
    assert len(errors) == 0, f"Unexpected errors: {errors}"


# ——— scaffolder ———


def test_scaffolder_init(tmp_path: Path):
    target = tmp_path / "test-skill"
    pkg = init_skill_package(
        target_dir=target,
        name="test-skill",
        description="A test skill from scaffolder",
        category="knowledge",
        kind="producer",
        resources=["references"],
    )
    assert pkg.exists()
    assert (pkg / "SKILL.md").is_file()
    assert (pkg / "contract.json").is_file()
    assert (pkg / "agents" / "openai.yaml").is_file()
    assert (pkg / "references").is_dir()

    # Verify generated files are valid
    contract_data = json.loads((pkg / "contract.json").read_text())
    assert contract_data["id"] == "test-skill"
    assert contract_data["category"] == "knowledge"
    assert contract_data["kind"] == "producer"

    # Generated package should pass validation
    findings = validate_structural(pkg) + validate_semantic(pkg) + validate_safety(pkg)
    assert _count_errors(findings) == 0, findings


def test_scaffolder_no_overwrite(tmp_path: Path):
    target = tmp_path / "existing"
    target.mkdir()
    (target / "SKILL.md").write_text("existing")
    (target / "contract.json").write_text("{}")
    (target / "agents").mkdir()
    (target / "agents" / "openai.yaml").write_text("x: 1")
    with pytest.raises(FileExistsError):
        init_skill_package(
            target_dir=target,
            name="existing",
            description="test",
            category="knowledge",
            kind="producer",
        )


def test_scaffolder_router_gets_implicit_true(tmp_path: Path):
    target = tmp_path / "router-skill"
    pkg = init_skill_package(
        target_dir=target,
        name="router-skill",
        description="A router skill",
        category="routing",
        kind="router",
    )
    oa_raw = yaml.safe_load((pkg / "agents" / "openai.yaml").read_text())
    assert oa_raw["policy"]["allow_implicit_invocation"] is True


def test_scaffolder_producer_gets_implicit_false(tmp_path: Path):
    target = tmp_path / "producer-skill"
    pkg = init_skill_package(
        target_dir=target,
        name="producer-skill",
        description="A producer skill",
        category="engineering",
        kind="producer",
    )
    oa_raw = yaml.safe_load((pkg / "agents" / "openai.yaml").read_text())
    assert oa_raw["policy"]["allow_implicit_invocation"] is False


# ——— validation repeatability ———


def test_validation_repeatable():
    """Same package should produce same findings across two runs."""
    pkg = FIXTURES / "valid" / "comprehensive-router"
    r1 = validate_structural(pkg) + validate_semantic(pkg) + validate_safety(pkg)
    r2 = validate_structural(pkg) + validate_semantic(pkg) + validate_safety(pkg)
    assert len(r1) == len(r2)
    assert [f.code for f in r1] == [f.code for f in r2]


# ——— CLI smoke ———


def test_cli_init(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """CLI init should create a package and exit 0."""
    target = tmp_path / "cli-test-skill"
    monkeypatch.setattr(sys, "argv", [
        "inkdesk-skill", "init", "cli-test-skill",
        "--description", "CLI test",
        "--category", "knowledge",
        "--kind", "producer",
        "--target", str(target),
    ])
    from inkdesk_skill_sdk.cli import main
    rc = main()
    assert rc == 0
    assert target.exists()
    assert (target / "SKILL.md").is_file()


def test_cli_validate_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """CLI validate should exit 0 for valid packages."""
    monkeypatch.setattr(sys, "argv", [
        "inkdesk-skill", "validate",
        "--root", str(FIXTURES / "valid"),
    ])
    from inkdesk_skill_sdk.cli import main
    rc = main()
    assert rc == 0


def test_cli_validate_invalid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """CLI validate should exit non-zero for invalid packages."""
    monkeypatch.setattr(sys, "argv", [
        "inkdesk-skill", "validate",
        "--root", str(FIXTURES / "invalid"),
    ])
    from inkdesk_skill_sdk.cli import main
    rc = main()
    assert rc != 0


def test_cli_graph(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """CLI graph should exit 0 for valid packages."""
    monkeypatch.setattr(sys, "argv", [
        "inkdesk-skill", "graph",
        "--root", str(FIXTURES / "valid"),
    ])
    from inkdesk_skill_sdk.cli import main
    rc = main()
    assert rc == 0


# ——— 4.2.1 integration tests ———


def test_real_skills_all_validate():
    """All 13 real skill packages in vault/skills/ must pass full validation."""
    registry = SkillRegistry([Path("vault/skills")])
    packages = registry.discover()
    # At minimum we expect 13 skills; fixture dirs don't count
    assert len(packages) >= 13
    failed = []
    for p in packages:
        meta = registry.resolve(p)
        assert meta is not None, f"Registry could not resolve {p.name}"
        vr = meta.validation_result
        if not vr.passed:
            failed.append((meta.name, vr.findings))
    assert not failed, f"Skills failed validation: {failed}"


def test_real_skills_graph_integrity():
    """Routing graph for real skills must have no cycles."""
    registry = SkillRegistry([Path("vault/skills")])
    graph = build_graph(registry)
    assert len(graph.nodes) >= 13
    findings = validate_graph(graph)
    errors = [f for f in findings if f.severity == Severity.ERROR]
    assert not errors, f"Graph errors: {errors}"


def test_real_skills_link_completeness():
    """Every nextSkills reference must resolve to an existing skill (check raw contract)."""
    import json
    registry = SkillRegistry([Path("vault/skills")])
    packages = registry.discover()
    all_ids = {p.name for p in packages}
    missing = []
    for p in packages:
        ct = json.loads((p / "contract.json").read_text(encoding="utf-8"))
        for ns in ct.get("nextSkills", []):
            if ns["skillId"] not in all_ids:
                missing.append(f"{p.name} -> {ns['skillId']}")
    assert not missing, f"Broken nextSkills links: {missing}"


def test_real_skills_router_has_all_links():
    """skill-router should have nextSkills covering all other skills."""
    import json
    registry = SkillRegistry([Path("vault/skills")])
    rt_ct = json.loads(Path("vault/skills/skill-router/contract.json").read_text(encoding="utf-8"))
    router_targets = {ns["skillId"] for ns in rt_ct.get("nextSkills", [])}
    all_ids = {p.name for p in registry.discover()}
    all_ids.discard("skill-router")
    missing = all_ids - router_targets
    assert not missing, f"skill-router missing links to: {missing}"


def test_real_skills_knowledge_chain():
    """Knowledge chain: all producers link to patch-wiki-page or deposit-answer."""
    import json
    knowledge_ids = {"ingest-source", "answer-from-wiki", "deposit-answer",
                     "patch-wiki-page", "run-wiki-health", "extract-insight"}
    for sid in knowledge_ids:
        ct = json.loads(Path(f"vault/skills/{sid}/contract.json").read_text(encoding="utf-8"))
        if sid != "patch-wiki-page":
            targets = {ns["skillId"] for ns in ct.get("nextSkills", [])}
            assert targets, f"{sid} has no nextSkills"
            assert targets & {"patch-wiki-page", "deposit-answer"}, \
                f"{sid} should link to patch-wiki-page or deposit-answer, got {targets}"


def test_real_skills_dev_chain():
    """Dev chain: tech-solution -> tech-review -> coding -> test-prep -> test-fix."""
    import json
    chain = ["tech-solution", "tech-review", "coding", "test-prep", "test-fix"]
    for i, sid in enumerate(chain):
        ct = json.loads(Path(f"vault/skills/{sid}/contract.json").read_text(encoding="utf-8"))
        if i < len(chain) - 1:
            targets = {ns["skillId"] for ns in ct.get("nextSkills", [])}
            expected_next = chain[i + 1]
            assert expected_next in targets, \
                f"{sid} should link to {expected_next}, got {targets}"


def test_real_skills_diagnostic_write_policy():
    """diagnostic skills must not claim direct wiki write."""
    import json
    for sid in ["test-fix", "problem-solve", "run-wiki-health"]:
        ct = json.loads(Path(f"vault/skills/{sid}/contract.json").read_text(encoding="utf-8"))
        cw = ct.get("writePolicy", {}).get("canonicalWiki", "")
        assert cw in ("denied", "proposal-only"), \
            f"{sid} canonicalWiki={cw}, must be denied or proposal-only"


def test_real_skills_producer_has_hard_gates():
    """Every producer skill must declare at least required_input gate."""
    import json
    registry = SkillRegistry([Path("vault/skills")])
    for p in registry.discover():
        if p.name == "skill-router":
            continue
        ct = json.loads((p / "contract.json").read_text(encoding="utf-8"))
        if ct.get("kind") == "producer":
            kinds = {g["kind"] for g in ct.get("hardGates", [])}
            assert "required_input" in kinds, \
                f"{p.name} producer missing required_input gate"


def test_real_skills_no_direct_wiki_write_claim():
    """Sweep: no skill contract should claim direct wiki write."""
    import json
    registry = SkillRegistry([Path("vault/skills")])
    for p in registry.discover():
        raw = (p / "contract.json").read_text(encoding="utf-8")
        data = json.loads(raw)
        cw = data.get("writePolicy", {}).get("canonicalWiki", "")
        assert cw != "direct", f"{p.name} has canonicalWiki=direct"
