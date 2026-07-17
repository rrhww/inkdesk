from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from inkdesk_server.api.errors import install_error_handlers
from inkdesk_server.api.routers import system_health, vault
from inkdesk_server.modules.runs import api as runs


def create_api_app(*, lifespan: Callable | None = None) -> FastAPI:
    app = FastAPI(title="Inkdesk Python Server", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    app.include_router(system_health.router)
    app.include_router(vault.router)
    app.include_router(runs.router)
    return app
