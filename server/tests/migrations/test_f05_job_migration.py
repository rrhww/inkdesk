from sqlalchemy import inspect
from sqlalchemy import text


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


def test_guarded_f05_rollback_allows_empty_schema_and_refuses_runtime_history(raw_temp_app_env, capsys) -> None:
    from inkdesk_server.db import get_engine
    from inkdesk_server.db_migrations import main

    assert main(["upgrade"]) == 0
    capsys.readouterr()
    assert main(["rollback-f05"]) == 0
    assert '"currentRevision": "f04_0002"' in capsys.readouterr().out

    assert main(["upgrade"]) == 0
    capsys.readouterr()
    with get_engine().begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO jobs (
                    id, organization_id, capability_space_id, kind, subject_type, subject_id,
                    idempotency_key, payload_json, status, priority, available_at,
                    attempt_count, max_attempts, created_at, updated_at
                ) VALUES (
                    'job-runtime', 'org', 'space', 'test', 'test', 'subject',
                    'runtime-key', '{}', 'pending', 0, CURRENT_TIMESTAMP,
                    0, 3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            )
        )
    assert main(["rollback-f05"]) == 1
    assert '"code": "DB_MIGRATION_ROLLBACK_UNSAFE"' in capsys.readouterr().out
    assert "jobs" in inspect(get_engine()).get_table_names()
