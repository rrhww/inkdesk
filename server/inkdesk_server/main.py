from __future__ import annotations

import asyncio
import json
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from inkdesk_server.core.config import get_settings
from inkdesk_server.engine import EngineRuntime
from inkdesk_server.graph_index import GraphIndexRuntime
from inkdesk_server.harness.audit import HarnessAuditError, HarnessAuditRuntime, TERMINAL_STATUSES
from inkdesk_server.harness.executor import ExecutorError
from inkdesk_server.harness.models import PermissionStatus
from inkdesk_server.harness.permissions import PermissionError
from inkdesk_server.harness.run_store import RunNotFoundError
from inkdesk_server.knowledge import KnowledgeService
from inkdesk_server.knowledge_health import KnowledgeHealthRuntime
from inkdesk_server.schemas import (
    ApiErrorResponse,
    EngineCommandRequest,
    HarnessRunRequest,
    KnowledgeBriefing,
    KnowledgeReviewCreateRequest,
    KnowledgeReviewDecisionRequest,
    KnowledgeSignalActionRequest,
    KnowledgeSearchResponse,
    KnowledgeSourcesResponse,
    KnowledgeTopicList,
    PermissionDecisionRequest,
    SkillRunRequest,
    TaskCreateRequest,
    TaskListResponse,
    TaskTransitionRequest,
)
from inkdesk_server.security import ApiError, ResourceNotFoundError
from inkdesk_server.tasks import TaskEventBus, TaskRuntime
from inkdesk_server.tech_solution import SkillExecutionError, TechSolutionRuntime


