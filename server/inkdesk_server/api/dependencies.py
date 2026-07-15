from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from inkdesk_server.core.config import Settings, get_settings
from inkdesk_server.db import get_db
from inkdesk_server import research


def get_research_service_dependency(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> research.ResearchWorkspaceService:
    return research.get_research_service(db, settings)
