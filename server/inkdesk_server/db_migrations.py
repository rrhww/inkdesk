from __future__ import annotations

import argparse
import json
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, inspect, text

from inkdesk_server.core.config import get_settings
from inkdesk_server.db import get_engine
from inkdesk_server.schema_contract import F01_COMPATIBILITY_DIGEST, application_schema_digest, table_data_fingerprints


HEAD_REVISION = "f02_0001"
VERSION_TABLE = "alembic_version"
MIGRATION_LOCK_KEY = 518_020_001


class DatabaseState(StrEnum):
    EMPTY = "EMPTY"
    F01_CURRENT_UNMANAGED = "F01_CURRENT_UNMANAGED"
    MANAGED_CURRENT = "MANAGED_CURRENT"
    MANAGED_BEHIND = "MANAGED_BEHIND"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN_REVISION = "UNKNOWN_REVISION"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"


@dataclass(frozen=True)
class DatabaseStatus:
    state: DatabaseState
    currentRevision: str | None
    headRevision: str
    schemaDigest: str | None
    requiredAction: str
    dialect: str


class DatabaseReadinessError(RuntimeError):
    def __init__(self, code: str, status: DatabaseStatus):
        self.code = code
        self.status = status
        super().__init__(f"{code}: run python -m inkdesk_server.db_migrations upgrade")


class MigrationLockTimeout(RuntimeError):
    pass


def inspect_database(engine: Engine) -> DatabaseStatus:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    dialect = engine.dialect.name
    if VERSION_TABLE in tables:
        with engine.connect() as connection:
            revisions = list(connection.execute(text("SELECT version_num FROM alembic_version")))
        current_revision = revisions[0][0] if len(revisions) == 1 else None
        if current_revision == HEAD_REVISION:
            schema_digest = None
            if dialect == "postgresql":
                schema_digest = application_schema_digest(engine, exclude_tables={VERSION_TABLE})
                if schema_digest != F01_COMPATIBILITY_DIGEST:
                    return DatabaseStatus(
                        state=DatabaseState.SCHEMA_DRIFT,
                        currentRevision=current_revision,
                        headRevision=HEAD_REVISION,
                        schemaDigest=schema_digest,
                        requiredAction="manual_intervention",
                        dialect=dialect,
                    )
            elif _sqlite_metadata_drift(engine):
                return DatabaseStatus(
                    state=DatabaseState.SCHEMA_DRIFT,
                    currentRevision=current_revision,
                    headRevision=HEAD_REVISION,
                    schemaDigest=None,
                    requiredAction="manual_intervention",
                    dialect=dialect,
                )
            return DatabaseStatus(
                state=DatabaseState.MANAGED_CURRENT,
                currentRevision=current_revision,
                headRevision=HEAD_REVISION,
                schemaDigest=schema_digest,
                requiredAction="none",
                dialect=dialect,
            )
        if current_revision in _known_revisions():
            return DatabaseStatus(
                state=DatabaseState.MANAGED_BEHIND,
                currentRevision=current_revision,
                headRevision=HEAD_REVISION,
                schemaDigest=None,
                requiredAction="upgrade",
                dialect=dialect,
            )
        return DatabaseStatus(
            state=DatabaseState.UNKNOWN_REVISION,
            currentRevision=current_revision,
            headRevision=HEAD_REVISION,
            schemaDigest=None,
            requiredAction="manual_intervention",
            dialect=dialect,
        )

    user_tables = {table for table in tables if not table.startswith("sqlite_")}
    if not user_tables:
        return DatabaseStatus(
            state=DatabaseState.EMPTY,
            currentRevision=None,
            headRevision=HEAD_REVISION,
            schemaDigest=None,
            requiredAction="upgrade",
            dialect=dialect,
        )
    if dialect == "postgresql":
        schema_digest = application_schema_digest(engine)
        if schema_digest == F01_COMPATIBILITY_DIGEST:
            return DatabaseStatus(
                state=DatabaseState.F01_CURRENT_UNMANAGED,
                currentRevision=None,
                headRevision=HEAD_REVISION,
                schemaDigest=schema_digest,
                requiredAction="upgrade",
                dialect=dialect,
            )
        return DatabaseStatus(
            state=DatabaseState.UNSUPPORTED,
            currentRevision=None,
            headRevision=HEAD_REVISION,
            schemaDigest=schema_digest,
            requiredAction="manual_intervention",
            dialect=dialect,
        )
    return DatabaseStatus(
        state=DatabaseState.UNSUPPORTED,
        currentRevision=None,
        headRevision=HEAD_REVISION,
        schemaDigest=None,
        requiredAction="manual_intervention",
        dialect=dialect,
    )


def _error(code: str, status: DatabaseStatus) -> dict[str, str | None]:
    return {
        "code": code,
        "currentRevision": status.currentRevision,
        "headRevision": status.headRevision,
        "dialect": status.dialect,
        "nextCommand": "python -m inkdesk_server.db_migrations status",
    }


def _print(payload: object) -> None:
    print(json.dumps(payload, sort_keys=True))


def _alembic_config() -> Config:
    server_root = Path(__file__).resolve().parent.parent
    config = Config(str(server_root / "alembic.ini"))
    config.set_main_option("script_location", str(server_root / "alembic"))
    config.set_main_option("sqlalchemy.url", get_settings().db_url)
    return config


