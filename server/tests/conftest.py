from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture()
def temp_app_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    try:
        from inkdesk_server.core.config import get_settings
        from inkdesk_server.db import get_engine, get_session_factory

        get_settings.cache_clear()
        get_engine.cache_clear()
        get_session_factory.cache_clear()
    except Exception:
        pass

    db_path = tmp_path / "inkdesk-test.db"
    vault_root = tmp_path / "vault"
    monkeypatch.setenv("INKDESK_DB_URL", f"sqlite+pysqlite:///{db_path}")
    monkeypatch.setenv("INKDESK_VAULT_ROOT", str(vault_root))
    monkeypatch.setenv("INKDESK_AUTH_SECRET", "test-owner-session-secret")
    monkeypatch.setenv("INKDESK_AUTH_ALLOW_LEGACY_OWNER_COOKIE", "true")
    monkeypatch.setenv("INKDESK_AGENT_RUNTIME", "deterministic")
    monkeypatch.setenv("INKDESK_ENABLE_WEB_ASSIST", "false")
    monkeypatch.setenv("INKDESK_ENABLE_LOCAL_SEED", "false")
    yield vault_root
