from __future__ import annotations

import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest


F01_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts" / "f01"
sys.path.insert(0, str(F01_SCRIPTS))

from baseline_contracts import (  # noqa: E402
    RestoreGuardrailError,
    create_vault_zip,
    fingerprint_table_rows,
    fingerprint_vault,
    safe_extract_vault_zip,
)


def test_table_fingerprint_is_stable_for_row_order_and_json_key_order() -> None:
    rows = [
        {"id": "topic-2", "payload": {"z": 2, "a": 1}, "created_at": datetime(2026, 7, 11, 12, tzinfo=UTC)},
        {"id": "topic-1", "payload": {"a": 1, "z": 2}, "created_at": datetime(2026, 7, 11, 11, tzinfo=UTC)},
    ]
    reordered = [
        {"id": "topic-1", "payload": {"z": 2, "a": 1}, "created_at": datetime(2026, 7, 11, 11, tzinfo=UTC)},
        {"id": "topic-2", "payload": {"a": 1, "z": 2}, "created_at": datetime(2026, 7, 11, 12, tzinfo=UTC)},
    ]

    assert fingerprint_table_rows("topics", rows, primary_key=["id"]) == fingerprint_table_rows(
        "topics", reordered, primary_key=["id"]
    )


def test_table_fingerprint_captures_empty_table_and_binary_values() -> None:
    empty = fingerprint_table_rows("events", [], primary_key=["id"])
    binary = fingerprint_table_rows("events", [{"id": "event-1", "data": b"\x00\xff"}], primary_key=["id"])

    assert empty["rowCount"] == 0
    assert empty["sha256"] != binary["sha256"]


def test_table_fingerprint_requires_a_primary_key() -> None:
    with pytest.raises(ValueError, match="primary key"):
        fingerprint_table_rows("audit_entries", [{"message": "x"}], primary_key=[])


def test_vault_fingerprint_tracks_only_relative_path_size_and_hash(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    (vault / "wiki").mkdir(parents=True)
    (vault / "wiki" / "topic.md").write_text("stable", encoding="utf-8")

    fingerprint = fingerprint_vault(vault)

    assert fingerprint["fileCount"] == 1
    assert fingerprint["files"] == [{
        "path": "wiki/topic.md",
        "size": len("stable".encode("utf-8")),
        "sha256": fingerprint["files"][0]["sha256"],
    }]
    assert "stable" not in str(fingerprint)

    (vault / "wiki" / "topic.md").write_text("changed", encoding="utf-8")
    assert fingerprint["sha256"] != fingerprint_vault(vault)["sha256"]


def test_vault_fingerprint_rejects_symbolic_links(tmp_path: Path) -> None:
    linked = tmp_path / "linked-vault"
    linked.mkdir()
    target = tmp_path / "target.md"
    target.write_text("target", encoding="utf-8")
    try:
        (linked / "link.md").symlink_to(target)
    except OSError:
        pytest.skip("symbolic links are not available in this test environment")
    with pytest.raises(RestoreGuardrailError, match="symbolic"):
        fingerprint_vault(linked)


def test_safe_vault_archive_round_trip_preserves_fingerprint(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "raw").mkdir(parents=True)
    (source / "raw" / "note.md").write_text("F01 restore evidence", encoding="utf-8")
    archive = tmp_path / "vault.zip"
    evidence_root = tmp_path / ".local" / "f01-baseline" / "run"
    active_vault = tmp_path / "active"
    active_vault.mkdir()
    restored = evidence_root / "restore" / "vault"

    create_vault_zip(source, archive)
    safe_extract_vault_zip(archive, restored, evidence_root=evidence_root, active_vault=active_vault)

    assert fingerprint_vault(source) == fingerprint_vault(restored)


def test_safe_vault_extraction_rejects_dangerous_zip_before_writing(tmp_path: Path) -> None:
    archive = tmp_path / "dangerous.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../outside.md", "blocked")
    evidence_root = tmp_path / ".local" / "f01-baseline" / "run"
    destination = evidence_root / "restore" / "vault"
    active_vault = tmp_path / "active"
    active_vault.mkdir()

    with pytest.raises(RestoreGuardrailError, match="ZIP"):
        safe_extract_vault_zip(archive, destination, evidence_root=evidence_root, active_vault=active_vault)
    assert not destination.exists()


def test_safe_vault_extraction_rejects_case_colliding_zip_paths(tmp_path: Path) -> None:
    archive = tmp_path / "case-collision.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("wiki/Readme.md", "one")
        handle.writestr("wiki/README.md", "two")
    evidence_root = tmp_path / ".local" / "f01-baseline" / "run"
    destination = evidence_root / "restore" / "vault"
    active_vault = tmp_path / "active"
    active_vault.mkdir()

    with pytest.raises(RestoreGuardrailError, match="case"):
        safe_extract_vault_zip(archive, destination, evidence_root=evidence_root, active_vault=active_vault)
    assert not destination.exists()
