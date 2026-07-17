from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from inkdesk_server.core.config import Settings, get_settings
from inkdesk_server.db import get_db
from inkdesk_server import research
from inkdesk_server.modules.spaces.topology import WorkspaceSpaceContext, SpaceTopologyError
from inkdesk_server.modules.spaces.workspace_adapter import require_workspace_context
from inkdesk_server.security import ResourceNotFoundError


def get_research_service_dependency(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> research.ResearchWorkspaceService:
    return research.get_research_service(db, settings)


def get_default_workspace_context(
    db: Annotated[Session, Depends(get_db)],
) -> WorkspaceSpaceContext:
    try:
        return require_workspace_context(db, workspace_slug=research.DEFAULT_WORKSPACE_SLUG)
    except SpaceTopologyError as error:
        if error.code == "SPACE_WORKSPACE_NOT_FOUND":
            raise ResourceNotFoundError(f"Workspace not found: {research.DEFAULT_WORKSPACE_SLUG}") from error
        raise