def _known_revisions() -> set[str]:
    script = ScriptDirectory.from_config(_alembic_config())
    return {revision.revision for revision in script.walk_revisions() if revision.revision}


def _sqlite_metadata_drift(engine: Engine) -> bool:
    from inkdesk_server import models  # noqa: F401
    from inkdesk_server.db import Base

    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return bool(compare_metadata(context, Base.metadata))


@contextmanager
def _migration_lock(engine: Engine):
    if engine.dialect.name != "postgresql":
        yield
        return
    timeout_seconds = get_settings().migration_lock_timeout_seconds
    deadline = time.monotonic() + timeout_seconds
    with engine.connect() as connection:
        locked = False
        try:
            while True:
                locked = bool(
                    connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": MIGRATION_LOCK_KEY}).scalar_one()
                )
                if locked:
                    break
                if time.monotonic() >= deadline:
                    raise MigrationLockTimeout
                time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
            yield
        finally:
            if locked:
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK_KEY})


def _upgrade_empty_database() -> DatabaseStatus:
    command.upgrade(_alembic_config(), "head")
    return inspect_database(get_engine())


def _adopt_f01_database(engine: Engine) -> DatabaseStatus:
    before_schema = application_schema_digest(engine)
    before_data = table_data_fingerprints(engine)
    command.stamp(_alembic_config(), HEAD_REVISION)
    after_schema = application_schema_digest(engine, exclude_tables={VERSION_TABLE})
    after_data = table_data_fingerprints(engine, exclude_tables={VERSION_TABLE})
    if after_schema != before_schema or after_data != before_data:
        raise RuntimeError("F01 adoption changed the application schema or data")
    return inspect_database(engine)


def _error_code_for_status(status: DatabaseStatus) -> str:
    if status.state is DatabaseState.UNKNOWN_REVISION:
        return "DB_REVISION_UNKNOWN"
    if status.state is DatabaseState.SCHEMA_DRIFT:
        return "DB_SCHEMA_DRIFT"
    if status.state in {DatabaseState.EMPTY, DatabaseState.F01_CURRENT_UNMANAGED, DatabaseState.MANAGED_BEHIND}:
        return "DB_REVISION_BEHIND"
    return "DB_SCHEMA_UNSUPPORTED"


def assert_database_ready() -> None:
    status = inspect_database(get_engine())
    if status.state is not DatabaseState.MANAGED_CURRENT:
        raise DatabaseReadinessError(_error_code_for_status(status), status)


def _upgrade(status: DatabaseStatus) -> int:
    if status.state is DatabaseState.UNSUPPORTED:
        _print(_error("DB_SCHEMA_UNSUPPORTED", status))
        return 1
    if status.state is DatabaseState.EMPTY:
        try:
            upgraded = _upgrade_empty_database()
        except Exception:
            _print(_error("DB_MIGRATION_FAILED", status))
            return 1
        if upgraded.state is DatabaseState.MANAGED_CURRENT:
            _print(asdict(upgraded))
            return 0
        _print(_error("DB_MIGRATION_FAILED", upgraded))
        return 1
    if status.state is DatabaseState.F01_CURRENT_UNMANAGED:
        try:
            adopted = _adopt_f01_database(get_engine())
        except Exception:
            _print(_error("DB_MIGRATION_FAILED", status))
            return 1
        if adopted.state is DatabaseState.MANAGED_CURRENT:
            _print(asdict(adopted))
            return 0
        _print(_error("DB_MIGRATION_FAILED", adopted))
        return 1
    if status.state is DatabaseState.MANAGED_BEHIND:
        try:
            command.upgrade(_alembic_config(), "head")
            upgraded = inspect_database(get_engine())
        except Exception:
            _print(_error("DB_MIGRATION_FAILED", status))
            return 1
        if upgraded.state is DatabaseState.MANAGED_CURRENT:
            _print(asdict(upgraded))
            return 0
        _print(_error("DB_MIGRATION_FAILED", upgraded))
        return 1
    if status.state is DatabaseState.MANAGED_CURRENT:
        _print(asdict(status))
        return 0
    _print(_error(_error_code_for_status(status), status))
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m inkdesk_server.db_migrations")
    parser.add_argument("command", choices=("status", "check", "upgrade"))
    args = parser.parse_args(argv)
    if args.command == "status":
        status = inspect_database(get_engine())
        _print(asdict(status))
        return 0
    if args.command == "check":
        status = inspect_database(get_engine())
        if status.state is DatabaseState.MANAGED_CURRENT:
            _print(asdict(status))
            return 0
        _print(_error(_error_code_for_status(status), status))
        return 1
    engine = get_engine()
    try:
        with _migration_lock(engine):
            return _upgrade(inspect_database(engine))
    except MigrationLockTimeout:
        status = DatabaseStatus(
            state=DatabaseState.MANAGED_BEHIND,
            currentRevision=None,
            headRevision=HEAD_REVISION,
            schemaDigest=None,
            requiredAction="retry",
            dialect=engine.dialect.name,
        )
        _print(_error("DB_MIGRATION_LOCK_TIMEOUT", status))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
