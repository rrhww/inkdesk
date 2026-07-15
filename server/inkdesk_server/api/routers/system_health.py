from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from inkdesk_server.api.dependencies import get_research_service_dependency
from inkdesk_server.research import ResearchWorkspaceService


router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/actuator/health")
def actuator_health(
    research_service: Annotated[ResearchWorkspaceService, Depends(get_research_service_dependency)],
):
    return {"status": "UP", "retrieval": research_service.get_retrieval_health()}
