from __future__ import annotations

import pytest
from alembic import command
from sqlalchemy import inspect, text


def _revision(engine) -> str:
    with engine.connect() as connection:
        return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def test_upgrade_builds_empty_sqlite_database_and_is_repeatable(raw_temp_app_env, capsys):
    from inkdesk_server import models  # noqa: F401
    from inkdesk_server.db import Base, get_engine
    from inkdesk_server.db_migrations import HEAD_REVISION, main

    engine = get_engine()
    assert main(["upgrade"]) == 0
    capsys.readouterr()

    tables = set(inspect(engine).get_table_names())
    assert tables == set(Base.metadata.tables) | {"alembic_version"}
    assert _revision(engine) == HEAD_REVISION

    assert main(["upgrade"]) == 0
    capsys.readouterr()
    assert _revision(engine) == HEAD_REVISION


def test_baseline_downgrade_is_refused_without_dropping_schema(raw_temp_app_env, capsys):
    from inkdesk_server.db import get_engine
    from inkdesk_server.db_migrations import HEAD_REVISION, _alembic_config, main

    engine = get_engine()
    assert main(["upgrade"]) == 0
    capsys.readouterr()

    with pytest.raises(RuntimeError, match="irreversible"):
        command.downgrade(_alembic_config(), "base")

    assert _revision(engine) == HEAD_REVISION
    assert "users" in inspect(engine).get_table_names()
