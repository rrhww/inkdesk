"""Add the default Organization and Capability Space compatibility topology."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid5

from alembic import op
import sqlalchemy as sa


revision = "f04_0002"
down_revision = "f02_0001"
branch_labels = None
depends_on = None

ORGANIZATION_ID = "organization-default"
NAMESPACE = UUID("b1d4a53b-5bc0-4887-9422-0bd732d45cb0")


def _id(identity: str) -> str:
    return str(uuid5(NAMESPACE, identity))


def _personal_slug(workspace_slug: str, user_id: str) -> str:
    return f"personal-{workspace_slug}-{sha256(user_id.encode('utf-8')).hexdigest()[:12]}"


def upgrade() -> None:
    bind = op.get_bind()
    owners = [row.owner_user_id for row in bind.execute(sa.text("SELECT DISTINCT owner_user_id FROM workspaces ORDER BY owner_user_id"))]
    if len(owners) > 1:
        raise RuntimeError("SPACE_LEGACY_OWNERSHIP_UNSUPPORTED")
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("organization_id", "user_id"),
    )
    op.create_table(
        "capability_spaces",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("parent_space_id", sa.String(length=64), nullable=True),
        sa.Column("owner_membership_id", sa.String(length=64), nullable=True),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("scope_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_space_id"], ["capability_spaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_membership_id"], ["organization_memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("organization_id", "slug"),
    )
    op.create_table(
        "workspace_space_bindings",
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("project_space_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_space_id"], ["capability_spaces.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("workspace_id"), sa.UniqueConstraint("project_space_id"),
    )
    if not owners:
        return
    now = datetime.now(UTC)
    owner_id = owners[0]
    membership = _id(f"membership:{ORGANIZATION_ID}:{owner_id}")
    organization_space = _id(f"organization:{ORGANIZATION_ID}")
    bind.execute(sa.text("INSERT INTO organizations (id, slug, name, status, created_at, updated_at) VALUES (:id, :slug, :name, :status, :now, :now)"), {"id": ORGANIZATION_ID, "slug": "default", "name": "Default Organization", "status": "active", "now": now})
    bind.execute(sa.text("INSERT INTO organization_memberships (id, organization_id, user_id, role, status, created_at, updated_at) VALUES (:id, :organization_id, :user_id, 'owner', 'active', :now, :now)"), {"id": membership, "organization_id": ORGANIZATION_ID, "user_id": owner_id, "now": now})
    bind.execute(sa.text("INSERT INTO capability_spaces (id, organization_id, parent_space_id, owner_membership_id, slug, name, scope_type, status, created_at, updated_at) VALUES (:id, :organization_id, NULL, NULL, 'organization', 'Default Organization', 'organization', 'active', :now, :now)"), {"id": organization_space, "organization_id": ORGANIZATION_ID, "now": now})
    for workspace in bind.execute(sa.text("SELECT id, slug, name FROM workspaces ORDER BY id")).mappings():
        project = _id(f"project:{ORGANIZATION_ID}:{workspace['id']}")
        personal = _id(f"personal:{ORGANIZATION_ID}:{workspace['id']}:{owner_id}")
        bind.execute(sa.text("INSERT INTO capability_spaces (id, organization_id, parent_space_id, owner_membership_id, slug, name, scope_type, status, created_at, updated_at) VALUES (:id, :organization_id, :parent, NULL, :slug, :name, 'project', 'active', :now, :now)"), {"id": project, "organization_id": ORGANIZATION_ID, "parent": organization_space, "slug": f"project-{workspace['slug']}", "name": workspace['name'], "now": now})
        bind.execute(sa.text("INSERT INTO capability_spaces (id, organization_id, parent_space_id, owner_membership_id, slug, name, scope_type, status, created_at, updated_at) VALUES (:id, :organization_id, :parent, :membership, :slug, :name, 'personal', 'active', :now, :now)"), {"id": personal, "organization_id": ORGANIZATION_ID, "parent": project, "membership": membership, "slug": _personal_slug(workspace['slug'], owner_id), "name": f"{workspace['name']} Personal", "now": now})
        bind.execute(sa.text("INSERT INTO workspace_space_bindings (workspace_id, project_space_id) VALUES (:workspace_id, :project_space_id)"), {"workspace_id": workspace['id'], "project_space_id": project})


def downgrade() -> None:
    raise RuntimeError("F04 downgrade is irreversible without the guarded rollback-f04 command")
