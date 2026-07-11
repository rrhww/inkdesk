"""Pure validation and canonicalization helpers for the F01 baseline tools."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ALLOWED_OVERALL_STATUSES = {"PASS", "PASS_WITH_KNOWN_ISSUES", "FAIL"}
ALLOWED_TEST_STATUSES = ALLOWED_OVERALL_STATUSES | {"ENVIRONMENT_ERROR"}
RESTORE_DATABASE_PREFIX = "inkdesk_f01_restore_"
_SYSTEM_DATABASES = {"postgres", "template0", "template1"}
_SHA256_LENGTH = 64


class ManifestValidationError(ValueError):
    """Raised when local F01 evidence cannot be trusted."""


class RestoreGuardrailError(ValueError):
    """Raised before an operation could overwrite or escape a restore target."""


def canonical_json(value: Any) -> str:
    """Return stable JSON suitable for comparisons and hashes."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json_default)


def canonical_sha256(value: Any) -> str:
    return sha256_text(canonical_json(value))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint_table_rows(table_name: str, rows: Iterable[Mapping[str, Any]], *, primary_key: list[str]) -> dict[str, Any]:
    """Hash canonical rows in primary-key order without retaining their values."""

    if not isinstance(table_name, str) or not table_name:
        raise ValueError("table name is required")
    if not primary_key or not all(isinstance(column, str) and column for column in primary_key):
        raise ValueError(f"table {table_name} requires a primary key for deterministic fingerprinting")
    normalized_rows = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError(f"table {table_name} has a non-object row")
        missing = [column for column in primary_key if column not in row]
        if missing:
            raise ValueError(f"table {table_name} row is missing primary key columns: {', '.join(missing)}")
        normalized_rows.append(_normalize_fingerprint_value(dict(row)))
    normalized_rows.sort(key=lambda row: tuple(canonical_json(row[column]) for column in primary_key))
    stream = "".join(canonical_json(row) + "\n" for row in normalized_rows)
    return {"table": table_name, "rowCount": len(normalized_rows), "sha256": sha256_text(stream)}


def fingerprint_vault(root: Path) -> dict[str, Any]:
    """Fingerprint ordinary Vault files by relative path, byte size, and SHA-256 only."""

    if not root.is_dir():
        raise RestoreGuardrailError(f"Vault root does not exist or is not a directory: {root}")
    files: list[dict[str, Any]] = []
    seen_casefolded_paths: set[str] = set()
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if path.is_symlink():
            raise RestoreGuardrailError(f"Vault contains a symbolic link or reparse point: {path}")
        if not path.is_file():
            continue
        relative_path = path.relative_to(root).as_posix()
        normalized = relative_path.casefold()
        if normalized in seen_casefolded_paths:
            raise RestoreGuardrailError("Vault contains paths that collide on a case-insensitive filesystem")
        seen_casefolded_paths.add(normalized)
        files.append({"path": relative_path, "size": path.stat().st_size, "sha256": sha256_file(path)})
    files.sort(key=lambda item: item["path"].casefold())
    return {"fileCount": len(files), "files": files, "sha256": canonical_sha256(files)}


def create_vault_zip(source_root: Path, archive_path: Path) -> dict[str, Any]:
    """Create a deterministic Vault archive after validating the source tree."""

    fingerprint = fingerprint_vault(source_root)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for file in fingerprint["files"]:
            source = source_root / file["path"]
            info = ZipInfo(file["path"])
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, source.read_bytes(), compress_type=ZIP_DEFLATED)
    return {"path": archive_path.name, "fileCount": fingerprint["fileCount"], "sha256": sha256_file(archive_path)}


def safe_extract_vault_zip(archive_path: Path, destination: Path, *, evidence_root: Path, active_vault: Path) -> None:
    """Extract only a validated Vault ZIP into a fresh isolated target."""

    validate_restore_vault_target(destination, evidence_root=evidence_root, active_vault=active_vault)
    with ZipFile(archive_path) as archive:
        members = archive.infolist()
        validate_zip_members(members, destination=destination)
        destination.mkdir(parents=True, exist_ok=False)
        for member in members:
            if member.is_dir():
                (destination / Path(*PurePosixPath(member.filename).parts)).mkdir(parents=True, exist_ok=True)
                continue
            target = destination / Path(*PurePosixPath(member.filename).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member, "r") as source, target.open("xb") as output:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    output.write(chunk)
    fingerprint_vault(destination)


