"""Assemble F01 capture status and a paired source fingerprint without record content."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from baseline_contracts import canonical_sha256, canonical_json


def summarize_capture(
    *,
    mode: str,
    contracts: Sequence[Mapping[str, Any]],
    tests: Sequence[Mapping[str, Any]],
    backup_status: str | None,
    restore_status: str | None,
) -> dict[str, Any]:
    """Return the only statuses a capture may honestly report."""

    if mode != "all":
        return _failed_summary("Only a complete all capture can certify an F01 baseline.")
    if not contracts or any(contract.get("status") != "PASS" for contract in contracts):
        return _failed_summary("Required contract evidence is unavailable or failing.")
    if not tests or any(test.get("status") not in {"PASS", "PASS_WITH_KNOWN_ISSUES"} for test in tests):
        return _failed_summary("Required test evidence is unavailable or failing.")
    if backup_status != "PASS" or restore_status != "PASS":
        return _failed_summary("Backup or restore verification did not pass.")

    known_issue_ids = sorted(
        {
            issue_id
            for test in tests
            if test.get("status") == "PASS_WITH_KNOWN_ISSUES"
            for issue_id in test.get("knownIssueIds", [])
            if isinstance(issue_id, str) and issue_id
        }
    )
    if any(test.get("status") == "PASS_WITH_KNOWN_ISSUES" and not test.get("knownIssueIds") for test in tests):
        return _failed_summary("Known-issue test evidence is missing its issue identifier.")
    return {
        "overallStatus": "PASS_WITH_KNOWN_ISSUES" if known_issue_ids else "PASS",
        "knownIssueIds": known_issue_ids,
        "reason": None,
    }


def write_source_fingerprint(*, database_path: Path, vault_path: Path, output_path: Path) -> dict[str, Any]:
    """Combine content-free database and Vault fingerprints into one hashable record."""

    database = _load_mapping(database_path, "database fingerprint")
    vault = _load_mapping(vault_path, "Vault fingerprint")
    payload = {"schemaVersion": "1.0", "database": database, "vault": vault}
    result = {**payload, "sha256": canonical_sha256(payload)}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(canonical_json(result) + "\n", encoding="utf-8", newline="\n")
    return result


def select_known_issues(document: Mapping[str, Any] | Sequence[Mapping[str, Any]], *, issue_ids: Sequence[str]) -> list[dict[str, Any]]:
    """Select only the current issue records actually matched during one capture."""

    issues = document.get("issues", []) if isinstance(document, Mapping) else document
    if not isinstance(issues, Sequence) or isinstance(issues, (str, bytes)):
        raise ValueError("known issues document must contain an issues list")
    selected_ids = set(issue_ids)
    return [dict(issue) for issue in issues if isinstance(issue, Mapping) and issue.get("id") in selected_ids]


def _failed_summary(reason: str) -> dict[str, Any]:
    return {"overallStatus": "FAIL", "knownIssueIds": [], "reason": reason}


def _load_mapping(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"{label} is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} is not valid JSON: {path}") from error
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    summary = commands.add_parser("summary")
    summary.add_argument("--input", type=Path, required=True)
    summary.add_argument("--output", type=Path, required=True)
    fingerprint = commands.add_parser("source-fingerprint")
    fingerprint.add_argument("--database", type=Path, required=True)
    fingerprint.add_argument("--vault", type=Path, required=True)
    fingerprint.add_argument("--output", type=Path, required=True)
    issues = commands.add_parser("select-known-issues")
    issues.add_argument("--known-issues", type=Path, required=True)
    issues.add_argument("--issue-ids", type=Path, required=True)
    issues.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)

    if arguments.command == "source-fingerprint":
        write_source_fingerprint(database_path=arguments.database, vault_path=arguments.vault, output_path=arguments.output)
        return 0
    if arguments.command == "select-known-issues":
        document = _load_mapping(arguments.known_issues, "known issues")
        issue_ids = _load_string_list(arguments.issue_ids, "known issue IDs")
        result = select_known_issues(document, issue_ids=issue_ids)
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(canonical_json(result) + "\n", encoding="utf-8", newline="\n")
        return 0

    document = _load_mapping(arguments.input, "capture summary input")
    result = summarize_capture(
        mode=str(document.get("mode", "")),
        contracts=_mapping_sequence(document.get("contracts")),
        tests=_mapping_sequence(document.get("tests")),
        backup_status=_string_or_none(document.get("backupStatus")),
        restore_status=_string_or_none(document.get("restoreStatus")),
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(canonical_json(result) + "\n", encoding="utf-8", newline="\n")
    return 0


def _mapping_sequence(value: Any) -> Sequence[Mapping[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        return []
    return value


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _load_string_list(path: Path, label: str) -> list[str]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"{label} are missing: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} are not valid JSON: {path}") from error
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{label} must be a JSON array of non-empty strings: {path}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
