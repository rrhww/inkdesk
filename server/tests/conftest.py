from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture()
def temp_app_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    try:
        from inkvault_server.core.config import get_settings
        from inkvault_server.db import get_engine, get_session_factory

        get_settings.cache_clear()
        get_engine.cache_clear()
        get_session_factory.cache_clear()
    except Exception:
        pass

    db_path = tmp_path / "inkvault-test.db"
    vault_root = tmp_path / "vault"
    monkeypatch.setenv("INKVAULT_DB_URL", f"sqlite+pysqlite:///{db_path}")
    monkeypatch.setenv("INKVAULT_VAULT_ROOT", str(vault_root))
    monkeypatch.setenv("INKVAULT_AUTH_SECRET", "test-owner-session-secret")
    monkeypatch.setenv("INKVAULT_AUTH_ALLOW_LEGACY_OWNER_COOKIE", "true")
    monkeypatch.setenv("INKVAULT_AGENT_RUNTIME", "deterministic")
    monkeypatch.setenv("INKVAULT_ENABLE_WEB_ASSIST", "false")
    monkeypatch.setenv("INKVAULT_ENABLE_LOCAL_SEED", "false")
    yield vault_root
