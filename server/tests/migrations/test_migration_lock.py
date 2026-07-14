from __future__ import annotations

import json

from sqlalchemy import inspect, text


def test_postgres_upgrade_times_out_while_another_migration_holds_lock(
    temporary_postgres_app_env, monkeypatch, capsys
):
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.db import get_engine
    from inkdesk_server.db_migrations import MIGRATION_LOCK_KEY, main

    monkeypatch.setenv("INKDESK_MIGRATION_LOCK_TIMEOUT_SECONDS", "0")
    get_settings.cache_clear()
    engine = get_engine()
    with engine.connect() as lock_connection:
        lock_connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": MIGRATION_LOCK_KEY})
        assert main(["upgrade"]) == 1
        result = json.loads(capsys.readouterr().out.strip())
        assert result["code"] == "DB_MIGRATION_LOCK_TIMEOUT"
        assert "alembic_version" not in inspect(engine).get_table_names()
        lock_connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK_KEY})
