from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from inkdesk_server.models import Workspace
from inkdesk_server.modules.spaces.constants import ORGANIZATION_SCOPE, PERSONAL_SCOPE, PROJECT_SCOPE
from inkdesk_server.modules.spaces.models import CapabilitySpace, Organization, OrganizationMembership, WorkspaceSpaceBinding
from inkdesk_server.modules.spaces.topology import SpaceTopologyError, WorkspaceSpaceContext


def require_workspace_context(db: Session, *, workspace_slug: str) -> WorkspaceSpaceContext:
    workspace = db.scalar(select(Workspace).where(Workspace.slug == workspace_slug))
    if workspace is None:
        raise SpaceTopologyError("SPACE_WORKSPACE_NOT_FOUND")
    return require_workspace_context_by_id(db, workspace_id=workspace.id)


def require_workspace_context_by_id(db: Session, *, workspace_id: str) -> WorkspaceSpaceContext:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise SpaceTopologyError("SPACE_WORKSPACE_NOT_FOUND")
    binding = db.get(WorkspaceSpaceBinding, workspace.id)
    if binding is None:
        raise SpaceTopologyError("SPACE_BINDING_MISSING")
    project = db.get(CapabilitySpace, binding.project_space_id)
    if project is None or project.scope_type != PROJECT_SCOPE or project.owner_membership_id is not None:
        raise SpaceTopologyError("SPACE_TOPOLOGY_INVALID")
    organization_space = db.get(CapabilitySpace, project.parent_space_id)
    organization = db.get(Organization, project.organization_id)
    membership = db.scalar(select(OrganizationMembership).where(OrganizationMembership.organization_id == project.organization_id, OrganizationMembership.user_id == workspace.owner_user_id))
    personal = db.scalar(select(CapabilitySpace).where(CapabilitySpace.parent_space_id == project.id, CapabilitySpace.owner_membership_id == (membership.id if membership else None)))
    if organization is None or organization_space is None or membership is None or personal is None:
        raise SpaceTopologyError("SPACE_MEMBERSHIP_MISSING")
    if organization_space.scope_type != ORGANIZATION_SCOPE or organization_space.parent_space_id is not None or personal.scope_type != PERSONAL_SCOPE or personal.organization_id != project.organization_id:
        raise SpaceTopologyError("SPACE_TOPOLOGY_INVALID")
    return WorkspaceSpaceContext(workspace, organization, membership, organization_space, project, personal)
