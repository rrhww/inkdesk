from __future__ import annotations

import pytest
from sqlalchemy import select


def test_default_topology_is_deterministic_and_resolvable(temp_app_env):
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.db import get_session_factory
    from inkdesk_server.modules.spaces.models import CapabilitySpace, Organization, OrganizationMembership, WorkspaceSpaceBinding
    from inkdesk_server.modules.spaces.workspace_adapter import require_workspace_context
    from inkdesk_server.research import get_research_service

    with get_session_factory()() as db:
        get_research_service(db, get_settings()).bootstrap_seed_data()
        context = require_workspace_context(db, workspace_slug="inkdesk")
        assert context.workspace.id == "workspace-inkdesk"
        assert context.organization.id == "organization-default"
        assert context.project_space.scope_type == "project"
        assert context.personal_space.parent_space_id == context.project_space.id
        assert len(db.scalars(select(Organization)).all()) == 1
        assert len(db.scalars(select(OrganizationMembership)).all()) == 1
        assert len(db.scalars(select(CapabilitySpace)).all()) == 3
        assert len(db.scalars(select(WorkspaceSpaceBinding)).all()) == 1


def test_multiple_legacy_owners_fail_before_topology_writes(temp_app_env):
    from datetime import UTC, datetime

    from inkdesk_server.db import get_session_factory
    from inkdesk_server.models import User, Workspace
    from inkdesk_server.modules.spaces.bootstrap import ensure_default_topology
    from inkdesk_server.modules.spaces.models import Organization
    from inkdesk_server.modules.spaces.topology import SpaceTopologyError

    now = datetime.now(UTC)
    with get_session_factory()() as db:
        db.add_all([
            User(id="u1", username="u1", email="u1@example.test", password_hash="x", status="ACTIVE", created_at=now, updated_at=now),
            User(id="u2", username="u2", email="u2@example.test", password_hash="x", status="ACTIVE", created_at=now, updated_at=now),
        ])
        db.add_all([
            Workspace(id="w1", owner_user_id="u1", name="One", slug="one", created_at=now, updated_at=now),
            Workspace(id="w2", owner_user_id="u2", name="Two", slug="two", created_at=now, updated_at=now),
        ])
        db.flush()
        with pytest.raises(SpaceTopologyError, match="SPACE_LEGACY_OWNERSHIP_UNSUPPORTED"):
            ensure_default_topology(db)
        assert db.scalar(select(Organization)) is None
