from __future__ import annotations

from fastapi.testclient import TestClient

from inkdesk_server.security import ApiError, ResourceNotFoundError


def test_api_shell_preserves_error_handler_responses():
    from inkdesk_server.api.app import create_api_app

    app = create_api_app()

    @app.get("/test-api-error")
    def api_error():
        raise ApiError(409, "CONFLICT", "conflict")

    @app.get("/test-not-found")
    def not_found():
        raise ResourceNotFoundError("missing")

    @app.get("/test-unexpected")
    def unexpected():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)

    assert client.get("/test-api-error").json() == {"code": "CONFLICT", "message": "conflict"}
    assert client.get("/test-not-found").json() == {"code": "NOT_FOUND", "message": "missing"}
    unexpected_response = client.get("/test-unexpected")
    assert unexpected_response.status_code == 500
    assert unexpected_response.json() == {"code": "INTERNAL_ERROR", "message": "Unexpected server error."}


def test_api_shell_preserves_local_web_cors_preflight():
    from inkdesk_server.api.app import create_api_app

    client = TestClient(create_api_app())
    response = client.options(
        "/api/vault/status",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "GET" in response.headers["access-control-allow-methods"]
