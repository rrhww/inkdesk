from __future__ import annotations

import json

from sqlalchemy import inspect, text


def _read_output(capsys) -> dict[str, object]:
    return json.loads(capsys.readouterr().out.strip())


def _build_unmanaged_f01_database(engine) -> None:
    from inkdesk_server import models  # noqa: F401
    from inkdesk_server.db import Base

    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users (id, username, email, password_hash, status, created_at, updated_at)
                VALUES ('user-1', 'owner', 'owner@example.test', 'hash', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO workspaces (id, owner_user_id, name, slug, created_at, updated_at)
                VALUES ('workspace-1', 'user-1', 'Workspace', 'workspace', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
        )


def test_upgrade_adopts_exact_f01_postgres_schema_without_changing_data(temporary_postgres_app_env, capsys):
    from inkdesk_server.db import get_engine
    from inkdesk_server.db_migrations import HEAD_REVISION, main
    from inkdesk_server.schema_contract import (
        F01_COMPATIBILITY_DIGEST,
        application_schema_digest,
        table_data_fingerprints,
    )

    engine = get_engine()
    _build_unmanaged_f01_database(engine)
    before_schema = application_schema_digest(engine)
    before_data = table_data_fingerprints(engine)
    assert before_schema == F01_COMPATIBILITY_DIGEST

    assert main(["status"]) == 0
    assert _read_output(capsys)["state"] == "F01_CURRENT_UNMANAGED"

    assert main(["upgrade"]) == 0
    capsys.readouterr()

    assert application_schema_digest(engine, exclude_tables={"alembic_version"}) == before_schema
    assert table_data_fingerprints(engine, exclude_tables={"alembic_version"}) == before_data
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD_REVISION

    assert main(["upgrade"]) == 0
    capsys.readouterr()


def test_upgrade_rejects_f01_schema_drift_without_stamping(temporary_postgres_app_env, capsys):
    from inkdesk_server.db import get_engine
    from inkdesk_server.db_migrations import main

    engine = get_engine()
    _build_unmanaged_f01_database(engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ALTER COLUMN username TYPE TEXT"))

    assert main(["upgrade"]) == 1
    result = _read_output(capsys)
    assert result["code"] == "DB_SCHEMA_UNSUPPORTED"
    assert "alembic_version" not in inspect(engine).get_table_names()
