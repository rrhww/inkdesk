from __future__ import annotations

import json
from pathlib import Path


MIGRATED_ROUTES = {
    ("GET", "/health"),
    ("GET", "/actuator/health"),
    ("GET", "/api/vault/status"),
    ("POST", "/api/vault/initialize"),
    ("POST", "/api/runs"),
    ("GET", "/api/runs"),
    ("GET", "/api/runs/{run_id}"),
}


def _route_pairs(app) -> list[tuple[str, str]]:
    return [
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
        if method not in {"HEAD", "OPTIONS"}
    ]


def test_main_composes_api_shell_without_duplicate_routes(temp_app_env):
    from inkdesk_server.main import create_app

    app = create_app()
    route_pairs = _route_pairs(app)

    for route in MIGRATED_ROUTES:
        assert route_pairs.count(route) == 1
    assert ("GET", "/api/health") in route_pairs
    assert ("POST", "/api/health/runs") in route_pairs
    assert any(route.path == "/mcp" for route in app.routes)


def test_w01_openapi_changes_are_limited_to_approved_run_contract_delta(temp_app_env):
    from inkdesk_server.main import create_app

    repository_root = Path(__file__).resolve().parents[3]
    snapshot = json.loads(
        (repository_root / "docs" / "delivery" / "baselines" / "f01" / "contracts" / "openapi.json").read_text(
            encoding="utf-8"
        )
    )

    current = create_app().openapi()
    baseline_paths = snapshot["paths"]
    current_paths = current["paths"]

    assert set(current_paths) == set(baseline_paths)
    for path, baseline_path in baseline_paths.items():
        if path.startswith("/api/runs"):
            continue
        assert current_paths[path] == baseline_path

    baseline_schemas = snapshot["components"]["schemas"]
    current_schemas = current["components"]["schemas"]
    changed_schemas = {
        name
        for name in set(baseline_schemas) | set(current_schemas)
        if baseline_schemas.get(name) != current_schemas.get(name)
    }
    assert changed_schemas <= {"CreateDevRunRequest", "DevRunResponse"}
