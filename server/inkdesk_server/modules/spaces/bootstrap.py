from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from inkdesk_server.models import Workspace
from inkdesk_server.modules.spaces.constants import (
    ACTIVE_STATUS, DEFAULT_ORGANIZATION_ID, DEFAULT_ORGANIZATION_NAME, DEFAULT_ORGANIZATION_SLUG,
    ORGANIZATION_SCOPE, PERSONAL_SCOPE, PROJECT_SCOPE, membership_id, organization_space_id,
    personal_slug, personal_space_id, project_space_id,
)
from inkdesk_server.modules.spaces.models import CapabilitySpace, Organization, OrganizationMembership, WorkspaceSpaceBinding
from inkdesk_server.modules.spaces.topology import SpaceTopologyError


def _expect(existing, **expected) -> None:
    if existing is not None and any(getattr(existing, key) != value for key, value in expected.items()):
        raise SpaceTopologyError("SPACE_IDENTITY_CONFLICT")


def ensure_default_topology(db: Session) -> None:
    workspaces = db.scalars(select(Workspace).order_by(Workspace.id)).all()
    owner_ids = {workspace.owner_user_id for workspace in workspaces}
    if len(owner_ids) > 1:
        raise SpaceTopologyError("SPACE_LEGACY_OWNERSHIP_UNSUPPORTED")
    if not workspaces:
        return
    now = datetime.now(UTC)
    owner_id = next(iter(owner_ids))
    organization = db.get(Organization, DEFAULT_ORGANIZATION_ID)
    _expect(organization, slug=DEFAULT_ORGANIZATION_SLUG, status=ACTIVE_STATUS)
    if organization is None:
        organization = Organization(id=DEFAULT_ORGANIZATION_ID, slug=DEFAULT_ORGANIZATION_SLUG, name=DEFAULT_ORGANIZATION_NAME, status=ACTIVE_STATUS, created_at=now, updated_at=now)
        db.add(organization)
    membership_key = membership_id(owner_id)
    membership = db.get(OrganizationMembership, membership_key)
    _expect(membership, organization_id=DEFAULT_ORGANIZATION_ID, user_id=owner_id, role="owner", status=ACTIVE_STATUS)
    if membership is None:
        membership = OrganizationMembership(id=membership_key, organization_id=DEFAULT_ORGANIZATION_ID, user_id=owner_id, role="owner", status=ACTIVE_STATUS, created_at=now, updated_at=now)
        db.add(membership)
    db.flush()
    org_space_key = organization_space_id()
    organization_space = db.get(CapabilitySpace, org_space_key)
    _expect(organization_space, organization_id=DEFAULT_ORGANIZATION_ID, parent_space_id=None, owner_membership_id=None, slug="organization", scope_type=ORGANIZATION_SCOPE, status=ACTIVE_STATUS)
    if organization_space is None:
        db.add(CapabilitySpace(id=org_space_key, organization_id=DEFAULT_ORGANIZATION_ID, parent_space_id=None, owner_membership_id=None, slug="organization", name=DEFAULT_ORGANIZATION_NAME, scope_type=ORGANIZATION_SCOPE, status=ACTIVE_STATUS, created_at=now, updated_at=now))
    db.flush()
    for workspace in workspaces:
        project_key = project_space_id(workspace.id)
        project = db.get(CapabilitySpace, project_key)
        _expect(project, organization_id=DEFAULT_ORGANIZATION_ID, parent_space_id=org_space_key, owner_membership_id=None, slug=f"project-{workspace.slug}", scope_type=PROJECT_SCOPE, status=ACTIVE_STATUS)
        if project is None:
            db.add(CapabilitySpace(id=project_key, organization_id=DEFAULT_ORGANIZATION_ID, parent_space_id=org_space_key, owner_membership_id=None, slug=f"project-{workspace.slug}", name=workspace.name, scope_type=PROJECT_SCOPE, status=ACTIVE_STATUS, created_at=now, updated_at=now))
        db.flush()
        personal_key = personal_space_id(workspace.id, owner_id)
        personal = db.get(CapabilitySpace, personal_key)
        _expect(personal, organization_id=DEFAULT_ORGANIZATION_ID, parent_space_id=project_key, owner_membership_id=membership_key, slug=personal_slug(workspace.slug, owner_id), scope_type=PERSONAL_SCOPE, status=ACTIVE_STATUS)
        if personal is None:
            db.add(CapabilitySpace(id=personal_key, organization_id=DEFAULT_ORGANIZATION_ID, parent_space_id=project_key, owner_membership_id=membership_key, slug=personal_slug(workspace.slug, owner_id), name=f"{workspace.name} Personal", scope_type=PERSONAL_SCOPE, status=ACTIVE_STATUS, created_at=now, updated_at=now))
        binding = db.get(WorkspaceSpaceBinding, workspace.id)
        _expect(binding, project_space_id=project_key)
        if binding is None:
            db.add(WorkspaceSpaceBinding(workspace_id=workspace.id, project_space_id=project_key))
    db.flush()