def validate_manifest(
    manifest: Mapping[str, Any], *, evidence_root: Path, known_issues: Iterable[Mapping[str, Any]] | None = None
) -> None:
    """Validate the minimum manifest contract without reading any evidence files."""

    _require_local_evidence_root(evidence_root)
    _require_mapping(manifest, "manifest")
    _require_fields(
        manifest,
        {
            "schemaVersion",
            "runId",
            "startedAt",
            "completedAt",
            "overallStatus",
            "git",
            "environment",
            "configuration",
            "contracts",
            "tests",
            "backup",
            "sourceFingerprint",
            "restore",
            "knownIssueIds",
            "interruptionReason",
        },
        "manifest",
    )
    if manifest["overallStatus"] not in ALLOWED_OVERALL_STATUSES:
        raise ManifestValidationError("overallStatus must be PASS, PASS_WITH_KNOWN_ISSUES, or FAIL")
    _parse_timestamp(manifest["startedAt"], "startedAt")
    _parse_timestamp(manifest["completedAt"], "completedAt")

    _validate_git(manifest["git"])
    _validate_environment(manifest["environment"])
    is_failure = manifest["overallStatus"] == "FAIL"
    _validate_configuration(manifest["configuration"], allow_empty_database=is_failure)
    _validate_contracts(manifest["contracts"], allow_empty=is_failure)
    _validate_test_records(manifest["tests"], allow_empty=is_failure)
    _validate_backup(manifest["backup"])
    _validate_fingerprint(manifest["sourceFingerprint"], "sourceFingerprint")
    _validate_restore(manifest["restore"])
    if is_failure:
        _require_nonempty_string(manifest["interruptionReason"], "interruptionReason")
    elif manifest["interruptionReason"] is not None and not isinstance(manifest["interruptionReason"], str):
        raise ManifestValidationError("interruptionReason must be a string or null")

    issue_ids = _validate_known_issue_ids(manifest["knownIssueIds"])
    manifest_issues = manifest.get("knownIssues")
    if manifest_issues is not None:
        manifest_issue_ids = validate_known_issues(manifest_issues)
        if issue_ids != manifest_issue_ids:
            raise ManifestValidationError("knownIssueIds must exactly match manifest knownIssues")
    if known_issues is not None:
        authoritative_issue_list = list(known_issues)
        authoritative_ids = validate_known_issues(authoritative_issue_list)
        if not issue_ids.issubset(authoritative_ids):
            raise ManifestValidationError("knownIssueIds must be declared by the authoritative known issues document")
        if manifest_issues is not None and _issues_by_id(manifest_issues) != _issues_by_id(authoritative_issue_list, ids=issue_ids):
            raise ManifestValidationError("manifest knownIssues must match the authoritative known issues document")
    if manifest_issues is None and known_issues is None and manifest["overallStatus"] == "PASS_WITH_KNOWN_ISSUES" and not issue_ids:
        raise ManifestValidationError("PASS_WITH_KNOWN_ISSUES requires knownIssueIds")
    _validate_overall_status(manifest["overallStatus"], manifest["tests"], issue_ids)


