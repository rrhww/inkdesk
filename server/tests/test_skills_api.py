from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient


COOKIE = {"inkdesk_owner_session": "owner"}


def _make_client(temp_app_env: Path) -> TestClient:
    from inkdesk_server.main import create_app
    app = create_app()
    return TestClient(app, cookies=COOKIE)


def _create_minimal_skill(vault_root: Path, name: str = "test-skill") -> Path:
    """在临时 vault 中创建一个最小可解析的 Skill package。"""
    pkg = vault_root / "skills" / name
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: 测试用 Skill\n---\n\n# {name}\n\n测试内容\n",
        encoding="utf-8",
    )
    (pkg / "contract.json").write_text(
        json.dumps({
            "schemaVersion": "1.0",
            "id": name,
            "version": "0.1.0",
            "status": "draft",
            "category": "engineering",
            "kind": "producer",
            "summary": "测试用 Skill",
            "inputs": [],
            "contextRequirements": [],
            "outputs": [],
            "hardGates": [],
            "capabilities": [],
            "writePolicy": {"canonicalWiki": "denied", "runArtifacts": "allowed", "codeRepository": "denied"},
            "verification": [],
            "nextSkills": [],
            "supportedRuntimes": ["inkdesk"],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    agents_dir = pkg / "agents"
    agents_dir.mkdir(exist_ok=True)
    (agents_dir / "openai.yaml").write_text(
        f"interface:\n  display_name: {name}\n  short_description: 测试\n  default_prompt: test\npolicy:\n  allow_implicit_invocation: false\n",
        encoding="utf-8",
    )
    refs_dir = pkg / "references"
    refs_dir.mkdir(exist_ok=True)
    (refs_dir / "guide.md").write_text("# 参考指南\n\n测试内容\n", encoding="utf-8")
    return pkg


def test_skills_list_empty(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    resp = client.get("/api/skills")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["valid"] == 0
    assert data["invalid"] == 0
    assert data["skills"] == []


def test_skills_list_with_one_skill(temp_app_env: Path) -> None:
    _create_minimal_skill(temp_app_env, "test-skill")
    client = _make_client(temp_app_env)
    resp = client.get("/api/skills")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["valid"] == 1
    assert data["invalid"] == 0
    assert data["byStatus"]["draft"] == 1
    skill = data["skills"][0]
    assert skill["name"] == "test-skill"
    assert skill["contractId"] == "test-skill"
    assert skill["status"] == "draft"
    assert skill["category"] == "engineering"
    assert skill["kind"] == "producer"
    assert skill["valid"] is True


def test_skill_detail_found(temp_app_env: Path) -> None:
    _create_minimal_skill(temp_app_env, "test-skill")
    client = _make_client(temp_app_env)
    resp = client.get("/api/skills/test-skill")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "test-skill"
    assert data["contractId"] == "test-skill"
    assert data["version"] == "0.1.0"
    assert data["status"] == "draft"
    assert data["category"] == "engineering"
    assert data["kind"] == "producer"
    assert data["summary"] == "测试用 Skill"
    assert data["valid"] is True
    assert "测试内容" in data["skillMd"]
    assert data["contract"]["id"] == "test-skill"
    assert "guide.md" in data["references"]
    assert "openai.yaml" in data["agents"]
    assert isinstance(data["validationFindings"], list)


def test_skill_detail_not_found(temp_app_env: Path) -> None:
    client = _make_client(temp_app_env)
    resp = client.get("/api/skills/nonexistent")
    assert resp.status_code == 404
