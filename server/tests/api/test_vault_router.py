from __future__ import annotations

from fastapi.testclient import TestClient

from inkdesk_server.security import ApiError


class FakeResearchService:
    def __init__(self) -> None:
        self.initialized_with: str | None = None

    def get_vault_status(self) -> dict[str, object]:
        return {"initialized": False, "vaultType": None, "sharedDirsExist": False}

    def initialize_vault(self, vault_type: str) -> dict[str, object]:
        if vault_type == "conflict":
            raise ApiError(409, "VAULT_CONFLICT", "already initialized")
        self.initialized_with = vault_type
        return {"initialized": True, "vaultType": vault_type, "sharedDirsExist": True}


def test_vault_routes_use_override_and_preserve_contracts():
    from inkdesk_server.api.app import create_api_app
    from inkdesk_server.api.dependencies import get_research_service_dependency

    fake = FakeResearchService()
    app = create_api_app()
    app.dependency_overrides[get_research_service_dependency] = lambda: fake
    client = TestClient(app)

    assert client.get("/api/vault/status").json() == fake.get_vault_status()
    assert client.post("/api/vault/initialize", json={"vaultType": "general"}).json() == {
        "initialized": True,
        "vaultType": "general",
        "sharedDirsExist": True,
    }
    assert fake.initialized_with == "general"
    assert client.post("/api/vault/initialize", json={}).status_code == 422
    assert client.post("/api/vault/initialize", json={"vaultType": 4}).status_code == 422
    conflict = client.post("/api/vault/initialize", json={"vaultType": "conflict"})
    assert conflict.status_code == 409
    assert conflict.json() == {"code": "VAULT_CONFLICT", "message": "already initialized"}

    schema = app.openapi()
    assert schema["paths"]["/api/vault/status"]["get"]["operationId"] == "vault_status_api_vault_status_get"
    assert schema["paths"]["/api/vault/initialize"]["post"]["operationId"] == "vault_initialize_api_vault_initialize_post"
