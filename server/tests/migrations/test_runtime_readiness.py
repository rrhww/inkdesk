from __future__ import annotations

import pytest


def test_init_db_rejects_empty_database_without_creating_tables(raw_temp_app_env):
    from inkdesk_server.db import get_engine, init_db
    from inkdesk_server.db_migrations import DatabaseReadinessError

    with pytest.raises(DatabaseReadinessError, match="DB_REVISION_BEHIND"):
        init_db()

    assert get_engine().dialect.has_table(get_engine().connect(), "users") is False


def test_init_db_accepts_database_at_alembic_head(raw_temp_app_env, capsys):
    from inkdesk_server.db import init_db
    from inkdesk_server.db_migrations import main

    assert main(["upgrade"]) == 0
    capsys.readouterr()

    init_db()
