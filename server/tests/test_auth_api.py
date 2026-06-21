from __future__ import annotations

from fastapi.testclient import TestClient


def test_api_endpoints_require_no_authentication(temp_app_env):
    """All private API endpoints are accessible without any auth cookie in single-tenant mode."""
    from inkdesk_server.main import create_app

    client = TestClient(create_app())

    endpoints = [
        ("GET", "/api/admin/home"),
        ("GET", "/api/wiki"),
        ("GET", "/api/raw"),
        ("GET", "/api/ingest"),
        ("GET", "/api/runs"),
        ("GET", "/api/health"),
    ]

    for method, path in endpoints:
        resp = client.request(method, path)
        assert resp.status_code == 200, f"{method} {path} returned {resp.status_code}"


def test_resource_not_found_returns_404(temp_app_env):
    from inkdesk_server.main import create_app

    client = TestClient(create_app())
    resp = client.get("/api/runs/nonexistent-id")
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


def test_compile_task_not_found_returns_404(temp_app_env):
    from inkdesk_server.main import create_app

    client = TestClient(create_app())
    resp = client.get("/api/compile/nonexistent-task")
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"
