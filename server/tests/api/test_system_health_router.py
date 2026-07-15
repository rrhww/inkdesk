from __future__ import annotations

from fastapi.testclient import TestClient


class FakeResearchService:
    def get_retrieval_health(self) -> dict[str, object]:
        return {"pgvectorReady": True, "embeddingConfigured": True, "retrievalMode": "hybrid"}


def test_system_health_routes_are_independent_and_keep_operation_ids():
    from inkdesk_server.api.app import create_api_app
    from inkdesk_server.api.dependencies import get_research_service_dependency

    app = create_api_app()
    app.dependency_overrides[get_research_service_dependency] = FakeResearchService
    client = TestClient(app)

    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/actuator/health").json() == {
        "status": "UP",
        "retrieval": {"pgvectorReady": True, "embeddingConfigured": True, "retrievalMode": "hybrid"},
    }

    schema = app.openapi()
    assert schema["paths"]["/health"]["get"]["operationId"] == "health_health_get"
    assert schema["paths"]["/actuator/health"]["get"]["operationId"] == "actuator_health_actuator_health_get"
