from __future__ import annotations

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext


def test_postgres_baseline_matches_f01_contract_and_model_metadata(temporary_postgres_app_env, capsys):
    from inkdesk_server.db import Base, get_engine
    from inkdesk_server.db_migrations import main
    from inkdesk_server.model_registry import load_orm_models
    from inkdesk_server.schema_contract import F05_COMPATIBILITY_DIGEST, application_schema_digest

    load_orm_models()

    assert main(["upgrade"]) == 0
    capsys.readouterr()

    engine = get_engine()
    assert application_schema_digest(engine, exclude_tables={"alembic_version"}) == F05_COMPATIBILITY_DIGEST
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, Base.metadata) == []
