from __future__ import annotations

from pathlib import Path

import pytest


def test_vault_service_initializes_raw_wiki_and_agents_file(temp_app_env: Path):
    from inkvault_server.core.config import get_settings
    from inkvault_server.vault import VaultService

    service = VaultService(get_settings())
    service.ensure_initialized()

    assert (temp_app_env / "raw").is_dir()
    assert (temp_app_env / "wiki").is_dir()
    assert "raw -> ingest -> wiki" in (temp_app_env / "AGENTS.md").read_text(encoding="utf-8")


def test_vault_service_rejects_path_traversal(temp_app_env: Path):
    from inkvault_server.core.config import get_settings
    from inkvault_server.vault import VaultService

    service = VaultService(get_settings())
    service.ensure_initialized()

    with pytest.raises(ValueError):
        service.write_vault_file("../outside.md", "bad")

    assert not temp_app_env.parent.joinpath("outside.md").exists()
