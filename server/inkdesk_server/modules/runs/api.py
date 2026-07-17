from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from inkdesk_server.api.dependencies import get_default_workspace_context
from inkdesk_server.db import get_db
from inkdesk_server.modules.runs.service import RunsApplicationService
from inkdesk_server.modules.spaces.topology import WorkspaceSpaceContext
from inkdesk_server.run_service import RunService
from inkdesk_server.schemas import CreateDevRunRequest, DevRunResponse, DevRunSummaryResponse


router = APIRouter()


@router.post("/api/runs", response_model=DevRunResponse, status_code=201)
def run_create(
    request: CreateDevRunRequest,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[WorkspaceSpaceContext, Depends(get_default_workspace_context)],
) -> DevRunResponse:
    return RunsApplicationService(db).create_run(
        context=context,
        run_type=request.type,
        title=request.title,
        repo_context=request.repoContext,
        goal_contract=request.goalContract,
    )


@router.get("/api/runs", response_model=list[DevRunSummaryResponse])
def run_list(
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[WorkspaceSpaceContext, Depends(get_default_workspace_context)],
) -> list[DevRunSummaryResponse]:
    return RunService(db).get_runs(context.workspace.id)


@router.get("/api/runs/{run_id}", response_model=DevRunResponse)
def run_detail(
    run_id: str,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[WorkspaceSpaceContext, Depends(get_default_workspace_context)],
) -> DevRunResponse:
    return RunService(db).get_run(run_id, context.workspace.id)
