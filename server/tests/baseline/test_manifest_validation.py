from __future__ import annotations

import sys
from copy import deepcopy
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


F01_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts" / "f01"
sys.path.insert(0, str(F01_SCRIPTS))

from baseline_contracts import ManifestValidationError, validate_manifest  # noqa: E402
from verify_baseline import EvidenceVerificationError, verify_evidence_tree  # noqa: E402


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
        "interruptionReason": None,
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


def test_accepts_a_partial_failure_manifest_with_an_interruption_reason(tmp_path: Path) -> None:
    manifest = _valid_manifest()
    manifest["overallStatus"] = "FAIL"
    manifest["configuration"]["database"] = ""  # type: ignore[index]
    manifest["contracts"] = []
    manifest["tests"] = []
    manifest["interruptionReason"] = "local-postgres and local-server must be running"

    validate_manifest(manifest, evidence_root=tmp_path / ".local" / "f01-baseline" / "run")


def test_failure_manifest_matches_the_committed_json_schema() -> None:
    manifest = _valid_manifest()
    manifest["overallStatus"] = "FAIL"
    manifest["configuration"]["database"] = ""  # type: ignore[index]
    manifest["contracts"] = []
    manifest["tests"] = []
    manifest["interruptionReason"] = "local-postgres and local-server must be running"
    schema_path = F01_SCRIPTS.parents[1] / "docs" / "delivery" / "baselines" / "f01" / "manifest.schema.json"

    errors = list(Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8"))).iter_errors(manifest))

    assert errors == []


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


def test_rejects_pass_when_a_test_used_a_known_issue(tmp_path: Path) -> None:
    manifest = _valid_manifest()
    issue = _known_issue()
    manifest["tests"][0]["exitCode"] = 1  # type: ignore[index]
    manifest["tests"][0]["status"] = "PASS_WITH_KNOWN_ISSUES"  # type: ignore[index]
    manifest["tests"][0]["knownIssueIds"] = [issue["id"]]  # type: ignore[index]
    manifest["knownIssueIds"] = [issue["id"]]
    manifest["knownIssues"] = [issue]

    with pytest.raises(ManifestValidationError, match="PASS cannot include known issues"):
        validate_manifest(manifest, evidence_root=tmp_path / ".local" / "f01-baseline" / "run")


def test_rejects_known_issue_status_when_a_test_remains_unresolved(tmp_path: Path) -> None:
    manifest = _valid_manifest()
    issue = _known_issue()
    manifest["overallStatus"] = "PASS_WITH_KNOWN_ISSUES"
    manifest["tests"][0]["exitCode"] = 1  # type: ignore[index]
    manifest["tests"][0]["status"] = "FAIL"  # type: ignore[index]
    manifest["knownIssueIds"] = [issue["id"]]
    manifest["knownIssues"] = [issue]

    with pytest.raises(ManifestValidationError, match="unresolved test evidence"):
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


def test_rejects_manifest_known_issue_that_differs_from_the_authoritative_document(tmp_path: Path) -> None:
    manifest = _valid_manifest()
    authoritative_issue = _known_issue()
    tampered_issue = dict(authoritative_issue, reason="A different reason must not be accepted.")
    manifest["tests"][0]["exitCode"] = 1  # type: ignore[index]
    manifest["tests"][0]["status"] = "PASS_WITH_KNOWN_ISSUES"  # type: ignore[index]
    manifest["tests"][0]["knownIssueIds"] = [authoritative_issue["id"]]  # type: ignore[index]
    manifest["overallStatus"] = "PASS_WITH_KNOWN_ISSUES"
    manifest["knownIssueIds"] = [authoritative_issue["id"]]
    manifest["knownIssues"] = [tampered_issue]

    with pytest.raises(ManifestValidationError, match="must match the authoritative known issues document"):
        validate_manifest(
            manifest,
            evidence_root=tmp_path / ".local" / "f01-baseline" / "run",
            known_issues=[authoritative_issue],
        )


@pytest.mark.parametrize("path", ["C:/evidence/postgres.dump", "/tmp/postgres.dump", "../outside.dump"])
def test_rejects_absolute_or_escaping_evidence_path(tmp_path: Path, path: str) -> None:
    manifest = deepcopy(_valid_manifest())
    manifest["backup"]["database"]["path"] = path  # type: ignore[index]

    with pytest.raises(ManifestValidationError, match="path"):
        validate_manifest(manifest, evidence_root=tmp_path / ".local" / "f01-baseline" / "run")


def test_rejects_manifest_evidence_outside_local_directory(tmp_path: Path) -> None:
    with pytest.raises(ManifestValidationError, match=".local"):
        validate_manifest(_valid_manifest(), evidence_root=tmp_path / "evidence" / "run")


def test_evidence_verifier_requires_each_manifest_artifact_and_matching_checksum(tmp_path: Path) -> None:
    evidence_root = tmp_path / ".local" / "f01-baseline" / "run"
    manifest = _valid_manifest()
    artifact_paths = {
        "contracts/openapi.json": "openapi",
        "tests/server.stdout.log": "stdout",
        "tests/server.stderr.log": "stderr",
        "backup/postgres.dump": "database",
        "backup/vault.zip": "vault",
        "fingerprints/source.json": "source",
        "restore/report.json": "report",
    }
    from baseline_contracts import sha256_file

    for relative_path, content in artifact_paths.items():
        target = evidence_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    manifest["contracts"][0]["sha256"] = sha256_file(evidence_root / "contracts/openapi.json")  # type: ignore[index]
    manifest["backup"]["database"]["sha256"] = sha256_file(evidence_root / "backup/postgres.dump")  # type: ignore[index]
    manifest["backup"]["vault"]["sha256"] = sha256_file(evidence_root / "backup/vault.zip")  # type: ignore[index]
    manifest["sourceFingerprint"]["sha256"] = sha256_file(evidence_root / "fingerprints/source.json")  # type: ignore[index]

    verify_evidence_tree(manifest, evidence_root=evidence_root)

    (evidence_root / "backup/vault.zip").write_text("tampered", encoding="utf-8")
    with pytest.raises(EvidenceVerificationError, match="checksum"):
        verify_evidence_tree(manifest, evidence_root=evidence_root)
