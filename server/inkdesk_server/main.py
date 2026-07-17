from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Query, Request, Response, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from inkdesk_server.core.config import Settings, get_settings
from inkdesk_server.api.app import create_api_app
from inkdesk_server.db import get_db, init_db, session_scope
from inkdesk_server.deposit_service import DepositService
from inkdesk_server.health_service import HealthService
from inkdesk_server.health_history_service import HealthHistoryService
from inkdesk_server.evaluation_service import EvaluationService
from inkdesk_server.mcp import build_mcp_server
from inkdesk_server.models import CompileTask, CompileStep, Source, Workspace
from inkdesk_server.vault import VaultService
from inkdesk_server.research import DEFAULT_WORKSPACE_SLUG, ResearchWorkspaceService, get_research_service
from inkdesk_server.run_service import RunService
from inkdesk_server.schemas import (
    AddRunEventRequest,
    AdvanceRunRequest,
    AskBriefingResponse,
    AskRequest,
    AskResponse,
    AskThreadResponse,
    CreateDevRunRequest,
    CreateSourceRequest,
    DepositRequest,
    DepositResponse,
    DevRunResponse,
    DevRunSummaryResponse,
    HealthResponse,
    HealthRunSummary,
    HealthTrendResponse,
    PermissionRespondRequest,
    ResearchDashboardResponse,
    ReviewDecisionResponse,
    ReviewItemResponse,
    SourceResponse,
    TopicDetailResponse,
    TopicSummaryResponse,
    WebRawImportRequest,
)
from inkdesk_server.security import ApiError, ResourceNotFoundError


def _resolve_workspace(db: Session) -> Workspace:
    from inkdesk_server.modules.spaces.topology import SpaceTopologyError
    from inkdesk_server.modules.spaces.workspace_adapter import require_workspace_context

    try:
        return require_workspace_context(db, workspace_slug=DEFAULT_WORKSPACE_SLUG).workspace
    except SpaceTopologyError as error:
        if error.code == "SPACE_WORKSPACE_NOT_FOUND":
            raise ResourceNotFoundError(f"Workspace not found: {DEFAULT_WORKSPACE_SLUG}") from error
        raise


def _read_skill_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_skill_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _read_skill_dir(dir_path: Path) -> dict[str, str]:
    """读取目录下所有文件，返回 {filename: content}。"""
    result: dict[str, str] = {}
    if not dir_path.is_dir():
        return result
    for path in sorted(dir_path.iterdir()):
        if path.is_file():
            try:
                result[path.name] = path.read_text(encoding="utf-8")
            except OSError:
                continue
    return result


