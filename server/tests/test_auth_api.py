from __future__ import annotations

from fastapi.testclient import TestClient


def test_unauthenticated_private_endpoints_are_rejected(temp_app_env):
    from inkvault_server.main import create_app

    client = TestClient(create_app())

    me_response = client.get("/api/auth/me")
    topics_response = client.get("/api/wiki")

    assert me_response.status_code == 401
    assert me_response.json()["code"] == "UNAUTHORIZED"
    assert topics_response.status_code == 401
    assert topics_response.json()["code"] == "UNAUTHORIZED"


def test_login_me_and_logout_flow(temp_app_env):
    from inkvault_server.main import create_app

    client = TestClient(create_app())

    login_response = client.post(
        "/api/auth/login",
        json={"email": "owner@inkvault.local", "password": "inkvault-owner"},
    )

    assert login_response.status_code == 200
    token = login_response.json()["sessionToken"]
    assert isinstance(token, str)

    me_response = client.get("/api/auth/me", cookies={"inkvault_owner_session": token})
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "owner"
    assert me_response.json()["workspaceSlug"] == "inkvault"

    logout_response = client.post("/api/auth/logout", cookies={"inkvault_owner_session": token})
    assert logout_response.status_code == 204

    after_logout = client.get("/api/auth/me", cookies={"inkvault_owner_session": token})
    assert after_logout.status_code == 401
    assert after_logout.json()["code"] == "UNAUTHORIZED"


def test_invalid_credentials_are_rejected(temp_app_env):
    from inkvault_server.main import create_app

    client = TestClient(create_app())

    response = client.post(
        "/api/auth/login",
        json={"email": "owner@inkvault.local", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"