def validate_known_issues(known_issues: Iterable[Mapping[str, Any]]) -> set[str]:
    """Validate narrowly-scoped, expiring known issue records."""

    if isinstance(known_issues, (str, bytes)):
        raise ManifestValidationError("known issues must be a list")

    ids: set[str] = set()
    for index, issue in enumerate(known_issues):
        label = f"known issue {index}"
        _require_mapping(issue, label)
        _require_fields(
            issue,
            {
                "id",
                "kind",
                "scope",
                "matcher",
                "evidence",
                "reason",
                "disposition",
                "firstObservedAt",
                "expiresAt",
                "blocksNextPlan",
            },
            label,
        )
        issue_id = issue["id"]
        if not isinstance(issue_id, str) or not issue_id.strip() or issue_id in ids:
            raise ManifestValidationError(f"{label} id must be a unique non-empty string")
        ids.add(issue_id)
        _validate_issue_scope(issue["scope"], label)
        _validate_issue_matcher(issue["matcher"], label)
        _require_nonempty_string(issue["evidence"], f"{label} evidence")
        _require_nonempty_string(issue["reason"], f"{label} reason")
        _require_nonempty_string(issue["disposition"], f"{label} disposition")
        _parse_timestamp(issue["firstObservedAt"], f"{label} firstObservedAt")
        expires_at = _parse_timestamp(issue["expiresAt"], f"{label} expiresAt")
        if expires_at <= datetime.now(UTC):
            raise ManifestValidationError(f"{label} expiresAt must be in the future")
        if not isinstance(issue["blocksNextPlan"], bool):
            raise ManifestValidationError(f"{label} blocksNextPlan must be boolean")
    return ids


def classify_test_result(
    *,
    suite: str,
    command: str,
    exit_code: int,
    duration: float,
    stdout: str,
    stderr: str,
    known_issues: Iterable[Mapping[str, Any]],
    environment_error: str | None = None,
) -> dict[str, Any]:
    """Classify captured command output without silently accepting failures."""

    _require_nonempty_string(suite, "test suite")
    _require_nonempty_string(command, "test command")
    if not isinstance(exit_code, int):
        raise ManifestValidationError("test exit code must be an integer")
    if not isinstance(duration, (int, float)) or duration < 0:
        raise ManifestValidationError("test duration must be a non-negative number")
    if not isinstance(stdout, str) or not isinstance(stderr, str):
        raise ManifestValidationError("test stdout and stderr must be captured strings")
    if environment_error is not None:
        _require_nonempty_string(environment_error, "environment error")

    validated_issues = list(known_issues)
    validate_known_issues(validated_issues)
    matched_ids = [
        issue["id"]
        for issue in validated_issues
        if _known_issue_matches(issue, suite=suite, command=command, exit_code=exit_code, stdout=stdout, stderr=stderr)
    ]
    result = {
        "suite": suite,
        "command": command,
        "exitCode": exit_code,
        "duration": duration,
        "status": "ENVIRONMENT_ERROR" if environment_error else ("PASS" if exit_code == 0 else ("PASS_WITH_KNOWN_ISSUES" if matched_ids else "FAIL")),
        "stdout": stdout,
        "stderr": stderr,
        "knownIssueIds": matched_ids,
    }
    if environment_error:
        result["environmentError"] = environment_error
    return result


def validate_restore_database_name(target_database: str, *, source_database: str) -> None:
    """Allow only a generated, non-system database as a restore target."""

    if not isinstance(target_database, str) or not target_database:
        raise RestoreGuardrailError("restore database name is required")
    target_folded = target_database.casefold()
    if (
        target_folded == source_database.casefold()
        or target_folded in _SYSTEM_DATABASES
        or not target_folded.startswith(RESTORE_DATABASE_PREFIX)
        or len(target_database) == len(RESTORE_DATABASE_PREFIX)
        or len(target_database) > 63
    ):
        raise RestoreGuardrailError("restore database name is not an allowed isolated target")


def validate_restore_vault_target(target: Path, *, evidence_root: Path, active_vault: Path) -> None:
    """Ensure extraction happens only in a new directory inside this run's evidence."""

    root = evidence_root.resolve(strict=False)
    target_resolved = target.resolve(strict=False)
    active_resolved = active_vault.resolve(strict=False)
    if _is_relative_to(target_resolved, active_resolved) or _is_relative_to(active_resolved, target_resolved):
        raise RestoreGuardrailError("restore vault target must not be the active vault")
    if not _is_relative_to(target_resolved, root) or target_resolved == root:
        raise RestoreGuardrailError("restore vault target must be below the evidence root")
    _reject_symlinked_parent(target_resolved, root)
    if target.exists() and any(target.iterdir()):
        raise RestoreGuardrailError("restore vault target must be empty; non-empty directories are refused")


