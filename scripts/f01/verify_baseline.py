"""Verify F01 evidence completeness, hashes, and known-issue discipline."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from baseline_contracts import ManifestValidationError, sha256_file, validate_manifest


class EvidenceVerificationError(ValueError):
    """Evidence references a missing, escaping, or altered artifact."""


def verify_evidence_tree(
    manifest: Mapping[str, Any], *, evidence_root: Path, known_issues: Iterable[Mapping[str, Any]] | None = None
) -> None:
    """Validate the manifest and verify all referenced local artifact paths and hashes."""

    try:
        validate_manifest(manifest, evidence_root=evidence_root, known_issues=known_issues)
    except ManifestValidationError as error:
        raise EvidenceVerificationError(str(error)) from error
    root = evidence_root.resolve(strict=False)
    for relative_path, expected_sha256 in _hashed_artifacts(manifest):
        actual_path = _resolve_artifact(root, relative_path)
        if not actual_path.is_file():
            raise EvidenceVerificationError(f"missing evidence artifact: {relative_path}")
        if sha256_file(actual_path) != expected_sha256:
            raise EvidenceVerificationError(f"checksum mismatch for evidence artifact: {relative_path}")
    for relative_path in _unhashed_artifacts(manifest):
        actual_path = _resolve_artifact(root, relative_path)
        if not actual_path.is_file():
            raise EvidenceVerificationError(f"missing evidence artifact: {relative_path}")


def load_json_document(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise EvidenceVerificationError(f"required JSON document is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise EvidenceVerificationError(f"invalid JSON document: {path}") from error


def _hashed_artifacts(manifest: Mapping[str, Any]) -> list[tuple[str, str]]:
    artifacts = [(contract["path"], contract["sha256"]) for contract in manifest["contracts"]]
    artifacts.extend(
        [
            (manifest["backup"]["database"]["path"], manifest["backup"]["database"]["sha256"]),
            (manifest["backup"]["vault"]["path"], manifest["backup"]["vault"]["sha256"]),
            (manifest["sourceFingerprint"]["path"], manifest["sourceFingerprint"]["sha256"]),
        ]
    )
    return artifacts


def _unhashed_artifacts(manifest: Mapping[str, Any]) -> list[str]:
    artifacts = [test["stdout"] for test in manifest["tests"]]
    artifacts.extend(test["stderr"] for test in manifest["tests"])
    artifacts.append(manifest["restore"]["reportPath"])
    return artifacts


def _resolve_artifact(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise EvidenceVerificationError(f"evidence path escapes run directory: {relative_path}") from error
    return candidate


def _load_known_issue_list(path: Path | None) -> list[Mapping[str, Any]] | None:
    if path is None:
        return None
    document = load_json_document(path)
    if isinstance(document, list):
        return document
    if isinstance(document, Mapping) and isinstance(document.get("issues"), list):
        return document["issues"]
    raise EvidenceVerificationError("known issues document must be a list or an object with an issues list")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--known-issues", type=Path)
    arguments = parser.parse_args(argv)
    manifest = load_json_document(arguments.manifest)
    if not isinstance(manifest, Mapping):
        print("manifest must be a JSON object", file=sys.stderr)
        return 1
    try:
        verify_evidence_tree(
            manifest,
            evidence_root=arguments.evidence_root,
            known_issues=_load_known_issue_list(arguments.known_issues),
        )
    except EvidenceVerificationError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
