from __future__ import annotations

import json

from sqlalchemy import inspect, text


def _read_status(capsys) -> dict[str, object]:
    output = capsys.readouterr().out.strip()
    return json.loads(output)


def test_status_reports_empty_sqlite_database(raw_temp_app_env, capsys):
    from inkdesk_server.db_migrations import main

    assert main(["status"]) == 0

    status = _read_status(capsys)
    assert status["state"] == "EMPTY"
    assert status["currentRevision"] is None
    assert status["headRevision"] == "f05_0003"
    assert status["requiredAction"] == "upgrade"


def test_upgrade_rejects_partial_schema_without_creating_version_table(raw_temp_app_env, capsys):
    from inkdesk_server.db import get_engine
    from inkdesk_server.db_migrations import main

    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE partial_table (id INTEGER PRIMARY KEY)"))

    assert main(["upgrade"]) == 1

    result = _read_status(capsys)
    assert result["code"] == "DB_SCHEMA_UNSUPPORTED"
    assert result["dialect"] == "sqlite"
    assert "alembic_version" not in inspect(engine).get_table_names()


def test_upgrade_rejects_unknown_revision_without_mutating_database(raw_temp_app_env, capsys):
    from inkdesk_server.db import get_engine
    from inkdesk_server.db_migrations import main

    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version (version_num) VALUES ('unknown_revision')"))

    assert main(["upgrade"]) == 1

    result = _read_status(capsys)
    assert result["code"] == "DB_REVISION_UNKNOWN"
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "unknown_revision"


def test_check_rejects_managed_sqlite_schema_drift(raw_temp_app_env, capsys):
    from inkdesk_server.db import get_engine
    from inkdesk_server.db_migrations import main

    engine = get_engine()
    assert main(["upgrade"]) == 0
    capsys.readouterr()
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN unexpected_column TEXT"))

    assert main(["check"]) == 1
    assert _read_status(capsys)["code"] == "DB_SCHEMA_DRIFT"
