from __future__ import annotations

import sys
from pathlib import Path


F01_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts" / "f01"
sys.path.insert(0, str(F01_SCRIPTS))

from capture_summary import select_known_issues, summarize_capture, write_source_fingerprint  # noqa: E402


def _record(status: str, known_issue_ids: list[str] | None = None) -> dict[str, object]:
    return {"suite": "server", "status": status, "knownIssueIds": known_issue_ids or []}


def test_only_an_all_capture_can_report_a_certified_status() -> None:
    summary = summarize_capture(
        mode="contracts",
        contracts=[{"name": "openapi", "status": "PASS"}],
        tests=[_record("PASS")],
        backup_status="PASS",
        restore_status="PASS",
    )

    assert summary == {
        "overallStatus": "FAIL",
        "knownIssueIds": [],
        "reason": "Only a complete all capture can certify an F01 baseline.",
    }


def test_all_capture_reports_known_issue_status_only_for_matched_results() -> None:
    summary = summarize_capture(
        mode="all",
        contracts=[{"name": "openapi", "status": "PASS"}],
        tests=[_record("PASS"), _record("PASS_WITH_KNOWN_ISSUES", ["F01-TOOL-001"])],
        backup_status="PASS",
        restore_status="PASS",
    )

    assert summary == {
        "overallStatus": "PASS_WITH_KNOWN_ISSUES",
        "knownIssueIds": ["F01-TOOL-001"],
        "reason": None,
    }


def test_known_issue_result_is_not_an_unresolved_failure() -> None:
    summary = summarize_capture(
        mode="all",
        contracts=[{"name": "openapi", "status": "PASS"}],
        tests=[_record("PASS_WITH_KNOWN_ISSUES", ["F01-TOOL-001"])],
        backup_status="PASS",
        restore_status="PASS",
    )

    assert summary["overallStatus"] == "PASS_WITH_KNOWN_ISSUES"
    assert summary["reason"] is None


def test_all_capture_rejects_environment_or_recovery_failures() -> None:
    summary = summarize_capture(
        mode="all",
        contracts=[{"name": "openapi", "status": "PASS"}],
        tests=[_record("ENVIRONMENT_ERROR")],
        backup_status="PASS",
        restore_status="PASS",
    )

    assert summary["overallStatus"] == "FAIL"
    assert summary["knownIssueIds"] == []
    assert summary["reason"] == "Required test evidence is unavailable or failing."


def test_all_capture_rejects_an_unknown_test_status() -> None:
    summary = summarize_capture(
        mode="all",
        contracts=[{"name": "openapi", "status": "PASS"}],
        tests=[_record("SKIPPED")],
        backup_status="PASS",
        restore_status="PASS",
    )

    assert summary["overallStatus"] == "FAIL"
    assert summary["reason"] == "Required test evidence is unavailable or failing."


def test_source_fingerprint_combines_database_and_vault_without_record_values(tmp_path: Path) -> None:
    database_path = tmp_path / "source-database.json"
    vault_path = tmp_path / "source-vault.json"
    output_path = tmp_path / "source.json"
    database_path.write_text('{"sha256":"database-digest","tables":[{"rowCount":2}]}\n', encoding="utf-8")
    vault_path.write_text('{"sha256":"vault-digest","fileCount":3}\n', encoding="utf-8")

    result = write_source_fingerprint(
        database_path=database_path,
        vault_path=vault_path,
        output_path=output_path,
    )

    assert result["database"] == {"sha256": "database-digest", "tables": [{"rowCount": 2}]}
    assert result["vault"] == {"sha256": "vault-digest", "fileCount": 3}
    assert result["sha256"]
    assert output_path.read_text(encoding="utf-8").endswith("\n")


def test_known_issue_selection_accepts_an_empty_issue_document() -> None:
    assert select_known_issues({"schemaVersion": "1.0", "issues": []}, issue_ids=[]) == []


def test_known_issue_selection_keeps_only_matched_issue_records() -> None:
    document = {
        "issues": [
            {"id": "F01-TOOL-001", "reason": "first"},
            {"id": "F01-TOOL-002", "reason": "second"},
        ]
    }

    assert select_known_issues(document, issue_ids=["F01-TOOL-002"]) == [
        {"id": "F01-TOOL-002", "reason": "second"}
    ]
