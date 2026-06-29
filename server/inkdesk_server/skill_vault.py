"""
Vault-level I/O for Skill packages.

Thin wrapper around VaultService for skill/ directory access.
All path safety delegated to VaultService.
"""

from __future__ import annotations

from pathlib import Path

from inkdesk_server.vault import VaultService


class SkillVault:
    """Safe read/write for skill packages within the vault."""

    def __init__(self, vault_service: VaultService):
        self._vault = vault_service
        self._skills_root = vault_service.resolve("skills")

    @property
    def skills_root(self) -> Path:
        return self._skills_root

    def list_packages(self) -> list[str]:
        """List all skill package directory names."""
        root = self._skills_root
        if not root.is_dir():
            return []
        return sorted(
            d.name
            for d in root.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    def package_exists(self, name: str) -> bool:
        return (self._skills_root / name).is_dir()

    def read_file(self, package_name: str, relative_path: str) -> str:
        """Read a file from within a skill package."""
        full_rel = f"skills/{package_name}/{relative_path}"
        return self._vault.read_vault_file(full_rel)

    def write_file(self, package_name: str, relative_path: str, content: str) -> None:
        """Write a file into a skill package."""
        full_rel = f"skills/{package_name}/{relative_path}"
        self._vault.write_vault_file(full_rel, content)
