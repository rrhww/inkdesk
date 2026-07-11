from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


F01_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts" / "f01"
sys.path.insert(0, str(F01_SCRIPTS))

CAPTURE_SCRIPT = F01_SCRIPTS / "capture-baseline.ps1"

from baseline_contracts import ManifestValidationError, classify_test_result  # noqa: E402


def _known_issue() -> dict[str, object]:
    return {
        "id": "F01-TOOL-001",
        "kind": "tooling",
        "scope": {"suite": "web-fullstack", "command": "npm run e2e:fullstack"},
        "matcher": {"exitCode": 1, "stderrContains": "port 5432"},
        "evidence": "https://example.invalid/f01-tool-001",
        "reason": "The tool currently hard-codes an unavailable port.",
        "disposition": "track",
        "firstObservedAt": "2026-07-11T12:00:00Z",
        "expiresAt": (datetime.now(UTC) + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        "blocksNextPlan": False,
    }


def test_passing_command_is_recorded_as_pass() -> None:
    result = classify_test_result(
        suite="server",
        command="python -m pytest",
        exit_code=0,
        duration=1.0,
        stdout="tests passed",
        stderr="",
        known_issues=[],
    )

    assert result["status"] == "PASS"
    assert result["knownIssueIds"] == []


def test_unknown_failure_is_recorded_as_fail() -> None:
    result = classify_test_result(
        suite="server",
        command="python -m pytest",
        exit_code=1,
        duration=1.0,
        stdout="",
        stderr="assertion failed",
        known_issues=[],
    )

    assert result["status"] == "FAIL"
    assert result["knownIssueIds"] == []


def test_missing_required_environment_is_not_a_known_issue() -> None:
    result = classify_test_result(
        suite="postgres-integration",
        command="python -m pytest tests/test_pgvector_integration.py",
        exit_code=1,
        duration=0.0,
        stdout="",
        stderr="INKDESK_TEST_PGVECTOR_URL is required",
        known_issues=[],
        environment_error="INKDESK_TEST_PGVECTOR_URL is not configured",
    )

    assert result["status"] == "ENVIRONMENT_ERROR"
    assert result["knownIssueIds"] == []
    assert result["environmentError"] == "INKDESK_TEST_PGVECTOR_URL is not configured"


def test_only_exact_unexpired_known_issue_can_downgrade_a_failure() -> None:
    known_issue = _known_issue()
    result = classify_test_result(
        suite="web-fullstack",
        command="npm run e2e:fullstack",
        exit_code=1,
        duration=1.0,
        stdout="",
        stderr="backend failed on port 5432",
        known_issues=[known_issue],
    )

    assert result["status"] == "PASS_WITH_KNOWN_ISSUES"
    assert result["knownIssueIds"] == ["F01-TOOL-001"]


def test_partial_match_does_not_downgrade_failure() -> None:
    result = classify_test_result(
        suite="web-fullstack",
        command="npm run e2e:fullstack",
        exit_code=1,
        duration=1.0,
        stdout="",
        stderr="another failure",
        known_issues=[_known_issue()],
    )

    assert result["status"] == "FAIL"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"command": ""},
        {"duration": None},
        {"stdout": None},
        {"stderr": None},
    ],
)
def test_result_rejects_missing_required_execution_evidence(kwargs: dict[str, object]) -> None:
    arguments: dict[str, object] = {
        "suite": "server",
        "command": "python -m pytest",
        "exit_code": 0,
        "duration": 1.0,
        "stdout": "ok",
        "stderr": "",
        "known_issues": [],
    }
    arguments.update(kwargs)

    with pytest.raises(ManifestValidationError):
        classify_test_result(**arguments)  # type: ignore[arg-type]


def test_capture_script_adds_restore_report_path_to_the_manifest_record() -> None:
    script = CAPTURE_SCRIPT.read_text(encoding="utf-8")

    assert '$restoreReport = Get-Content -Raw -LiteralPath (Join-Path $runDirectory "restore\\report.json") | ConvertFrom-Json' in script
    assert '$restore = [ordered]@{' in script
    assert 'reportPath = "restore/report.json"' in script