def validate_zip_members(members: Iterable[ZipInfo], *, destination: Path) -> None:
    """Reject ZIP members that could escape a recovery directory or create links."""

    root = destination.resolve(strict=False)
    seen_casefolded_paths: set[str] = set()
    for member in members:
        name = member.filename
        if not isinstance(name, str) or not name:
            raise RestoreGuardrailError("ZIP member has no path")
        posix = PurePosixPath(name)
        windows = PureWindowsPath(name)
        if posix.is_absolute() or windows.is_absolute() or windows.drive or ".." in posix.parts or ".." in windows.parts:
            raise RestoreGuardrailError("ZIP member path escapes the restore target")
        if _is_zip_link_or_reparse_point(member):
            raise RestoreGuardrailError("ZIP symbolic link or reparse point is not allowed")
        relative = Path(*posix.parts)
        target = (root / relative).resolve(strict=False)
        if not _is_relative_to(target, root):
            raise RestoreGuardrailError("ZIP member target would escape the restore directory")
        _reject_symlinked_parent(target, root)
        normalized = relative.as_posix().casefold()
        if normalized in seen_casefolded_paths:
            raise RestoreGuardrailError("ZIP contains path entries that collide on a case-insensitive filesystem")
        seen_casefolded_paths.add(normalized)


def _validate_git(value: Any) -> None:
    _require_mapping(value, "git")
    _require_fields(value, {"commit", "branch", "dirty"}, "git")
    _require_nonempty_string(value["commit"], "git.commit")
    _require_nonempty_string(value["branch"], "git.branch")
    if not isinstance(value["dirty"], bool):
        raise ManifestValidationError("git.dirty must be boolean")


def _validate_environment(value: Any) -> None:
    _require_mapping(value, "environment")
    _require_fields(value, {"os", "python", "node", "npm", "docker", "compose", "postgres"}, "environment")
    for key in ("os", "python", "node", "npm", "docker", "compose", "postgres"):
        _require_nonempty_string(value[key], f"environment.{key}")


def _validate_configuration(value: Any, *, allow_empty_database: bool = False) -> None:
    _require_mapping(value, "configuration")
    _require_fields(value, {"mode", "composeFile", "services", "database", "vaultSource"}, "configuration")
    for key in ("mode", "composeFile", "vaultSource"):
        _require_nonempty_string(value[key], f"configuration.{key}")
    if allow_empty_database:
        if not isinstance(value["database"], str):
            raise ManifestValidationError("configuration.database must be a string")
    else:
        _require_nonempty_string(value["database"], "configuration.database")
    if not isinstance(value["services"], list) or not value["services"] or not all(
        isinstance(service, str) and service for service in value["services"]
    ):
        raise ManifestValidationError("configuration.services must be a non-empty list of names")


def _validate_contracts(value: Any, *, allow_empty: bool = False) -> None:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ManifestValidationError("contracts must be a non-empty list")
    for index, contract in enumerate(value):
        label = f"contracts[{index}]"
        _require_mapping(contract, label)
        _require_fields(contract, {"name", "path", "sha256", "status"}, label)
        _require_nonempty_string(contract["name"], f"{label}.name")
        _validate_evidence_path(contract["path"], f"{label}.path")
        _validate_sha256(contract["sha256"], f"{label}.sha256")
        if contract["status"] not in ALLOWED_OVERALL_STATUSES:
            raise ManifestValidationError(f"{label}.status is invalid")


def _validate_test_records(value: Any, *, allow_empty: bool = False) -> None:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ManifestValidationError("tests must be a non-empty list")
    required = {"suite", "command", "exitCode", "duration", "status", "stdout", "stderr", "knownIssueIds"}
    for index, test in enumerate(value):
        label = f"tests[{index}]"
        _require_mapping(test, label)
        _require_fields(test, required, label)
        _require_nonempty_string(test["suite"], f"{label}.suite")
        _require_nonempty_string(test["command"], f"{label}.command")
        if not isinstance(test["exitCode"], int):
            raise ManifestValidationError(f"{label}.exitCode must be an integer")
        if not isinstance(test["duration"], (int, float)) or test["duration"] < 0:
            raise ManifestValidationError(f"{label}.duration must be a non-negative number")
        if test["status"] not in ALLOWED_TEST_STATUSES:
            raise ManifestValidationError(f"{label}.status is invalid")
        _validate_evidence_path(test["stdout"], f"{label}.stdout")
        _validate_evidence_path(test["stderr"], f"{label}.stderr")
        _validate_known_issue_ids(test["knownIssueIds"])


