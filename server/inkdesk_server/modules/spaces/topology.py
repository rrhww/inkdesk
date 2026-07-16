from __future__ import annotations

from dataclasses import dataclass

from inkdesk_server.models import Workspace
from inkdesk_server.modules.spaces.models import CapabilitySpace, Organization, OrganizationMembership


class SpaceTopologyError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class WorkspaceSpaceContext:
    workspace: Workspace
    organization: Organization
    membership: OrganizationMembership
    organization_space: CapabilitySpace
    project_space: CapabilitySpace
    personal_space: CapabilitySpace
