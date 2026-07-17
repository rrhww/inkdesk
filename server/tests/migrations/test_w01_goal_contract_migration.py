from __future__ import annotations

from datetime import UTC, datetime

from alembic import command
from sqlalchemy import inspect, text


def test_w01_upgrade_backfills_run_scope_without_fabricating_contract(raw_temp_app_env, capsys) -> None:
    from inkdesk_server.db import get_session_factory
    from inkdesk_server.db_migrations import _alembic_config, main
    from inkdesk_server.models import User, Workspace
    from inkdesk_server.modules.spaces.bootstrap import ensure_default_topology
    from inkdesk_server.modules.spaces.workspace_adapter import require_workspace_context

    command.upgrade(_alembic_config(), "f05_0003")
    now = datetime.now(UTC)
    with get_session_factory()() as db:
        db.add(User(id="user-w01", username="w01", email="w01@example.test", password_hash="hash", status="ACTIVE", created_at=now, updated_at=now))
        db.add(Workspace(id="workspace-w01", owner_user_id="user-w01", name="W01", slug="w01", created_at=now, updated_at=now))
        db.flush()
        ensure_default_topology(db)
        db.execute(
            text(
                """
                INSERT INTO dev_runs (
                    id, workspace_id, type, title, goal, repo_context, status,
                    current_stage, stage_status, created_at, updated_at
                ) VALUES (
                    'run-w01-legacy', 'workspace-w01', 'PRD', 'Legacy run',
                    'Keep this text goal readable.', NULL, 'active',
                    'context', 'pending', :now, :now
                )
                """
            ),
            {"now": now},
        )
        db.commit()

    assert main(["upgrade"]) == 0
    capsys.readouterr()

    inspector = inspect(get_session_factory()().get_bind())
    assert {"organization_id", "capability_space_id", "created_by_membership_id"} <= {
        column["name"] for column in inspector.get_columns("dev_runs")
    }
    assert "run_goal_contracts" in inspector.get_table_names()

    with get_session_factory()() as db:
        context = require_workspace_context(db, workspace_slug="w01")
        row = db.execute(
            text(
                """
                SELECT organization_id, capability_space_id, created_by_membership_id
                FROM dev_runs WHERE id = 'run-w01-legacy'
                """
            )
        ).mappings().one()
        contracts = db.execute(text("SELECT run_id FROM run_goal_contracts")).all()

        assert row["organization_id"] == context.organization.id
        assert row["capability_space_id"] == context.project_space.id
        assert row["created_by_membership_id"] == context.membership.id
        assert contracts == []
