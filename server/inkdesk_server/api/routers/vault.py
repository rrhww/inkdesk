from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from inkdesk_server.api.dependencies import get_research_service_dependency
from inkdesk_server.research import ResearchWorkspaceService
from inkdesk_server.schemas import VaultInitializeRequest, VaultStatusResponse


router = APIRouter()


@router.get("/api/vault/status", response_model=VaultStatusResponse)
def vault_status(
    research_service: Annotated[ResearchWorkspaceService, Depends(get_research_service_dependency)],
):
    return research_service.get_vault_status()


@router.post("/api/vault/initialize", response_model=VaultStatusResponse)
def vault_initialize(
    request: VaultInitializeRequest,
    research_service: Annotated[ResearchWorkspaceService, Depends(get_research_service_dependency)],
):
    return research_service.initialize_vault(request.vaultType)