def _validate_overall_status(overall_status: str, tests: list[Any], known_issue_ids: set[str]) -> None:
    test_statuses = {test["status"] for test in tests}
    matched_issue_ids = {issue_id for test in tests for issue_id in test["knownIssueIds"]}
    if not matched_issue_ids.issubset(known_issue_ids):
        raise ManifestValidationError("knownIssueIds must include every matched test issue")
    if overall_status == "PASS":
        if known_issue_ids or "PASS_WITH_KNOWN_ISSUES" in test_statuses:
            raise ManifestValidationError("PASS cannot include known issues")
        if test_statuses & {"FAIL", "ENVIRONMENT_ERROR"}:
            raise ManifestValidationError("PASS cannot include unresolved test evidence")
    if overall_status == "PASS_WITH_KNOWN_ISSUES":
        if test_statuses & {"FAIL", "ENVIRONMENT_ERROR"}:
            raise ManifestValidationError("PASS_WITH_KNOWN_ISSUES cannot include unresolved test evidence")
        if not known_issue_ids or "PASS_WITH_KNOWN_ISSUES" not in test_statuses:
            raise ManifestValidationError("PASS_WITH_KNOWN_ISSUES requires matched known-issue test evidence")


def _validate_backup(value: Any) -> None:
    _require_mapping(value, "backup")
    _require_fields(value, {"database", "vault"}, "backup")
    database = value["database"]
    vault = value["vault"]
    _require_mapping(database, "backup.database")
    _require_fields(database, {"path", "format", "sha256"}, "backup.database")
    _validate_evidence_path(database["path"], "backup.database.path")
    _require_nonempty_string(database["format"], "backup.database.format")
    _validate_sha256(database["sha256"], "backup.database.sha256")
    _require_mapping(vault, "backup.vault")
    _require_fields(vault, {"path", "fileCount", "sha256"}, "backup.vault")
    _validate_evidence_path(vault["path"], "backup.vault.path")
    if not isinstance(vault["fileCount"], int) or vault["fileCount"] < 0:
        raise ManifestValidationError("backup.vault.fileCount must be a non-negative integer")
    _validate_sha256(vault["sha256"], "backup.vault.sha256")


def _validate_fingerprint(value: Any, label: str) -> None:
    _require_mapping(value, label)
    _require_fields(value, {"path", "sha256"}, label)
    _validate_evidence_path(value["path"], f"{label}.path")
    _validate_sha256(value["sha256"], f"{label}.sha256")


def _validate_restore(value: Any) -> None:
    _require_mapping(value, "restore")
    _require_fields(value, {"targetDatabase", "targetVault", "status", "cleanupStatus", "reportPath"}, "restore")
    validate_restore_database_name(value["targetDatabase"], source_database="__active_database_unknown__")
    _validate_evidence_path(value["targetVault"], "restore.targetVault")
    if value["status"] not in ALLOWED_OVERALL_STATUSES:
        raise ManifestValidationError("restore.status is invalid")
    _require_nonempty_string(value["cleanupStatus"], "restore.cleanupStatus")
    _validate_evidence_path(value["reportPath"], "restore.reportPath")


