"""
Skill Registry — recursive discovery, resolution, metadata, and status reporting.

Registry only reads and reports metadata/validation — it does NOT execute Skills.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from inkdesk_skill_sdk.contracts import REQUIRED_FILES, Contract, SkillStatus
from inkdesk_skill_sdk.validation import (
    ValidationResult,
    validate_safety,
    validate_semantic,
    validate_structural,
)


@dataclass(frozen=True, slots=True)
class SkillMetadata:
    """Lightweight registry entry for one Skill package."""

    name: str
    path: str
    contract_id: str
    version: str
    status: SkillStatus
    category: str
    kind: str
    summary: str
    validation_result: ValidationResult | None


class SkillRegistry:
    """Discovers and indexes Skill packages under one or more roots."""

    def __init__(self, roots: list[Path] | None = None):
        self._roots: list[Path] = [Path(r).resolve() for r in roots] if roots else []

    def add_root(self, root: Path) -> None:
        self._roots.append(Path(root).resolve())

    def discover(self) -> list[Path]:
        """Find all directories that look like Skill packages (have SKILL.md + contract.json)."""
        packages: list[Path] = []
        seen: set[str] = set()

        for root in self._roots:
            if not root.is_dir():
                continue
            for entry in sorted(root.iterdir()):
                if not entry.is_dir():
                    continue
                if entry.name.startswith(".") or entry.name.startswith("_"):
                    continue
                rp = str(entry.resolve())
                if rp in seen:
                    continue
                # Check if it has the required files
                if all((entry / f).is_file() for f in REQUIRED_FILES):
                    packages.append(entry)
                    seen.add(rp)

        return packages

    def resolve(self, package_path: Path) -> SkillMetadata | None:
        """Parse one package and return metadata, or None if unparseable."""
        package_path = package_path.resolve()
        name = package_path.name

        contract = self._load_contract(package_path)
        if contract is None:
            return None

        # Run validation
        try:
            findings = (
                validate_structural(package_path)
                + validate_semantic(package_path)
                + validate_safety(package_path)
            )
            result = ValidationResult(
                package_name=name,
                findings=tuple(findings),
                passed=all(f.severity.value != "error" for f in findings),
            )
        except Exception:
            result = None

        return SkillMetadata(
            name=name,
            path=str(package_path),
            contract_id=contract.id,
            version=contract.version,
            status=contract.status,
            category=contract.category.value,
            kind=contract.kind.value,
            summary=contract.summary,
            validation_result=result,
        )

    def resolve_all(self) -> list[SkillMetadata]:
        """Discover and resolve all packages across all roots."""
        result: list[SkillMetadata] = []
        for pkg_path in self.discover():
            meta = self.resolve(pkg_path)
            if meta is not None:
                result.append(meta)
        return result

    def get_summary(self) -> dict[str, Any]:
        """Return a registry-wide summary consumable by /app/skills."""
        all_meta = self.resolve_all()
        valid = [m for m in all_meta if m.validation_result and m.validation_result.passed]
        invalid = [m for m in all_meta if m.validation_result and not m.validation_result.passed]
        drafts = [m for m in all_meta if m.status == SkillStatus.DRAFT]
        actives = [m for m in all_meta if m.status == SkillStatus.ACTIVE]
        deprecated = [m for m in all_meta if m.status == SkillStatus.DEPRECATED]

        return {
            "total": len(all_meta),
            "valid": len(valid),
            "invalid": len(invalid),
            "byStatus": {
                "draft": len(drafts),
                "active": len(actives),
                "deprecated": len(deprecated),
            },
            "skills": [
                {
                    "name": m.name,
                    "contractId": m.contract_id,
                    "version": m.version,
                    "status": m.status.value,
                    "category": m.category,
                    "kind": m.kind,
                    "summary": m.summary,
                    "valid": m.validation_result.passed if m.validation_result else False,
                }
                for m in all_meta
            ],
        }

    @staticmethod
    def _load_contract(package_path: Path) -> Contract | None:
        contract_path = package_path / "contract.json"
        if not contract_path.is_file():
            return None
        try:
            data = json.loads(contract_path.read_text(encoding="utf-8"))
            return Contract.model_validate(data)
        except Exception:
            return None
