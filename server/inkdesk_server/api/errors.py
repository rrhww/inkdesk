from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from inkdesk_server.schemas import ApiErrorResponse
from inkdesk_server.security import ApiError, ResourceNotFoundError


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_, exception: ApiError):
        return JSONResponse(
            status_code=exception.status_code,
            content=ApiErrorResponse(code=exception.code, message=exception.message).model_dump(),
        )

    @app.exception_handler(ResourceNotFoundError)
    async def handle_not_found(_, exception: ResourceNotFoundError):
        return JSONResponse(
            status_code=exception.status_code,
            content=ApiErrorResponse(code=exception.code, message=exception.message).model_dump(),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_, __):
        return JSONResponse(
            status_code=500,
            content=ApiErrorResponse(code="INTERNAL_ERROR", message="Unexpected server error.").model_dump(),
        )
