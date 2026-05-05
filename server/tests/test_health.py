from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint_returns_up(temp_app_env):
    from inkvault_server.main import create_app

    client = TestClient(create_app())

    response = client.get("/actuator/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "UP",
        "retrieval": {
            "pgvectorReady": False,
            "embeddingConfigured": False,
            "retrievalMode": "lexical_fallback",
        },
    }


def test_lightweight_health_endpoint_returns_ok(temp_app_env):
    from inkvault_server.main import create_app

    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
