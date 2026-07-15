from __future__ import annotations

def _raise_if_called(*args, **kwargs):
    raise AssertionError("pure API shell must not initialize production runtime")


def _business_routes(app) -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
        if method not in {"HEAD", "OPTIONS"} and route.path not in {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
    }


def test_create_api_app_is_pure_and_has_f01_metadata(monkeypatch):
    import inkdesk_server.db as db
    import inkdesk_server.mcp as mcp
    import inkdesk_server.research as research

    monkeypatch.setattr(db, "init_db", _raise_if_called)
    monkeypatch.setattr(mcp, "build_mcp_server", _raise_if_called)
    monkeypatch.setattr(research, "get_research_service", _raise_if_called)

    from inkdesk_server.api.app import create_api_app

    first = create_api_app()
    second = create_api_app()

    assert first.title == "Inkdesk Python Server"
    assert first.version == "0.1.0"
    assert first is not second
    assert _business_routes(first) == {
        ("GET", "/health"),
        ("GET", "/actuator/health"),
        ("GET", "/api/vault/status"),
        ("POST", "/api/vault/initialize"),
    }
    assert _business_routes(second) == _business_routes(first)
    assert "/api/health" not in {path for _, path in _business_routes(first)}
