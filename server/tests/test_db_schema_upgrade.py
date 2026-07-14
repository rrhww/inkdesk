from __future__ import annotations

from sqlalchemy import inspect, text


def test_init_db_only_checks_an_alembic_managed_database(temp_app_env):
    from inkdesk_server.db import get_engine, init_db

    engine = get_engine()
    before_tables = inspect(engine).get_table_names()
    with engine.connect() as connection:
        before_revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    init_db()

    assert inspect(engine).get_table_names() == before_tables
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == before_revision
