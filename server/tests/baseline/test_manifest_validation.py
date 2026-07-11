from __future__ import annotations

import sys
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


F01_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts" / "f01"
sys.path.insert(0, str(F01_SCRIPTS))

from baseline_contracts import ManifestValidationError, validate_manifest  # noqa: E402


def _valid_manifest() -> dict[str, object]:
    return {
        "schemaVersion": "1.0",
        "runId": "20260711T120000Z-example",
        "startedAt": "2026-07-11T12:00:00Z",
        "completedAt": "2026-07-11T12:01:00Z",
        "overallStatus": "PASS",
        "git": {"commit": "abc123", "branch": "main", "dirty": False},
        "environment": {
            "os": "Windows",
            "python": "3.12",
            "node": "22",
            "npm": "10",
            "docker": "27",
            "compose": "2",
            "postgres": "16",
        },
        "configuration": {
            "mode": "docker",
            "composeFile": "infra/docker-compose.local-docker.yml",
            "services": ["local-postgres", "local-server", "local-web"],
            "database": "inkdesk",
            "vaultSource": "volume:inkdesk-local-vault-data",
        },
        "contracts": [
            {
                "name": "openapi",
                "path": "contracts/openapi.json",
                "sha256": "a" * 64,
                "status": "PASS",
            }
        ],
        "tests": [
            {
                "suite": "server",
                "command": "python -m pytest",
                "exitCode": 0,
                "duration": 1.25,
                "status": "PASS",
                "stdout": "tests/server.stdout.log",
                "stderr": "tests/server.stderr.log",
                "knownIssueIds": [],
            }
        ],
        "backup": {
            "database": {
                "path": "backup/postgres.dump",
                "format": "custom",
                "sha256": "b" * 64,
            },
            "vault": {
                "path": "backup/vault.zip",
                "fileCount": 2,
                "sha256": "c" * 64,
            },
        },
        "sourceFingerprint": {"path": "fingerprints/source.json", "sha256": "d" * 64},
        "restore": {
            "targetDatabase": "inkdesk_f01_restore_example",
            "targetVault": "restore/vault",
            "status": "PASS",
            "cleanupStatus": "CLEANED",
            "reportPath": "restore/report.json",
        },
        "knownIssueIds": [],
    }


def _known_issue(**overrides: object) -> dict[str, object]:
    expires_at = datetime.now(UTC) + timedelta(days=14)
    issue: dict[str, object] = {
        "id": "F01-TOOL-001",
        "kind": "tooling",
        "scope": {"suite": "web-fullstack", "command": "npm run e2e:fullstack"},
        "matcher": {"exitCode": 1, "stderrContains": "port 5432"},
        "evidence": "https://example.invalid/f01-tool-001",
        "reason": "The existing preflight command hard-codes a local port.",
        "disposition": "track",
        "firstObservedAt": "2026-07-11T12:00:00Z",
        "expiresAt": expires_at.isoformat().replace("+00:00", "Z"),
        "blocksNextPlan": False,
    }
    issue.update(overrides)
    return issue


def test_accepts_complete_manifest_in_local_evidence_directory(tmp_path: Path) -> None:
    evidence_root = tmp_path / ".local" / "f01-baseline" / "20260711T120000Z-example"

    validate_manifest(_valid_manifest(), evidence_root=evidence_root)


def test_rejects_manifest_with_missing_checksum(tmp_path: Path) -> None:
    manifest = _valid_manifest()
    del manifest["backup"]["database"]["sha256"]  # type: ignore[index]

    with pytest.raises(ManifestValidationError, match="sha256"):
        validate_manifest(manifest, evidence_root=tmp_path / ".local" / "f01-baseline" / "run")


@pytest.mark.parametrize("status", ["SUCCESS", "SKIPPED", "pass"])
def test_rejects_unknown_overall_status(tmp_path: Path, status: str) -> None:
    manifest = _valid_manifest()
    manifest["overallStatus"] = status

    with pytest.raises(ManifestValidationError, match="overallStatus"):
        validate_manifest(manifest, evidence_root=tmp_path / ".local" / "f01-baseline" / "run")


@pytest.mark.parametrize(
    ("issue_overrides", "message"),
    [
        ({"matcher": {"stderrRegex": ".*"}}, "matcher"),
        ({"scope": "all tests"}, "scope"),
        ({"expiresAt": "2020-01-01T00:00:00Z"}, "expiresAt"),
    ],
)
def test_rejects_imprecise_or_expired_known_issue(
    tmp_path: Path, issue_overrides: dict[str, object], message: str
) -> None:
    manifest = _valid_manifest()
    issue = _known_issue(**issue_overrides)
    manifest["knownIssueIds"] = [issue["id"]]
    manifest["knownIssues"] = [issue]

    with pytest.raises(ManifestValidationError, match=message):
        validate_manifest(manifest, evidence_root=tmp_path / ".local" / "f01-baseline" / "run")


@pytest.mark.parametrize("path", ["C:/evidence/postgres.dump", "/tmp/postgres.dump", "../outside.dump"])
def test_rejects_absolute_or_escaping_evidence_path(tmp_path: Path, path: str) -> None:
    manifest = deepcopy(_valid_manifest())
    manifest["backup"]["database"]["path"] = path  # type: ignore[index]

    with pytest.raises(ManifestValidationError, match="path"):
        validate_manifest(manifest, evidence_root=tmp_path / ".local" / "f01-baseline" / "run")


def test_rejects_manifest_evidence_outside_local_directory(tmp_path: Path) -> None:
    with pytest.raises(ManifestValidationError, match=".local"):
        validate_manifest(_valid_manifest(), evidence_root=tmp_path / "evidence" / "run")