def _validate_known_issue_ids(value: Any) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(issue_id, str) and issue_id for issue_id in value):
        raise ManifestValidationError("knownIssueIds must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise ManifestValidationError("knownIssueIds must not contain duplicates")
    return set(value)


def _issues_by_id(issues: Iterable[Mapping[str, Any]], *, ids: set[str] | None = None) -> dict[str, Mapping[str, Any]]:
    return {
        issue["id"]: issue
        for issue in issues
        if ids is None or issue["id"] in ids
    }


def _validate_issue_scope(value: Any, label: str) -> None:
    _require_mapping(value, f"{label} scope")
    if not value:
        raise ManifestValidationError(f"{label} scope must name a bounded target")
    for key, part in value.items():
        _require_nonempty_string(key, f"{label} scope key")
        _require_nonempty_string(part, f"{label} scope.{key}")
        if part.casefold() in {"all", "all tests", "*"}:
            raise ManifestValidationError(f"{label} scope must not whitelist an entire suite")


def _validate_issue_matcher(value: Any, label: str) -> None:
    _require_mapping(value, f"{label} matcher")
    allowed_keys = {"exitCode", "stdoutContains", "stderrContains"}
    if not value or set(value) - allowed_keys:
        raise ManifestValidationError(f"{label} matcher must use exact supported fields")
    if "exitCode" in value and (not isinstance(value["exitCode"], int) or value["exitCode"] < 1):
        raise ManifestValidationError(f"{label} matcher.exitCode must be a non-zero integer")
    for key in ("stdoutContains", "stderrContains"):
        if key in value:
            _require_nonempty_string(value[key], f"{label} matcher.{key}")
            if value[key].strip() in {".*", "*"}:
                raise ManifestValidationError(f"{label} matcher must not use fuzzy regular expressions")


def _known_issue_matches(
    issue: Mapping[str, Any], *, suite: str, command: str, exit_code: int, stdout: str, stderr: str
) -> bool:
    scope = issue["scope"]
    matcher = issue["matcher"]
    if scope.get("suite") != suite or scope.get("command") != command:
        return False
    if "exitCode" in matcher and matcher["exitCode"] != exit_code:
        return False
    if "stdoutContains" in matcher and matcher["stdoutContains"] not in stdout:
        return False
    return "stderrContains" not in matcher or matcher["stderrContains"] in stderr


def _validate_evidence_path(value: Any, label: str) -> None:
    _require_nonempty_string(value, label)
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if posix.is_absolute() or windows.is_absolute() or windows.drive or ".." in posix.parts or ".." in windows.parts:
        raise ManifestValidationError(f"{label} must be a relative evidence path")


def _validate_sha256(value: Any, label: str) -> None:
    if not isinstance(value, str) or len(value) != _SHA256_LENGTH or any(char not in "0123456789abcdef" for char in value):
        raise ManifestValidationError(f"{label} must be a lowercase SHA-256 checksum")


def _require_local_evidence_root(evidence_root: Path) -> None:
    if ".local" not in {part.casefold() for part in evidence_root.parts}:
        raise ManifestValidationError("evidence_root must be inside the repository .local directory")


def _require_mapping(value: Any, label: str) -> None:
    if not isinstance(value, Mapping):
        raise ManifestValidationError(f"{label} must be an object")


def _require_fields(value: Mapping[str, Any], fields: set[str], label: str) -> None:
    missing = sorted(field for field in fields if field not in value)
    if missing:
        raise ManifestValidationError(f"{label} is missing required fields: {', '.join(missing)}")


def _require_nonempty_string(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{label} must be a non-empty string")


def _parse_timestamp(value: Any, label: str) -> datetime:
    _require_nonempty_string(value, label)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ManifestValidationError(f"{label} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ManifestValidationError(f"{label} must include a timezone")
    return parsed.astimezone(UTC)


def _is_zip_link_or_reparse_point(member: ZipInfo) -> bool:
    unix_mode = (member.external_attr >> 16) & 0xFFFF
    is_unix_link = stat.S_ISLNK(unix_mode)
    has_windows_reparse_point = member.create_system == 0 and bool(member.external_attr & 0x0400)
    return is_unix_link or has_windows_reparse_point


def _reject_symlinked_parent(target: Path, root: Path) -> None:
    current = root
    relative_parts = target.relative_to(root).parts
    for part in relative_parts[:-1]:
        current = current / part
        if current.exists() and current.is_symlink():
            raise RestoreGuardrailError("restore target traverses an existing symbolic link or reparse point")


def _is_relative_to(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return True


def _json_default(value: Any) -> str:
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return str(value)


def _normalize_fingerprint_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _normalize_fingerprint_value(child) for key, child in value.items()}
    if isinstance(value, list | tuple):
        return [_normalize_fingerprint_value(child) for child in value]
    if isinstance(value, bytes):
        return {"$bytes": value.hex()}
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, Path):
        return value.as_posix()
    return value
