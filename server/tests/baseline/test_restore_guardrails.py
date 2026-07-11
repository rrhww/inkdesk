from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest


F01_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts" / "f01"
sys.path.insert(0, str(F01_SCRIPTS))

from baseline_contracts import (  # noqa: E402
    RestoreGuardrailError,
    validate_restore_database_name,
    validate_restore_vault_target,
    validate_zip_members,
)


@pytest.mark.parametrize(
    "target_database",
    ["inkdesk", "postgres", "template0", "template1", "scratch", "inkdesk_f01_restore_"],
)
def test_rejects_active_or_invalid_restore_database_name(target_database: str) -> None:
    with pytest.raises(RestoreGuardrailError, match="database"):
        validate_restore_database_name(target_database, source_database="inkdesk")


def test_accepts_generated_restore_database_name() -> None:
    validate_restore_database_name("inkdesk_f01_restore_20260711_abcdef", source_database="inkdesk")


def test_rejects_active_vault_and_non_empty_target(tmp_path: Path) -> None:
    evidence_root = tmp_path / ".local" / "f01-baseline" / "run"
    active_vault = tmp_path / "vault"
    active_vault.mkdir(parents=True)
    restore_target = evidence_root / "restore" / "vault"
    restore_target.mkdir(parents=True)
    (restore_target / "existing.md").write_text("do not overwrite", encoding="utf-8")

    with pytest.raises(RestoreGuardrailError, match="active"):
        validate_restore_vault_target(active_vault, evidence_root=evidence_root, active_vault=active_vault)

    with pytest.raises(RestoreGuardrailError, match="non-empty"):
        validate_restore_vault_target(restore_target, evidence_root=evidence_root, active_vault=active_vault)


def test_accepts_new_vault_target_below_evidence_root(tmp_path: Path) -> None:
    evidence_root = tmp_path / ".local" / "f01-baseline" / "run"
    active_vault = tmp_path / "vault"
    active_vault.mkdir()

    validate_restore_vault_target(
        evidence_root / "restore" / "vault",
        evidence_root=evidence_root,
        active_vault=active_vault,
    )


@pytest.mark.parametrize("entry_name", ["../escape.md", "/absolute.md", "C:/windows.md"])
def test_rejects_dangerous_zip_member_paths(entry_name: str, tmp_path: Path) -> None:
    info = zipfile.ZipInfo(entry_name)

    with pytest.raises(RestoreGuardrailError, match="ZIP"):
        validate_zip_members([info], destination=tmp_path / "restore")


def test_rejects_zip_symbolic_link(tmp_path: Path) -> None:
    info = zipfile.ZipInfo("wiki/link.md")
    info.create_system = 3
    info.external_attr = 0o120777 << 16

    with pytest.raises(RestoreGuardrailError, match="symbolic"):
        validate_zip_members([info], destination=tmp_path / "restore")


def test_rejects_zip_target_escape_after_resolution(tmp_path: Path) -> None:
    destination = tmp_path / "restore"
    info = zipfile.ZipInfo("nested/../../escape.md")

    with pytest.raises(RestoreGuardrailError, match="escape"):
        validate_zip_members([info], destination=destination)
