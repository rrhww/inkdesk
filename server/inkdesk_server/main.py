from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from inkdesk_server.core.config import get_settings
from inkdesk_server.db import init_db
from inkdesk_server.engine import EngineRuntime
from inkdesk_server.graph_index import GraphIndexRuntime
from inkdesk_server.schemas import ApiErrorResponse, EngineCommandRequest
from inkdesk_server.security import ApiError, ResourceNotFoundError


def create_app() -> FastAPI:
    settings = get_settings()
    init_db()
    graph_runtime = GraphIndexRuntime(settings)
    engine_runtime = EngineRuntime(settings, graph_runtime.current)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if settings.enable_file_watcher:
            graph_runtime.start(asyncio.get_running_loop())
        else:
            graph_runtime.events.attach_loop(asyncio.get_running_loop())
            graph_runtime.schedule_refresh("startup", debounce_seconds=0.0)
        try:
            yield
        finally:
            await engine_runtime.close()
            graph_runtime.stop()

    app = FastAPI(title="Inkdesk Graph Engine", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
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

    @app.get("/api/graph/stream")
    async def graph_stream(request: Request, once: bool = False):
        async def events():
            initial = graph_runtime.current().to_dict()
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
                    yield f"event: {event['event']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
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

    return app


app = create_app()
