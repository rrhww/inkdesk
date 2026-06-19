from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, File, Response, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from inkdesk_server.core.config import Settings, get_settings
from inkdesk_server.db import get_db, init_db, session_scope
from inkdesk_server.deposit_service import DepositService
from inkdesk_server.models import User
from inkdesk_server.vault import VaultService
from inkdesk_server.research import ResearchWorkspaceService, get_research_service
from inkdesk_server.run_service import RunService
from inkdesk_server.schemas import (
    AddRunEventRequest,
    ApiErrorResponse,
    AskBriefingResponse,
    AskRequest,
    AskResponse,
    AskThreadResponse,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthMeResponse,
    CreateDevRunRequest,
    CreateSourceRequest,
    DepositRequest,
    DepositResponse,
    DevRunResponse,
    DevRunSummaryResponse,
    ResearchDashboardResponse,
    ReviewDecisionResponse,
    ReviewItemResponse,
    SourceResponse,
    TopicDetailResponse,
    TopicSummaryResponse,
    VaultInitializeRequest,
    VaultStatusResponse,
    WebRawImportRequest,
)
from inkdesk_server.security import ApiError, InvalidCredentialsError, OwnerSessionService, ResourceNotFoundError, VerifiedOwnerSession, get_current_workspace, get_session_service, require_owner, verify_password


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings = get_settings()
    with session_scope() as db:
        get_research_service(db, settings).bootstrap_seed_data()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    init_db()
    with session_scope() as db:
        get_research_service(db, settings).bootstrap_seed_data()

    app = FastAPI(title="Inkdesk Python Server", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(ApiError)
    async def handle_api_error(_, exception: ApiError):
        return JSONResponse(status_code=exception.status_code, content=ApiErrorResponse(code=exception.code, message=exception.message).model_dump())

    @app.exception_handler(ResourceNotFoundError)
    async def handle_not_found(_, exception: ResourceNotFoundError):
        return JSONResponse(status_code=exception.status_code, content=ApiErrorResponse(code=exception.code, message=exception.message).model_dump())

    @app.exception_handler(InvalidCredentialsError)
    async def handle_invalid_credentials(_, exception: InvalidCredentialsError):
        return JSONResponse(status_code=exception.status_code, content=ApiErrorResponse(code=exception.code, message=exception.message).model_dump())

    @app.exception_handler(Exception)
    async def handle_unexpected(_, __):
        return JSONResponse(status_code=500, content=ApiErrorResponse(code="INTERNAL_ERROR", message="Unexpected server error.").model_dump())

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/actuator/health")
    def actuator_health(
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return {
            "status": "UP",
            "retrieval": get_research_service(db, settings).get_retrieval_health(),
        }

    @app.get("/api/vault/status", response_model=VaultStatusResponse)
    def vault_status(
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_vault_status()

    @app.post("/api/vault/initialize", response_model=VaultStatusResponse)
    def vault_initialize(
        request: VaultInitializeRequest,
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).initialize_vault(request.vaultType)

    @app.post("/api/auth/login", response_model=AuthLoginResponse)
    def login(
        request: AuthLoginRequest,
        db: Annotated[Session, Depends(get_db)],
        session_service: Annotated[OwnerSessionService, Depends(get_session_service)],
    ):
        user = db.scalar(select(User).where(User.email == request.email))
        if not user or user.status.upper() != "ACTIVE" or not verify_password(request.password, user.password_hash):
            raise InvalidCredentialsError()
        return AuthLoginResponse(sessionToken=session_service.create_session_token(user))

    @app.post("/api/auth/logout", status_code=204)
    def logout(
        owner: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        session_service: Annotated[OwnerSessionService, Depends(get_session_service)],
    ):
        session_service.invalidate_session(owner.username, db)
        return Response(status_code=204)

    @app.get("/api/auth/me", response_model=AuthMeResponse)
    def me(owner: Annotated[VerifiedOwnerSession, Depends(require_owner)], db: Annotated[Session, Depends(get_db)]):
        workspace = get_current_workspace(db, owner.username)
        return AuthMeResponse(
            userId=owner.user_id,
            username=owner.username,
            workspaceId=workspace.id,
            workspaceName=workspace.name,
            workspaceSlug=workspace.slug,
        )

    @app.get("/api/admin/home", response_model=ResearchDashboardResponse)
    def home(
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_dashboard()

    @app.get("/api/raw", response_model=list[SourceResponse])
    def raw_list(
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_sources()

    @app.post("/api/raw", response_model=SourceResponse, status_code=201)
    def raw_create(
        request: CreateSourceRequest,
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).create_source(request.kind, request.title, request.locator, request.excerpt, request.body)

    @app.post("/api/raw/web", response_model=SourceResponse, status_code=201)
    def raw_web_import(
        request: WebRawImportRequest,
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).import_web_source(request.url, request.title)

    @app.post("/api/raw/pdf", response_model=SourceResponse, status_code=201)
    def raw_pdf_import(
        file: UploadFile = File(...),
        title: str | None = None,
        locator: str | None = None,
        _: VerifiedOwnerSession = Depends(require_owner),
        db: Session = Depends(get_db),
        settings: Settings = Depends(get_settings),
    ):
        return get_research_service(db, settings).import_pdf_source(file, title, locator)

    @app.get("/api/ingest", response_model=list[ReviewItemResponse])
    def ingest_list(
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_review_items()

    @app.get("/api/ingest/{review_id}", response_model=ReviewItemResponse)
    def ingest_detail(
        review_id: str,
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_review_item(review_id)

    @app.post("/api/ingest/{review_id}/accept", response_model=ReviewDecisionResponse)
    def ingest_accept(
        review_id: str,
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).accept_review(review_id)

    @app.post("/api/ingest/{review_id}/reject", response_model=ReviewDecisionResponse)
    def ingest_reject(
        review_id: str,
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).reject_review(review_id)

    @app.get("/api/wiki", response_model=list[TopicSummaryResponse])
    def wiki_list(
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_topics()

    @app.get("/api/wiki/{topic_id}", response_model=TopicDetailResponse)
    def wiki_detail(
        topic_id: str,
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_topic(topic_id)

    @app.post("/api/ask", response_model=AskResponse)
    def ask(
        request: AskRequest,
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).ask(request)

    @app.get("/api/ask/briefing", response_model=AskBriefingResponse)
    def ask_briefing(
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
        topicId: str | None = None,
        askTurnId: str | None = None,
    ):
        return get_research_service(db, settings).get_ask_briefing(topic_id=topicId, ask_turn_id=askTurnId)

    @app.get("/api/ask/{ask_turn_id}", response_model=AskResponse)
    def ask_detail(
        ask_turn_id: str,
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_ask_turn(ask_turn_id)

    @app.get("/api/ask/{ask_turn_id}/thread", response_model=AskThreadResponse)
    def ask_thread(
        ask_turn_id: str,
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_ask_thread(ask_turn_id)

    @app.post("/api/ask/{ask_turn_id}/writeback", response_model=ReviewItemResponse)
    def ask_writeback(
        ask_turn_id: str,
        _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).create_ask_writeback_proposal(ask_turn_id)

    @app.post("/api/runs", response_model=DevRunResponse, status_code=201)
    def run_create(
        request: CreateDevRunRequest,
        owner: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        workspace = get_current_workspace(db, owner.username)
        return RunService(db).create_run(
            workspace.id, request.type, request.title, request.goal, request.repoContext,
        )

    @app.get("/api/runs", response_model=list[DevRunSummaryResponse])
    def run_list(
        owner: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        workspace = get_current_workspace(db, owner.username)
        return RunService(db).get_runs(workspace.id)

    @app.get("/api/runs/{run_id}", response_model=DevRunResponse)
    def run_detail(
        run_id: str,
        owner: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        workspace = get_current_workspace(db, owner.username)
        return RunService(db).get_run(run_id, workspace.id)

    @app.post("/api/runs/{run_id}/events", response_model=DevRunResponse)
    def run_add_event(
        run_id: str,
        request: AddRunEventRequest,
        owner: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        workspace = get_current_workspace(db, owner.username)
        return RunService(db).add_event(
            run_id, request.stage, request.eventType, request.payload, workspace.id,
        )

    @app.post("/api/runs/{run_id}/cancel", response_model=DevRunResponse)
    def run_cancel(
        run_id: str,
        owner: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        workspace = get_current_workspace(db, owner.username)
        return RunService(db).cancel_run(run_id, workspace.id)

    @app.post("/api/deposits", response_model=DepositResponse)
    def deposit_create(
        request: DepositRequest,
        owner: Annotated[VerifiedOwnerSession, Depends(require_owner)],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
        response: Response = None,
    ):
        workspace = get_current_workspace(db, owner.username)
        deposit_service = DepositService(db, VaultService(settings))
        result = deposit_service.deposit(
            workspace_id=workspace.id,
            source=request.source,
            payload=request.payload,
            run_id=request.runId,
            ask_turn_id=request.askTurnId,
            stage=request.stage,
        )
        if not result.isNew:
            response.status_code = 200
        else:
            response.status_code = 201
        return result

    return app


app = create_app()
