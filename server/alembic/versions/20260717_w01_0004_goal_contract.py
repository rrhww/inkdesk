"""Add immutable Goal Contract v1 storage and direct Run scope."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "w01_0004"
down_revision = "f05_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dev_runs", sa.Column("organization_id", sa.String(length=64), nullable=True))
    op.add_column("dev_runs", sa.Column("capability_space_id", sa.String(length=64), nullable=True))
    op.add_column("dev_runs", sa.Column("created_by_membership_id", sa.String(length=64), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT run.id, project.organization_id, binding.project_space_id, membership.id AS membership_id
            FROM dev_runs AS run
            LEFT JOIN workspaces AS workspace ON workspace.id = run.workspace_id
            LEFT JOIN workspace_space_bindings AS binding ON binding.workspace_id = run.workspace_id
            LEFT JOIN capability_spaces AS project ON project.id = binding.project_space_id
            LEFT JOIN organization_memberships AS membership
              ON membership.organization_id = project.organization_id
             AND membership.user_id = workspace.owner_user_id
            ORDER BY run.id
            """
        )
    ).mappings()
    for row in rows:
        if not row["organization_id"] or not row["project_space_id"] or not row["membership_id"]:
            raise RuntimeError(f"W01_RUN_SCOPE_BACKFILL_FAILED:{row['id']}")
        bind.execute(
            sa.text(
                """
                UPDATE dev_runs
                   SET organization_id = :organization_id,
                       capability_space_id = :capability_space_id,
                       created_by_membership_id = :created_by_membership_id
                 WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "organization_id": row["organization_id"],
                "capability_space_id": row["project_space_id"],
                "created_by_membership_id": row["membership_id"],
            },
        )

    with op.batch_alter_table("dev_runs") as batch:
        batch.create_foreign_key("fk_dev_runs_organization", "organizations", ["organization_id"], ["id"], ondelete="RESTRICT")
        batch.create_foreign_key("fk_dev_runs_capability_space", "capability_spaces", ["capability_space_id"], ["id"], ondelete="RESTRICT")
        batch.create_foreign_key("fk_dev_runs_membership", "organization_memberships", ["created_by_membership_id"], ["id"], ondelete="RESTRICT")
        batch.alter_column("organization_id", nullable=False)
        batch.alter_column("capability_space_id", nullable=False)
        batch.alter_column("created_by_membership_id", nullable=False)
    op.create_index("ix_dev_runs_organization_id", "dev_runs", ["organization_id"])
    op.create_index("ix_dev_runs_capability_space_id", "dev_runs", ["capability_space_id"])
    op.create_index("ix_dev_runs_created_by_membership_id", "dev_runs", ["created_by_membership_id"])

    op.create_table(
        "run_goal_contracts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.SmallInteger(), nullable=False),
        sa.Column("contract_json", sa.Text(), nullable=False),
        sa.Column("contract_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("schema_version = 1", name="ck_run_goal_contracts_schema_version"),
        sa.ForeignKeyConstraint(["run_id"], ["dev_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )


def downgrade() -> None:
    raise RuntimeError("W01 downgrade is guarded; use rollback-w01 only when no Goal Contract data exists")