def create_app() -> FastAPI:
    settings = get_settings()
    init_db()
    with session_scope() as db:
        get_research_service(db, settings).bootstrap_seed_data()

    # --- MCP Server（必须在 lifespan 之前构建，以便 lifespan 管理其 session manager 生命周期）---
    mcp = build_mcp_server(settings)
    mcp_app = mcp.streamable_http_app()  # 创建 session_manager
    session_manager = mcp.session_manager

    # --- 编译后台 Worker ---
    from inkdesk_server.compile_worker import get_compile_worker
    compile_worker = get_compile_worker(settings)
    compile_worker.start()

    @asynccontextmanager
    async def app_lifespan(app: FastAPI):
        init_db()
        with session_scope() as db:
            get_research_service(db, settings).bootstrap_seed_data()
        async with session_manager.run():
            yield
        compile_worker.stop()

    app = create_api_app(lifespan=app_lifespan)

    @app.get("/api/admin/home", response_model=ResearchDashboardResponse)
    def home(
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_dashboard()

    @app.get("/api/raw", response_model=list[SourceResponse])
    def raw_list(
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_sources()

    @app.post("/api/raw", response_model=SourceResponse, status_code=201)
    def raw_create(
        request: CreateSourceRequest,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).create_source(request.kind, request.title, request.locator, request.excerpt, request.body)

    @app.post("/api/raw/web", response_model=SourceResponse, status_code=201)
    def raw_web_import(
        request: WebRawImportRequest,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).import_web_source(request.url, request.title)

    @app.post("/api/raw/pdf", response_model=SourceResponse, status_code=201)
    def raw_pdf_import(
        file: UploadFile = File(...),
        title: str | None = None,
        locator: str | None = None,
        db: Session = Depends(get_db),
        settings: Settings = Depends(get_settings),
    ):
        return get_research_service(db, settings).import_pdf_source(file, title, locator)

    @app.get("/api/ingest", response_model=list[ReviewItemResponse])
    def ingest_list(
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_review_items()

    @app.get("/api/ingest/{review_id}", response_model=ReviewItemResponse)
    def ingest_detail(
        review_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_review_item(review_id)

    @app.post("/api/ingest/{review_id}/accept", response_model=ReviewDecisionResponse)
    def ingest_accept(
        review_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).accept_review(review_id)

    @app.post("/api/ingest/{review_id}/reject", response_model=ReviewDecisionResponse)
    def ingest_reject(
        review_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).reject_review(review_id)

    @app.get("/api/wiki", response_model=list[TopicSummaryResponse])
    def wiki_list(
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_topics()

    @app.get("/api/wiki/{topic_id}", response_model=TopicDetailResponse)
    def wiki_detail(
        topic_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_topic(topic_id)

    @app.post("/api/ask", response_model=AskResponse)
    def ask(
        request: AskRequest,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).ask(request)

    @app.get("/api/ask/briefing", response_model=AskBriefingResponse)
    def ask_briefing(
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
        topicId: str | None = None,
        askTurnId: str | None = None,
    ):
        return get_research_service(db, settings).get_ask_briefing(topic_id=topicId, ask_turn_id=askTurnId)

    @app.get("/api/ask/{ask_turn_id}", response_model=AskResponse)
    def ask_detail(
        ask_turn_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_ask_turn(ask_turn_id)

    @app.get("/api/ask/{ask_turn_id}/thread", response_model=AskThreadResponse)
    def ask_thread(
        ask_turn_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).get_ask_thread(ask_turn_id)

    @app.post("/api/ask/{ask_turn_id}/writeback", response_model=ReviewItemResponse)
    def ask_writeback(
        ask_turn_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return get_research_service(db, settings).create_ask_writeback_proposal(ask_turn_id)

    @app.post("/api/runs/{run_id}/events", response_model=DevRunResponse)
    def run_add_event(
        run_id: str,
        request: AddRunEventRequest,
        db: Annotated[Session, Depends(get_db)],
    ):
        workspace = _resolve_workspace(db)
        return RunService(db).add_event(
            run_id, request.stage, request.eventType, request.payload, workspace.id,
        )

    @app.post("/api/runs/{run_id}/cancel", response_model=DevRunResponse)
    def run_cancel(
        run_id: str,
        db: Annotated[Session, Depends(get_db)],
    ):
        workspace = _resolve_workspace(db)
        return RunService(db).cancel_run(run_id, workspace.id)

    @app.post("/api/runs/{run_id}/advance", response_model=DevRunResponse)
    def run_advance(
        run_id: str,
        request: AdvanceRunRequest,
        db: Annotated[Session, Depends(get_db)],
    ):
        workspace = _resolve_workspace(db)
        return RunService(db).advance_run(run_id, request.action, workspace.id)

    @app.post("/api/runs/{run_id}/context-pack", response_model=DevRunResponse)
    def run_context_pack(
        run_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        workspace = _resolve_workspace(db)
        from inkdesk_server.stage_actions import StageActionService
        return StageActionService(db, settings).generate_context_pack(run_id, workspace.id)

    @app.post("/api/runs/{run_id}/solution", response_model=DevRunResponse)
    def run_solution(
        run_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        workspace = _resolve_workspace(db)
        from inkdesk_server.stage_actions import StageActionService
        return StageActionService(db, settings).generate_solution(run_id, workspace.id)

    @app.post("/api/runs/{run_id}/review", response_model=DevRunResponse)
    def run_review(
        run_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        workspace = _resolve_workspace(db)
        from inkdesk_server.stage_actions import StageActionService
        return StageActionService(db, settings).generate_review_checklist(run_id, workspace.id)

    @app.post("/api/runs/{run_id}/coding/execute", response_model=DevRunResponse)
    async def run_coding_execute(
        run_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        workspace = _resolve_workspace(db)
        from inkdesk_server.stage_actions import StageActionService
        return await StageActionService(db, settings).execute_coding(run_id, workspace.id)

    @app.get("/api/runs/{run_id}/coding/status")
    def run_coding_status(
        run_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        workspace = _resolve_workspace(db)
        from inkdesk_server.stage_actions import StageActionService
        return StageActionService(db, settings).get_coding_status(run_id, workspace.id)

    @app.get("/api/runs/{run_id}/coding/stream")
    async def run_coding_stream(
        run_id: str,
        db: Annotated[Session, Depends(get_db)],
    ):
        """SSE 端点：流式推送 coding session 的事件（对话、工具调用、权限请求、完成）。

        EventSource 不支持自定义 header，鉴权走 cookie。事件格式：
            event: <event_type>\ndata: <json>\n\n
        终止条件：session 不存在 / task 完成 / 客户端断开。
        """
        # 校验 run 存在且属于默认 workspace
        _resolve_workspace(db)
        from inkdesk_server.coding_session import get_session_manager
        manager = get_session_manager()
        session = manager.get(run_id)
        if session is None:
            return JSONResponse(
                status_code=404,
                content={"code": "SESSION_NOT_FOUND", "message": "No active coding session."},
            )

        async def event_generator():
            # 先发一个 connected 事件，让前端确认连接
            yield f"event: connected\ndata: {json.dumps({'run_id': run_id})}\n\n"
            while True:
                # session 结束且队列空 → 退出
                task_done = session.task is not None and session.task.done()
                if task_done and session.event_queue.empty():
                    yield f"event: stream_end\ndata: {json.dumps({'finished': True})}\n\n"
                    break
                try:
                    event_type, data = await asyncio.wait_for(
                        session.event_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    # 发心跳保持连接，防止代理超时断开
                    yield ": heartbeat\n\n"
                    continue
                payload = json.dumps(data, ensure_ascii=False, default=str)
                yield f"event: {event_type}\ndata: {payload}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
            },
        )

    @app.post("/api/runs/{run_id}/coding/permission/respond")
    async def run_coding_permission_respond(
        run_id: str,
        request: PermissionRespondRequest,
        db: Annotated[Session, Depends(get_db)],
    ):
        """前端回应权限请求：allow=true 放行，allow=false 拒绝。"""
        _resolve_workspace(db)
        from inkdesk_server.coding_session import PermissionResponse, get_session_manager
        manager = get_session_manager()
        response = PermissionResponse(
            request_id=request.request_id,
            allow=request.allow,
            reason=request.reason,
        )
        ok = manager.respond_permission(run_id, response)
        if not ok:
            return JSONResponse(
                status_code=409,
                content={
                    "code": "PERMISSION_NOT_PENDING",
                    "message": "No pending permission request or request_id mismatch.",
                },
            )
        return {"ok": True}

    @app.post("/api/runs/{run_id}/coding/abort")
    async def run_coding_abort(
        run_id: str,
        db: Annotated[Session, Depends(get_db)],
    ):
        """用户中断 coding session：设置 abort_event，取消 task。"""
        _resolve_workspace(db)
        from inkdesk_server.coding_session import get_session_manager
        manager = get_session_manager()
        ok = await manager.abort(run_id)
        if not ok:
            return JSONResponse(
                status_code=404,
                content={"code": "SESSION_NOT_FOUND", "message": "No active coding session."},
            )
        return {"ok": True}

    @app.post("/api/runs/{run_id}/deposit", response_model=DevRunResponse)
    def run_deposit(
        run_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        workspace = _resolve_workspace(db)
        from inkdesk_server.stage_actions import StageActionService
        return StageActionService(db, settings).create_deposit(run_id, workspace.id)

    @app.post("/api/runs/{run_id}/testing", response_model=DevRunResponse)
    def run_testing(
        run_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        workspace = _resolve_workspace(db)
        from inkdesk_server.stage_actions import StageActionService
        return StageActionService(db, settings).generate_testing_checklist(run_id, workspace.id)

    # ── Skill Workbench ──

    @app.get("/api/skills")
    def skills_list(
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        from inkdesk_skill_sdk.registry import SkillRegistry
        skills_root = Path(settings.vault_root) / "skills"
        registry = SkillRegistry([skills_root])
        return registry.get_summary()

    @app.get("/api/skills/{skill_name}")
    def skill_detail(
        skill_name: str,
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        from inkdesk_skill_sdk.registry import SkillRegistry
        skills_root = Path(settings.vault_root) / "skills"
        registry = SkillRegistry([skills_root])
        for pkg_path in registry.discover():
            if pkg_path.name == skill_name:
                meta = registry.resolve(pkg_path)
                if meta is None:
                    raise ResourceNotFoundError(f"Skill package not parseable: {skill_name}")
                validation_findings = []
                if meta.validation_result:
                    validation_findings = [
                        {
                            "code": f.code,
                            "path": f.path,
                            "message": f.message,
                            "severity": f.severity.value,
                        }
                        for f in meta.validation_result.findings
                    ]
                return {
                    "name": meta.name,
                    "contractId": meta.contract_id,
                    "version": meta.version,
                    "status": meta.status.value,
                    "category": meta.category,
                    "kind": meta.kind,
                    "summary": meta.summary,
                    "valid": meta.validation_result.passed if meta.validation_result else False,
                    "skillMd": _read_skill_file(pkg_path / "SKILL.md"),
                    "contract": _read_skill_json(pkg_path / "contract.json"),
                    "references": _read_skill_dir(pkg_path / "references"),
                    "templates": _read_skill_dir(pkg_path / "templates"),
                    "agents": _read_skill_dir(pkg_path / "agents"),
                    "validationFindings": validation_findings,
                    "path": str(pkg_path),
                }
        raise ResourceNotFoundError(f"Skill not found: {skill_name}")

    @app.post("/api/deposits", response_model=DepositResponse)
    def deposit_create(
        request: DepositRequest,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
        response: Response = None,
    ):
        workspace = _resolve_workspace(db)
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

    @app.get("/api/health", response_model=HealthResponse)
    def health_check(
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        service = HealthService(settings, VaultService(settings))
        return service.scan()

    # ── Health 快照与趋势 ──

    @app.post("/api/health/runs")
    def health_run_create(
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        vault = VaultService(settings)
        service = HealthService(settings, vault)
        history = HealthHistoryService(settings, vault)
        scan = service.scan()
        manifest = history.save_snapshot(scan)
        return manifest

    @app.get("/api/health/runs", response_model=HealthTrendResponse)
    def health_run_list(
        settings: Annotated[Settings, Depends(get_settings)],
        limit: int = Query(20, ge=1, le=100),
    ):
        vault = VaultService(settings)
        history = HealthHistoryService(settings, vault)
        return history.trend(limit)

    @app.get("/api/health/runs/{run_id}")
    def health_run_detail(
        run_id: str,
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        vault = VaultService(settings)
        history = HealthHistoryService(settings, vault)
        run = history.get_run(run_id)
        if run is None:
            raise ResourceNotFoundError(f"Health run not found: {run_id}")
        return run

    # ── Evaluation 边界 ──

    @app.get("/api/evals/golden")
    def evals_golden(
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        vault = VaultService(settings)
        evals = EvaluationService(settings, vault)
        return evals.get_golden_tasks()

    @app.post("/api/evals/runs")
    async def evals_run_create(
        request: Request,
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        body = await request.json()
        task_ids = body.get("taskIds", []) if isinstance(body, dict) else []
        rubric_ids = body.get("rubricIds", []) if isinstance(body, dict) else []
        vault = VaultService(settings)
        health = HealthService(settings, vault)
        scan = health.scan()
        gate = scan.get("gateStatus", "FAILED")
        history = HealthHistoryService(settings, vault)
        manifest = history.save_snapshot(scan)
        evals = EvaluationService(settings, vault)
        try:
            eval_manifest = evals.create_eval_run(task_ids, rubric_ids, gate, manifest["healthRunId"])
            return eval_manifest
        except ValueError as e:
            raise ApiError(409, "EVAL_RUN_REJECTED", str(e))

    @app.get("/api/evals/runs/{eval_run_id}")
    def evals_run_detail(
        eval_run_id: str,
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        vault = VaultService(settings)
        evals = EvaluationService(settings, vault)
        run = evals.get_eval_run(eval_run_id)
        if run is None:
            raise ResourceNotFoundError(f"Eval run not found: {eval_run_id}")
        return run

    # --- 编译流水线 ---

    @app.post("/api/raw/{source_id}/compile", status_code=202)
    def raw_compile(
        source_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        workspace = _resolve_workspace(db)
        source = db.get(Source, source_id)
        if source is None or source.workspace_id != workspace.id:
            raise ResourceNotFoundError(f"Source not found: {source_id}")
        if source.status == "WIKI_LINKED":
            raise ApiError(409, "SOURCE_ALREADY_LINKED", "Source is already linked to a wiki topic.")
        service = get_research_service(db, settings)
        task = service._enqueue_compile_for_source(source)
        db.commit()
        is_new = task.status == "PENDING"
        data = service._to_compile_task_response(task)
        data["isNew"] = is_new
        return data

    @app.get("/api/compile/queue")
    def compile_queue(
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        from sqlalchemy import select, desc
        service = get_research_service(db, settings)
        workspace = _resolve_workspace(db)
        tasks = db.scalars(
            select(CompileTask)
            .where(CompileTask.workspace_id == workspace.id)
            .order_by(desc(CompileTask.created_at))
            .limit(50)
        ).all()
        return [service._to_compile_task_summary(t) for t in tasks]

    @app.get("/api/compile/{task_id}")
    def compile_task_status(
        task_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        workspace = _resolve_workspace(db)
        task = db.get(CompileTask, task_id)
        if task is None or task.workspace_id != workspace.id:
            raise ResourceNotFoundError(f"Compile task not found: {task_id}")
        return get_research_service(db, settings)._to_compile_task_response(task)

    @app.post("/api/compile/{task_id}/retry", status_code=202)
    def compile_retry(
        task_id: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        workspace = _resolve_workspace(db)
        task = db.get(CompileTask, task_id)
        if task is None or task.workspace_id != workspace.id:
            raise ResourceNotFoundError(f"Compile task not found: {task_id}")
        if task.status != "FAILED":
            raise ApiError(409, "TASK_NOT_FAILED", "Only FAILED tasks can be retried.")
        for step in task.steps:
            step.status = "PENDING"
            step.error_message = None
            step.started_at = None
            step.completed_at = None
            step.payload_json = "{}"
            db.add(step)
        task.status = "PENDING"
        task.error_message = None
        task.started_at = None
        task.completed_at = None
        db.add(task)
        db.flush()
        if settings.job_backend == "durable":
            from inkdesk_server.infrastructure.jobs.adapters.compile import CompileJobAdapter

            if not CompileJobAdapter().retry_task(db, task, settings):
                raise ApiError(409, "TASK_RETRY_REJECTED", "The durable job cannot be retried.")
        else:
            from inkdesk_server.compile_worker import get_compile_worker

            get_compile_worker(settings).enqueue(task.id)
        db.commit()
        return get_research_service(db, settings)._to_compile_task_response(task)

    # --- MCP Server（挂载在 lifespan 管理的 mcp_app）---
    app.mount("/mcp", mcp_app)

    return app


app = create_app()
