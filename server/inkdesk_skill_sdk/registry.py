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

from inkdesk_skill_sdk.capabilities import (
    CapabilityManifest,
    PackageFormat,
    load_skill_package,
    parse_skill_frontmatter,
)
from inkdesk_skill_sdk.contracts import Contract, SkillStatus
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
    package_format: PackageFormat = PackageFormat.LEGACY_CONTRACT
    executable: bool = True
    capability: CapabilityManifest | None = None


class SkillRegistry:
    """Discovers and indexes Skill packages under one or more roots."""

    def __init__(self, roots: list[Path] | None = None):
        self._roots: list[Path] = [Path(r).resolve() for r in roots] if roots else []

    def add_root(self, root: Path) -> None:
        self._roots.append(Path(root).resolve())

    def discover(self) -> list[Path]:
        """Find all direct child directories containing an Agent Skills SKILL.md."""
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
                if (entry / "SKILL.md").is_file():
                    packages.append(entry)
                    seen.add(rp)

        return packages

    def resolve(self, package_path: Path) -> SkillMetadata | None:
        """Parse one package and return metadata, or None if unparseable."""
        package_path = package_path.resolve()
        name = package_path.name

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

        try:
            package = load_skill_package(package_path, warn_legacy=False)
        except Exception:
            return self._invalid_metadata(package_path, result)

        return SkillMetadata(
            name=name,
            path=str(package_path),
            contract_id=package.frontmatter.name,
            version=package.capability.version if package.capability else "0.0.0",
            status=package.capability.status if package.capability else SkillStatus.DRAFT,
            category=(
                package.legacy_contract.category.value
                if package.legacy_contract
                else "capability" if package.executable else "external"
            ),
            kind=(
                package.legacy_contract.kind.value
                if package.legacy_contract
                else "workflow" if package.executable else "instruction"
            ),
            summary=package.frontmatter.description,
            validation_result=result,
            package_format=package.package_format,
            executable=package.executable,
            capability=package.capability,
        )

    @staticmethod
    def _invalid_metadata(
        package_path: Path,
        validation_result: ValidationResult | None,
    ) -> SkillMetadata | None:
        try:
            frontmatter = parse_skill_frontmatter(package_path / "SKILL.md")
        except Exception:
            return None

        contract: Contract | None = None
        capability: CapabilityManifest | None = None
        try:
            if (package_path / "contract.json").is_file():
                contract = Contract.model_validate(
                    json.loads((package_path / "contract.json").read_text(encoding="utf-8"))
                )
            elif (package_path / "inkdesk.yaml").is_file():
                capability = CapabilityManifest.model_validate(
                    yaml.safe_load((package_path / "inkdesk.yaml").read_text(encoding="utf-8"))
                )
        except Exception:
            pass

        return SkillMetadata(
            name=package_path.name,
            path=str(package_path),
            contract_id=contract.id if contract else capability.id if capability else frontmatter.name,
            version=contract.version if contract else capability.version if capability else "0.0.0",
            status=contract.status if contract else capability.status if capability else SkillStatus.DRAFT,
            category=contract.category.value if contract else "capability" if capability else "external",
            kind=contract.kind.value if contract else "workflow" if capability else "instruction",
            summary=contract.summary if contract else frontmatter.description,
            validation_result=validation_result,
            package_format=(
                PackageFormat.LEGACY_CONTRACT
                if contract
                else PackageFormat.CAPABILITY if capability else PackageFormat.AGENT_SKILL
            ),
            executable=contract is not None or capability is not None,
            capability=capability,
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
                    "format": m.package_format.value,
                    "executable": m.executable,
                }
                for m in all_meta
            ],
        }