def create_app() -> FastAPI:
    settings = get_settings()
    graph_runtime = GraphIndexRuntime(settings)
    knowledge_service = KnowledgeService(graph_runtime)
    health_runtime = KnowledgeHealthRuntime(graph_runtime)

    def task_graph_snapshot():
        snapshot = graph_runtime.current()
        return graph_runtime.refresh("task-context") if snapshot.version == "empty" else snapshot

    task_events = TaskEventBus()
    task_runtime = TaskRuntime(task_graph_snapshot, on_change=task_events.publish)
    engine_runtime = EngineRuntime(
        settings,
        graph_runtime.current,
        graph_runtime.events.publish_runtime,
    )
    skill_runtime = TechSolutionRuntime(
        settings,
        graph_runtime.current,
        graph_runtime.refresh,
        graph_runtime.events.publish_runtime,
    )
    repo_root = settings.repo_root or str(Path(__file__).resolve().parents[2])
    harness_runtime = HarnessAuditRuntime(
        vault_root=settings.vault_root,
        repo_root=Path(repo_root),
        graph_refresh=graph_runtime.refresh,
        work_root=settings.harness_work_root,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        task_events.attach_loop(asyncio.get_running_loop())
        if settings.enable_file_watcher:
            graph_runtime.start(asyncio.get_running_loop())
        else:
            graph_runtime.events.attach_loop(asyncio.get_running_loop())
            graph_runtime.schedule_refresh("startup", debounce_seconds=0.0)
        try:
            yield
        finally:
            await engine_runtime.close()
            await skill_runtime.close()
            await harness_runtime.close()
            graph_runtime.stop()

    app = FastAPI(title="Inkdesk Graph Engine", version="0.2.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ],
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.exception_handler(ApiError)
    async def handle_api_error(_, exception: ApiError):
        return JSONResponse(
            status_code=exception.status_code,
            content=ApiErrorResponse(code=exception.code, message=exception.message).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(_, exception: RequestValidationError):
        first = exception.errors()[0] if exception.errors() else {}
        location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
        detail = str(first.get("msg") or "Request validation failed.")
        message = f"{location}: {detail}" if location else detail
        return JSONResponse(
            status_code=422,
            content=ApiErrorResponse(code="INVALID_REQUEST", message=message).model_dump(),
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "state": "in-memory"}

    @app.get("/api/graph")
    def graph_snapshot(source: str | None = None):
        snapshot = graph_runtime.current()
        if snapshot.version == "empty":
            snapshot = graph_runtime.refresh("api")
        if source is None:
            return snapshot.to_dict()
        if source not in {"vault", "repo"}:
            raise ApiError(400, "INVALID_GRAPH_SOURCE", "Graph source must be 'vault' or 'repo'.")
        return snapshot.for_source(source).to_dict()

    @app.get("/api/graph/document")
    def graph_document(nodeId: str):
        try:
            return graph_runtime.read_document(nodeId)
        except (FileNotFoundError, UnicodeDecodeError) as error:
            raise ResourceNotFoundError("Graph document was not found.") from error

    @app.get("/api/doc/{node_id:path}")
    def graph_document_by_id(node_id: str):
        return graph_document(nodeId=node_id)

    @app.get("/api/knowledge/topics", response_model=KnowledgeTopicList)
    def knowledge_topics():
        return knowledge_service.list_topics()

    @app.get("/api/knowledge/search", response_model=KnowledgeSearchResponse)
    def knowledge_search(q: str, scope: str = "all"):
        return knowledge_service.search(q, scope)

    @app.get("/api/knowledge/topics/{topic_id}/briefing", response_model=KnowledgeBriefing)
    def knowledge_briefing(topic_id: str):
        return knowledge_service.briefing(topic_id)

    @app.get("/api/knowledge/topics/{topic_id}/sources", response_model=KnowledgeSourcesResponse)
    def knowledge_sources(topic_id: str):
        return knowledge_service.sources(topic_id)

    @app.get("/api/knowledge/topics/{topic_id}/document")
    def knowledge_topic_document(topic_id: str):
        return knowledge_service.document(topic_id)

    @app.get("/api/knowledge/documents/{document_id:path}")
    def knowledge_document(document_id: str):
        return knowledge_service.document_by_id(document_id)

    @app.get("/api/knowledge/signals")
    def knowledge_signals(status: str | None = None, type: str | None = None, topicId: str | None = None):
        return {"signals": health_runtime.list_signals(status=status, signal_type=type, topic_id=topicId)}

    @app.get("/api/knowledge/signals/{signal_id}")
    def knowledge_signal(signal_id: str):
        return health_runtime.get_signal(signal_id)

    @app.post("/api/knowledge/signals/{signal_id}/actions")
    def knowledge_signal_action(signal_id: str, request: KnowledgeSignalActionRequest):
        return health_runtime.action(signal_id, request.action, request.ifVersion, request.note)

    @app.get("/api/knowledge/topics/{topic_id}/claims")
    def knowledge_claims(topic_id: str):
        return {"claims": health_runtime.claims(topic_id)}

    @app.get("/api/knowledge/claims/{claim_id}")
    def knowledge_claim(claim_id: str):
        return health_runtime.get_claim(claim_id)

    @app.get("/api/knowledge/claims/{claim_id}/evidence")
    def knowledge_claim_evidence(claim_id: str):
        return {"evidence": health_runtime.evidence(claim_id)}

    @app.get("/api/knowledge/health/summary")
    def knowledge_health_summary():
        return health_runtime.summary()

    @app.get("/api/knowledge/reviews")
    def knowledge_reviews(status: str | None = None):
        return {"reviews": health_runtime.list_reviews(status)}

    @app.post("/api/knowledge/reviews", status_code=201)
    def create_knowledge_review(request: KnowledgeReviewCreateRequest):
        return health_runtime.create_review(request.model_dump())

    @app.post("/api/knowledge/reviews/{review_id}/decision")
    def decide_knowledge_review(review_id: str, request: KnowledgeReviewDecisionRequest):
        return health_runtime.decide_review(review_id, request.decision, request.note)

    @app.get("/api/knowledge/stream")
    async def knowledge_stream(request: Request, once: bool = False):
        async def events():
            snapshot = graph_runtime.current()
            if snapshot.version == "empty":
                snapshot = graph_runtime.refresh("knowledge-stream")
            initial = {"type": "knowledge.updated", "version": snapshot.version}
            yield f"event: knowledge.updated\ndata: {json.dumps(initial, ensure_ascii=False)}\n\n"
            if once:
                return
            queue = graph_runtime.events.subscribe()
            try:
                while not await request.is_disconnected():
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=settings.graph_sse_heartbeat_seconds)
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"
                        continue
                    snapshot_payload = event.get("snapshot")
                    version = (
                        snapshot_payload.get("version")
                        if isinstance(snapshot_payload, dict)
                        else graph_runtime.current().version
                    )
                    payload = {"type": "knowledge.updated", "version": version}
                    yield f"event: knowledge.updated\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            finally:
                graph_runtime.events.unsubscribe(queue)

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/graph/stream")
    async def graph_stream(request: Request, once: bool = False, source: str | None = None):
        if source is not None and source not in {"vault", "repo"}:
            raise ApiError(400, "INVALID_GRAPH_SOURCE", "Graph source must be 'vault' or 'repo'.")

        def stream_snapshot():
            snapshot = graph_runtime.current()
            return snapshot.for_source(source) if source is not None else snapshot

        async def events():
            initial = stream_snapshot().to_dict()
            yield f"event: graph.snapshot\ndata: {json.dumps(initial, ensure_ascii=False)}\n\n"
            if once:
                return
            queue = graph_runtime.events.subscribe()
            try:
                while not await request.is_disconnected():
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=settings.graph_sse_heartbeat_seconds)
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"
                        continue
                    stream_event = {
                        **event,
                        "snapshot": stream_snapshot().to_dict(),
                    }
                    yield f"event: {event['event']}\ndata: {json.dumps(stream_event, ensure_ascii=False)}\n\n"
            finally:
                graph_runtime.events.unsubscribe(queue)

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/events")
    async def vault_events(request: Request, once: bool = False):
        async def events():
            initial = {
                "type": "graph.snapshot",
                "snapshot": graph_runtime.current().to_dict(),
            }
            yield f"data: {json.dumps(initial, ensure_ascii=False)}\n\n"
            if once:
                return
            queue = graph_runtime.events.subscribe()
            try:
                while not await request.is_disconnected():
                    try:
                        event = await asyncio.wait_for(
                            queue.get(),
                            timeout=settings.graph_sse_heartbeat_seconds,
                        )
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"
                        continue
                    event_type = str(event.get("event") or "graph.updated")
                    payload = {
                        "type": event_type,
                        **{key: value for key, value in event.items() if key != "event"},
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            finally:
                graph_runtime.events.unsubscribe(queue)

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/engine/health")
    def engine_health():
        return {"status": "ready", "state": "in-memory", "scheduler": "kahn-bfs"}

    @app.post("/api/engine/stream")
    async def engine_stream(command: EngineCommandRequest):
        async def events():
            async for item in engine_runtime.stream(command):
                yield f"event: {item.event}\ndata: {json.dumps(dict(item.data), ensure_ascii=False)}\n\n"

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/tasks", response_model=TaskListResponse)
    def list_tasks(status: str | None = None, originType: str | None = None, contextStatus: str | None = None):
        return {"tasks": task_runtime.list(status=status, origin_type=originType, context_status=contextStatus)}

    @app.post("/api/tasks", status_code=201)
    def create_task(request: TaskCreateRequest):
        created = task_runtime.create(request)
        # Keep the create response immediate; context assembly updates the same
        # durable record and can be explicitly retried through the context route.
        context_job = threading.Timer(0.05, task_runtime.assemble_context, args=(created["id"],))
        context_job.daemon = True
        context_job.start()
        return created

    @app.get("/api/tasks/stream")
    async def task_stream(request: Request, once: bool = False):
        async def events():
            yield "event: tasks.updated\ndata: " + json.dumps({"type": "tasks.updated", "taskId": None, "version": None}) + "\n\n"
            if once:
                return
            event_queue = task_events.subscribe()
            try:
                while not await request.is_disconnected():
                    try:
                        event = await asyncio.wait_for(event_queue.get(), timeout=settings.graph_sse_heartbeat_seconds)
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"
                        continue
                    yield f"event: tasks.updated\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            finally:
                task_events.unsubscribe(event_queue)

        return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive", "X-Accel-Buffering": "no"})

    @app.get("/api/tasks/{task_id}")
    def get_task(task_id: str):
        return task_runtime.get(task_id)

    @app.post("/api/tasks/{task_id}/context")
    def assemble_task_context(task_id: str, force: bool = False):
        return task_runtime.assemble_context(task_id, force=force)

    @app.post("/api/tasks/{task_id}/transition")
    def transition_task(task_id: str, request: TaskTransitionRequest):
        return task_runtime.transition(task_id, request.status, request.ifVersion)

    @app.post("/api/skills/{skill_id}/stream")
    async def skill_stream(skill_id: str, command: SkillRunRequest):
        try:
            skill_runtime.preflight(skill_id, command)
        except SkillExecutionError as exc:
            status_code = {
                "SKILL_NOT_FOUND": 404,
                "SKILL_INACTIVE": 409,
                "PROVIDER_NOT_CONFIGURED": 503,
            }.get(exc.code, 400)
            raise ApiError(status_code, exc.code, exc.message) from exc

        async def events():
            async for item in skill_runtime.stream(command):
                yield f"event: {item.event}\ndata: {json.dumps(dict(item.data), ensure_ascii=False)}\n\n"

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/runs", status_code=202)
    async def create_run(command: HarnessRunRequest, response: Response):
        try:
            run = await harness_runtime.create_run(
                command.capabilityId,
                command.inputs.model_dump(),
                command.executor,
            )
        except HarnessAuditError as exc:
            status = 404 if exc.code == "CAPABILITY_NOT_FOUND" else 400
            raise ApiError(status, exc.code, exc.message) from exc
        except ExecutorError as exc:
            raise ApiError(503, exc.code, exc.message) from exc
        response.headers["Location"] = f"/api/runs/{run.id}"
        return {
            "runId": run.id,
            "statusUrl": f"/api/runs/{run.id}",
            "eventsUrl": f"/api/runs/{run.id}/events",
        }

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str):
        try:
            record = harness_runtime.store.get_run(run_id)
            payload = record.model_dump(mode="json")
            payload["evidence"] = harness_runtime.store.read_json(run_id, "evidence.json")
            payload["findings"] = harness_runtime.store.read_json(run_id, "findings.json")
            return payload
        except (RunNotFoundError, ValueError) as exc:
            raise ResourceNotFoundError("Harness run was not found.") from exc

    @app.get("/api/runs/{run_id}/report")
    def get_run_report(run_id: str):
        try:
            content = harness_runtime.store.read_text(run_id, "report.md")
        except (RunNotFoundError, ValueError) as exc:
            raise ResourceNotFoundError("Harness run was not found.") from exc
        if content is None:
            raise ResourceNotFoundError("Harness report is not available yet.")
        return {"runId": run_id, "content": content}

    @app.post("/api/runs/{run_id}/cancel")
    async def cancel_run(run_id: str):
        try:
            return (await harness_runtime.cancel(run_id)).model_dump(mode="json")
        except (RunNotFoundError, ValueError) as exc:
            raise ResourceNotFoundError("Harness run was not found.") from exc

    @app.get("/api/runs/{run_id}/permissions")
    def get_run_permissions(run_id: str, status: str | None = None):
        try:
            parsed = PermissionStatus(status) if status else None
            return [item.model_dump(mode="json") for item in harness_runtime.list_permissions(run_id, parsed)]
        except ValueError as exc:
            raise ApiError(400, "INVALID_PERMISSION_STATUS", "Unknown permission status.") from exc
        except RunNotFoundError as exc:
            raise ResourceNotFoundError("Harness run was not found.") from exc

    @app.post("/api/runs/{run_id}/permissions/{permission_id}/decision")
    async def decide_run_permission(run_id: str, permission_id: str, command: PermissionDecisionRequest):
        try:
            result = await harness_runtime.decide_permission(
                run_id,
                permission_id,
                allow=command.decision == "allow_once",
                reason=command.reason,
            )
            return result.model_dump(mode="json")
        except RunNotFoundError as exc:
            raise ResourceNotFoundError("Harness run was not found.") from exc
        except PermissionError as exc:
            status_code = 404 if exc.code == "PERMISSION_NOT_FOUND" else 409
            raise ApiError(status_code, exc.code, exc.message) from exc

    @app.get("/api/executors/{executor_name}")
    async def get_executor(executor_name: str):
        try:
            return await harness_runtime.executors.probe(executor_name)
        except ExecutorError as exc:
            raise ApiError(503, exc.code, exc.message) from exc

    @app.post("/api/executors/{executor_name}/probe")
    async def probe_executor(executor_name: str):
        try:
            return await harness_runtime.executors.probe(executor_name, live=True, force=True)
        except ExecutorError as exc:
            raise ApiError(503, exc.code, exc.message) from exc

    @app.get("/api/runs/{run_id}/events")
    async def run_events(run_id: str, request: Request):
        raw_last_id = request.headers.get("last-event-id", "0")
        try:
            last_id = max(0, int(raw_last_id))
            harness_runtime.store.get_run(run_id)
        except (ValueError, RunNotFoundError) as exc:
            if isinstance(exc, ValueError) and not str(exc).startswith("Invalid run id"):
                raise ApiError(400, "INVALID_EVENT_ID", "Last-Event-ID must be an integer.") from exc
            raise ResourceNotFoundError("Harness run was not found.") from exc

        async def events():
            cursor = last_id
            queue = harness_runtime.store.subscribe(run_id)
            try:
                while True:
                    for event in harness_runtime.store.read_events(run_id, after=cursor):
                        cursor = event.sequence
                        yield (
                            f"id: {event.sequence}\n"
                            f"event: {event.type}\n"
                            f"data: {event.model_dump_json()}\n\n"
                        )
                    record = harness_runtime.store.get_run(run_id)
                    if record.status in TERMINAL_STATUSES and not harness_runtime.store.read_events(run_id, after=cursor):
                        return
                    if await request.is_disconnected():
                        return
                    try:
                        queued = await asyncio.wait_for(queue.get(), timeout=settings.graph_sse_heartbeat_seconds)
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"
                        continue
                    if queued.sequence <= cursor:
                        continue
            finally:
                harness_runtime.store.unsubscribe(run_id, queue)

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    return app


app = create_app()
