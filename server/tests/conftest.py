from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url


def _clear_database_caches() -> None:
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.db import get_engine, get_session_factory

    get_engine().dispose()
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


@pytest.fixture()
def raw_temp_app_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
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
    monkeypatch.setenv("INKDESK_AGENT_RUNTIME", "deterministic")
    monkeypatch.setenv("INKDESK_AGENT_PROVIDER_PROFILE", "openai")
    monkeypatch.setenv("INKDESK_AGENT_MODEL", "")
    monkeypatch.setenv("INKDESK_AGENT_API_KEY", "")
    monkeypatch.setenv("INKDESK_AGENT_BASE_URL", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_BASE_URL", "")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("INKDESK_EMBEDDING_PROVIDER_PROFILE", "openai")
    monkeypatch.setenv("INKDESK_EMBEDDING_MODEL", "")
    monkeypatch.setenv("INKDESK_EMBEDDING_API_KEY", "")
    monkeypatch.setenv("INKDESK_EMBEDDING_BASE_URL", "")
    monkeypatch.setenv("INKDESK_ENABLE_WEB_ASSIST", "false")
    monkeypatch.setenv("INKDESK_ENABLE_LOCAL_SEED", "false")
    yield vault_root


@pytest.fixture()
def temp_app_env(raw_temp_app_env: Path) -> Iterator[Path]:
    from inkdesk_server.db_migrations import main

    assert main(["upgrade"]) == 0
    yield raw_temp_app_env


@pytest.fixture()
def temporary_postgres_app_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[URL]:
    configured_url = os.getenv("INKDESK_TEST_PGVECTOR_URL")
    if not configured_url:
        pytest.skip("Set INKDESK_TEST_PGVECTOR_URL to run PostgreSQL migration tests.")

    source_url = make_url(configured_url)
    database_name = f"inkdesk_f02_test_{uuid.uuid4().hex}"
    database_url = source_url.set(database=database_name)
    admin_url = source_url.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
        monkeypatch.setenv("INKDESK_DB_URL", database_url.render_as_string(hide_password=False))
        _clear_database_caches()
        yield database_url
    finally:
        _clear_database_caches()
        with admin_engine.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)'))
        admin_engine.dispose()
