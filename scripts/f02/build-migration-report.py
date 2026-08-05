"""Build a sanitized F02 migration verification manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def build_migration_report(
    *, run_id: str, f01_manifest: Path, checks: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    f01 = _load_json(f01_manifest)
    if f01.get("overallStatus") != "PASS":
        raise ValueError("F01 evidence manifest must have overallStatus PASS")
    if not isinstance(f01.get("runId"), str) or not f01["runId"]:
        raise ValueError("F01 evidence manifest must include a runId")

    normalized_checks = [_normalize_check(check) for check in checks]
    return {
        "schemaVersion": "1.0",
        "runId": run_id,
        "overallStatus": "PASS" if all(check["status"] == "PASS" for check in normalized_checks) else "FAIL",
        "f01": {"runId": f01["runId"], "manifestSha256": _sha256_file(f01_manifest)},
        "checks": normalized_checks,
    }


def _normalize_check(check: Mapping[str, Any]) -> dict[str, Any]:
    name = check.get("name")
    status = check.get("status")
    artifacts = check.get("artifacts", [])
    if not isinstance(name, str) or not name:
        raise ValueError("F02 check name must be a non-empty string")
    if status not in {"PASS", "FAIL"}:
        raise ValueError(f"F02 check {name!r} has an invalid status")
    if not isinstance(artifacts, Sequence) or isinstance(artifacts, (str, bytes)):
        raise ValueError(f"F02 check {name!r} artifacts must be a list")
    normalized_artifacts = []
    for artifact in artifacts:
        path = Path(artifact)
        if not path.is_file():
            raise ValueError(f"F02 artifact does not exist: {path.name}")
        normalized_artifacts.append({"name": path.name, "sha256": _sha256_file(path)})
    return {"name": name, "status": status, "artifacts": normalized_artifacts}


def _load_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError("F01 evidence manifest is missing") from error
    except json.JSONDecodeError as error:
        raise ValueError("F01 evidence manifest is invalid JSON") from error
    if not isinstance(value, Mapping):
        raise ValueError("F01 evidence manifest must be a JSON object")
    return value


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--f01-manifest", type=Path, required=True)
    parser.add_argument("--checks", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    checks_document = _load_json(arguments.checks)
    checks = checks_document.get("checks") if isinstance(checks_document, Mapping) else None
    if not isinstance(checks, list):
        raise ValueError("checks document must contain a checks list")
    report = build_migration_report(run_id=arguments.run_id, f01_manifest=arguments.f01_manifest, checks=checks)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
