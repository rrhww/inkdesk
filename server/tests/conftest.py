from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture()
def temp_app_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    try:
        from inkdesk_server.core.config import get_settings

        get_settings.cache_clear()
    except Exception:
        pass

    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    monkeypatch.setenv("INKDESK_VAULT_ROOT", str(vault_root))
    monkeypatch.setenv("INKDESK_AGENT_RUNTIME", "deterministic")
    monkeypatch.setenv("INKDESK_AGENT_PROVIDER_PROFILE", "openai")
    monkeypatch.setenv("INKDESK_AGENT_MODEL", "")
    monkeypatch.setenv("INKDESK_AGENT_API_KEY", "")
    monkeypatch.setenv("INKDESK_AGENT_BASE_URL", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_BASE_URL", "")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("INKDESK_ENABLE_FILE_WATCHER", "false")
    yield vault_root
