from sqlalchemy import inspect


def test_f05_upgrade_creates_durable_job_tables_and_marks_head(raw_temp_app_env, capsys) -> None:
    from inkdesk_server.db import get_engine
    from inkdesk_server.db_migrations import main

    assert main(["upgrade"]) == 0
    capsys.readouterr()

    inspector = inspect(get_engine())
    assert {"jobs", "job_attempts"} <= set(inspector.get_table_names())
    assert {"organization_id", "capability_space_id", "idempotency_key"} <= {
        column["name"] for column in inspector.get_columns("jobs")
    }
    assert {"attempt_number", "lease_token", "lease_expires_at"} <= {
        column["name"] for column in inspector.get_columns("job_attempts")
    }

    assert main(["status"]) == 0
    assert '"headRevision": "f05_0003"' in capsys.readouterr().out


def test_job_models_are_registered_in_sqlalchemy_metadata() -> None:
    from inkdesk_server.db import Base
    from inkdesk_server.model_registry import load_orm_models

    load_orm_models()

    assert {"jobs", "job_attempts"} <= set(Base.metadata.tables)
