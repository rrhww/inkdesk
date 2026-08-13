from __future__ import annotations

import json
from pathlib import Path

import pytest

from inkdesk_server.core.config import get_settings
from inkdesk_server.graph_classification import classify_document
from inkdesk_server.graph_index import DirectoryScanner


def test_explicit_graph_metadata_overrides_inferred_classification() -> None:
    classification, warnings = classify_document(
        {
            "type": "concept",
            "stage": "verification",
            "domain": "quality",
            "category": "test-plan",
            "importance": "core",
            "graphVisibility": "primary",
        },
        "docs/product/example.md",
        source="repo",
        kind="concept",
    )

    assert warnings == ()
    assert classification.stage == "verification"
    assert classification.domain == "quality"
    assert classification.category == "test-plan"
    assert classification.importance == "core"
    assert classification.visibility == "primary"
    assert classification.origin == "frontmatter"


@pytest.mark.parametrize(
    ("path", "expected_visibility"),
    [
        ("server/tests/skill_fixtures/invalid/SKILL.md", "hidden"),
        ("server/vault/skills/tech-solution/templates/solution-template.md", "hidden"),
        (".claude/rules/agent.md", "hidden"),
        ("README.md", "secondary"),
    ],
)
def test_path_rules_keep_internal_markdown_out_of_the_primary_map(
    path: str,
    expected_visibility: str,
) -> None:
    classification, warnings = classify_document({}, path, source="repo", kind="document")

    assert warnings == ()
    assert classification.visibility == expected_visibility


def test_invalid_explicit_values_fall_back_and_emit_a_warning() -> None:
    classification, warnings = classify_document(
        {
            "stage": "brainstorm-everything",
            "domain": "Harness & Agents",
            "importance": "critical",
            "graphVisibility": "public",
        },
        "docs/architecture/adr-004.md",
        source="repo",
        kind="document",
    )

    assert classification.stage == "design"
    assert classification.domain == "architecture"
    assert classification.importance == "core"
    assert classification.visibility == "primary"
    assert classification.origin == "rule"
    assert {warning.field for warning in warnings} == {
        "stage",
        "domain",
        "importance",
        "graphVisibility",
    }


def test_existing_metadata_rules_take_precedence_over_path_rules() -> None:
    classification, warnings = classify_document(
        {"type": "tech-solution", "tags": ["harness"]},
        "tests/quality/fixture.md",
        source="repo",
        kind="document",
    )

    assert warnings == ()
    assert classification.stage == "design"
    assert classification.domain == "harness-agents"
    assert classification.category == "tech-solution"
    assert classification.visibility == "hidden"


def test_scanner_loads_legacy_snapshots_without_classification(
    temp_app_env: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setenv("INKDESK_REPO_ROOT", str(repo_root))
    get_settings.cache_clear()
    scanner = DirectoryScanner(get_settings())
    scanner.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    scanner.snapshot_path.write_text(
        json.dumps(
            {
                "version": "legacy",
                "generatedAt": "2026-08-04T00:00:00Z",
                "nodes": [
                    {
                        "id": "repo:README.md",
                        "label": "Readme",
                        "kind": "document",
                        "path": "README.md",
                        "source": "repo",
                        "status": "indexed",
                        "summary": "",
                    }
                ],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )

    snapshot = scanner.load_snapshot()

    assert snapshot.version == "legacy"
    assert snapshot.nodes[0].classification.stage == "knowledge"
    assert snapshot.nodes[0].classification.visibility == "secondary"


def test_snapshot_version_changes_when_only_graph_classification_changes(
    temp_app_env: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    document = repo_root / "proposal.md"
    document.write_text("---\nstage: design\n---\n# Proposal\n", encoding="utf-8")
    monkeypatch.setenv("INKDESK_REPO_ROOT", str(repo_root))
    get_settings.cache_clear()
    scanner = DirectoryScanner(get_settings())

    first = scanner.scan()
    document.write_text("---\nstage: verification\n---\n# Proposal\n", encoding="utf-8")
    second = scanner.scan()

    assert first.version != second.version
    assert first.nodes[0].classification.stage == "design"
    assert second.nodes[0].classification.stage == "verification"
    assert second.to_dict()["stats"]["classificationWarningCount"] == 0
