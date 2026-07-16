"""Add the durable Job / Attempt execution kernel."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json

from alembic import op
import sqlalchemy as sa


revision = "f05_0003"
down_revision = "f04_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("capability_space_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("subject_type", sa.String(length=80), nullable=False),
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("deduplication_key", sa.String(length=255), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["capability_space_id"], ["capability_spaces.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_table(
        "job_attempts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("worker_id", sa.String(length=255), nullable=False),
        sa.Column("lease_token", sa.String(length=128), nullable=False),
        sa.Column("leased_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "attempt_number"),
    )
    op.create_index("ix_jobs_claim", "jobs", ["status", "available_at", "priority", "created_at"])
    op.create_index("ix_jobs_subject", "jobs", ["kind", "subject_type", "subject_id"])
    op.create_index("ix_job_attempts_lease_expiry", "job_attempts", ["status", "lease_expires_at"])
    op.create_index(
        "uq_jobs_active_deduplication",
        "jobs",
        ["kind", "organization_id", "capability_space_id", "deduplication_key"],
        unique=True,
        postgresql_where=sa.text("deduplication_key IS NOT NULL AND status IN ('pending', 'running')"),
        sqlite_where=sa.text("deduplication_key IS NOT NULL AND status IN ('pending', 'running')"),
    )
    op.create_index(
        "uq_job_attempts_active_job",
        "job_attempts",
        ["job_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('leased', 'running')"),
        sqlite_where=sa.text("status IN ('leased', 'running')"),
    )
    _backfill_active_compile_tasks()


def _backfill_active_compile_tasks() -> None:
    """Preserve recoverable legacy work without inventing terminal history."""
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT task.id, task.workspace_id, task.source_id, task.content_hash, task.status,
                   binding.project_space_id, space.organization_id
            FROM compile_tasks AS task
            LEFT JOIN workspace_space_bindings AS binding ON binding.workspace_id = task.workspace_id
            LEFT JOIN capability_spaces AS space ON space.id = binding.project_space_id
            WHERE task.status IN ('PENDING', 'RUNNING')
            ORDER BY task.id
            """
        )
    ).mappings()
    now = datetime.now(UTC)
    for row in rows:
        if not row["project_space_id"] or not row["organization_id"]:
            raise RuntimeError("F05_BACKFILL_SCOPE_MISSING")
        digest = sha256(row["id"].encode("utf-8")).hexdigest()[:32]
        job_id = f"job-f05-{digest}"
        payload = json.dumps({"compile_task_id": row["id"]}, sort_keys=True, separators=(",", ":"))
        deduplication_key = f"compile:{row['workspace_id']}:{row['source_id'] or 'none'}:{row['content_hash'] or 'none'}"
        attempt_count = 1 if row["status"] == "RUNNING" else 0
        bind.execute(
            sa.text(
                """
                INSERT INTO jobs (
                    id, organization_id, capability_space_id, kind, subject_type, subject_id,
                    idempotency_key, deduplication_key, payload_json, status, priority,
                    available_at, attempt_count, max_attempts, created_at, updated_at
                ) VALUES (
                    :id, :organization_id, :capability_space_id, 'compile_source', 'compile_task', :subject_id,
                    :idempotency_key, :deduplication_key, :payload_json, 'pending', 0,
                    :now, :attempt_count, 3, :now, :now
                )
                """
            ),
            {
                "id": job_id,
                "organization_id": row["organization_id"],
                "capability_space_id": row["project_space_id"],
                "subject_id": row["id"],
                "idempotency_key": f"compile-task:{row['id']}",
                "deduplication_key": deduplication_key,
                "payload_json": payload,
                "now": now,
                "attempt_count": attempt_count,
            },
        )
        if row["status"] == "RUNNING":
            bind.execute(
                sa.text(
                    """
                    INSERT INTO job_attempts (
                        id, job_id, attempt_number, status, worker_id, lease_token,
                        leased_at, lease_expires_at, finished_at, error_code, error_message, created_at
                    ) VALUES (
                        :id, :job_id, 1, 'abandoned', 'legacy-worker', :token,
                        :now, :now, :now, 'LEGACY_WORKER_INTERRUPTED', 'Legacy worker was interrupted during F05 migration.', :now
                    )
                    """
                ),
                {"id": f"attempt-f05-{digest}", "job_id": job_id, "token": f"legacy-{digest}", "now": now},
            )
            bind.execute(sa.text("UPDATE compile_tasks SET status = 'PENDING', started_at = NULL WHERE id = :id"), {"id": row["id"]})
            bind.execute(
                sa.text("UPDATE compile_steps SET status = 'PENDING', started_at = NULL WHERE compile_task_id = :id AND status = 'RUNNING'"),
                {"id": row["id"]},
            )


def downgrade() -> None:
    raise RuntimeError("F05 downgrade requires the guarded rollback-f05 command")
