from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest


F01_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts" / "f01"
sys.path.insert(0, str(F01_SCRIPTS))

RESTORE_SCRIPT = F01_SCRIPTS / "restore-drill.ps1"

from baseline_contracts import (  # noqa: E402
    RestoreGuardrailError,
    validate_restore_database_name,
    validate_restore_vault_target,
    validate_zip_members,
)


@pytest.mark.parametrize(
    "target_database",
    [
        "inkdesk",
        "postgres",
        "template0",
        "template1",
        "scratch",
        "inkdesk_f01_restore_",
        "inkdesk_f01_restore_" + "x" * 64,
    ],
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


def test_restore_script_does_not_enumerate_a_missing_vault_target() -> None:
    script = RESTORE_SCRIPT.read_text(encoding="utf-8")
    expected_guard = "if ((Test-Path -LiteralPath $targetVault) -and (Get-ChildItem -LiteralPath $targetVault -Force | Select-Object -First 1))"

    assert script.count(expected_guard) == 2


def test_restore_script_uses_psycopg_urls_for_application_read_checks() -> None:
    script = RESTORE_SCRIPT.read_text(encoding="utf-8")

    assert '"postgresql+psycopg://$escapedUser`:$escapedPassword@127.0.0.1`:$($context.Port)/$($context.DatabaseName)"' in script
    assert '"postgresql+psycopg://$escapedUser`:$escapedPassword@127.0.0.1`:$($context.Port)/$targetDatabase"' in script


def test_restore_script_bounds_generated_database_names_with_a_digest() -> None:
    script = RESTORE_SCRIPT.read_text(encoding="utf-8")

    assert "function Get-F01GeneratedRestoreDatabaseName" in script
    assert "$maximumDatabaseNameLength = 63" in script
    assert "[Security.Cryptography.SHA256]::HashData" in script


def test_restore_script_uses_long_database_options_through_the_argument_wrapper() -> None:
    script = RESTORE_SCRIPT.read_text(encoding="utf-8")

    assert "pg_restore --exit-on-error -U $context.DatabaseUser --dbname $targetDatabase $dumpInContainer" in script
    assert "pg_restore --exit-on-error -U $context.DatabaseUser -d $targetDatabase" not in script
    assert "psql -U $context.DatabaseUser --dbname postgres --set ON_ERROR_STOP=1" in script
    assert "psql -U $context.DatabaseUser -d postgres" not in script


def test_restore_script_cleans_only_targets_created_by_this_drill() -> None:
    script = RESTORE_SCRIPT.read_text(encoding="utf-8")

    assert "$targetDatabaseCreated = $false" in script
    assert script.count("$targetDatabaseCreated = $true") == 2
    assert "if (-not $KeepRestoreTarget -and $targetDatabaseCreated -and $context)" in script
    assert "if (-not $KeepRestoreTarget -and $targetDatabaseCreated -and $Mode -eq \"host\"" in script
