from __future__ import annotations

import json
import re
from pathlib import Path
from time import sleep

from fastapi.testclient import TestClient

from inkdesk_server.core.config import get_settings


def _write_knowledge_fixture(vault_root: Path, repo_root: Path) -> None:
    wiki_root = vault_root / "wiki"
    wiki_root.mkdir(parents=True)
    repo_root.mkdir()

    (wiki_root / "codex-host.md").write_text(
        """---
title: Codex Host Adapter
type: topic
status: stale
summary: Embed Inkdesk into Codex while keeping the web app independent.
openQuestions:
  - Which renderer selectors remain stable?
healthSignals:
  - conflicting
---
# Codex Host Adapter

## Current Understanding
- CDP is an optional host adapter.
- The independent web application remains the fallback.

## Key Decisions
- Business truth stays in the Inkdesk service.

## Code Paths
- `scripts/codex/injector.mjs`

## Open Questions
- Can a second Codex instance always be launched?

Evidence lives in [[host-research]]. The missing probe is [[renderer-contract]].
""",
        encoding="utf-8",
    )
    (wiki_root / "host-research.md").write_text(
        """---
title: Host Research
type: source
summary: Results from the Windows CDP compatibility spike.
---
# Host Research

The iframe and CSP bypass probes succeeded.
""",
        encoding="utf-8",
    )
    (repo_root / "architecture.md").write_text(
        """---
title: Architecture Decisions
type: design
summary: Repository architecture decisions.
---
# Architecture Decisions

The graph index is a derived read model.
""",
        encoding="utf-8",
    )


def _client_with_fixture(temp_app_env: Path, tmp_path: Path, monkeypatch):
    repo_root = tmp_path / "repo"
    _write_knowledge_fixture(temp_app_env, repo_root)
    monkeypatch.setenv("INKDESK_REPO_ROOT", str(repo_root))
    get_settings.cache_clear()
    from inkdesk_server.main import create_app

    return TestClient(create_app())


def test_knowledge_topics_are_stable_traceable_summaries(temp_app_env: Path, tmp_path: Path, monkeypatch) -> None:
    with _client_with_fixture(temp_app_env, tmp_path, monkeypatch) as client:
        payload = {"topics": []}
        for _ in range(50):
            response = client.get("/api/knowledge/topics")
            assert response.status_code == 200
            payload = response.json()
            if payload["topics"]:
                break
            sleep(0.02)

    topics = payload["topics"]
    assert {topic["title"] for topic in topics} == {"Architecture Decisions", "Codex Host Adapter"}
    assert payload["stats"]["topicCount"] == 2
    assert payload["stats"]["sourceCount"] == 1
    assert payload["stats"]["signalCount"] >= 4

    host = next(topic for topic in topics if topic["title"] == "Codex Host Adapter")
    assert re.fullmatch(r"topic-[a-f0-9]{16}", host["id"])
    assert host["sourceCount"] == 1
    assert host["openQuestionCount"] == 2
    assert {signal["type"] for signal in host["signals"]} >= {
        "stale",
        "unsupported",
        "conflicting",
        "open_question",
    }
    assert host["updatedAt"].endswith("+00:00")
    assert host["sourceCoverage"] == "supported"
    assert host["provenanceStatus"] == "supported"


def test_knowledge_search_returns_topic_briefings_in_scope(temp_app_env: Path, tmp_path: Path, monkeypatch) -> None:
    with _client_with_fixture(temp_app_env, tmp_path, monkeypatch) as client:
        client.get("/api/knowledge/topics")
        vault_result = client.get(
            "/api/knowledge/search",
            params={"q": "independent fallback", "scope": "vault"},
        )
        repo_result = client.get(
            "/api/knowledge/search",
            params={"q": "graph index", "scope": "repo"},
        )
        invalid_scope = client.get(
            "/api/knowledge/search",
            params={"q": "graph", "scope": "elsewhere"},
        )

    assert vault_result.status_code == 200
    assert vault_result.json()["query"] == "independent fallback"
    assert [item["title"] for item in vault_result.json()["results"]] == ["Codex Host Adapter"]
    assert [item["title"] for item in repo_result.json()["results"]] == ["Architecture Decisions"]
    assert invalid_scope.status_code == 400
    assert invalid_scope.json()["code"] == "INVALID_KNOWLEDGE_SCOPE"


def test_knowledge_briefing_and_sources_preserve_provenance(temp_app_env: Path, tmp_path: Path, monkeypatch) -> None:
    with _client_with_fixture(temp_app_env, tmp_path, monkeypatch) as client:
        topics = client.get("/api/knowledge/topics").json()["topics"]
        host = next(topic for topic in topics if topic["title"] == "Codex Host Adapter")
        briefing_response = client.get(f"/api/knowledge/topics/{host['id']}/briefing")
        sources_response = client.get(f"/api/knowledge/topics/{host['id']}/sources")
        missing_response = client.get("/api/knowledge/topics/topic-0000000000000000/briefing")

    assert briefing_response.status_code == 200
    briefing = briefing_response.json()
    assert briefing["topicId"] == host["id"]
    assert briefing["title"] == "Codex Host Adapter"
    assert "CDP is an optional host adapter." in briefing["currentUnderstanding"]
    assert briefing["keyDecisions"] == ["Business truth stays in the Inkdesk service."]
    assert briefing["codePaths"] == ["scripts/codex/injector.mjs"]
    assert set(briefing["openQuestions"]) == {
        "Which renderer selectors remain stable?",
        "Can a second Codex instance always be launched?",
    }
    assert briefing["sources"][0]["title"] == "Host Research"
    source = briefing["sources"][0]
    assert re.fullmatch(r"vault:wiki/host-research\.md", source["documentId"])
    assert source["href"].startswith("/api/knowledge/documents/")
    assert source["locator"]["heading"] == "Host Research"
    assert source["locator"]["startLine"] == 1
    assert source["excerpt"] == "The iframe and CSP bypass probes succeeded."
    assert re.fullmatch(r"[a-f0-9]{64}", source["contentHash"])
    assert source["sourceCoverage"] == "supported"
    assert source["provenanceStatus"] == "supported"
    assert briefing["relatedTopics"] == []
    assert 0.0 <= briefing["confidence"] <= 1.0
    assert {signal["type"] for signal in briefing["signals"]} >= {"unsupported", "conflicting"}
    assert briefing["sourceCoverage"] == "supported"
    assert briefing["provenanceStatus"] == "supported"

    architecture = next(topic for topic in topics if topic["title"] == "Architecture Decisions")
    architecture_briefing = client.get(f"/api/knowledge/topics/{architecture['id']}/briefing").json()
    assert architecture_briefing["sourceCoverage"] == "none"
    assert architecture_briefing["provenanceStatus"] == "unsupported"
    assert architecture_briefing["confidence"] <= 0.25

    source_payload = sources_response.json()
    assert source_payload["topicId"] == host["id"]
    assert source_payload["sources"] == briefing["sources"]
    assert source_payload["sources"][0]["path"] == "wiki/host-research.md"
    assert missing_response.status_code == 404


def test_knowledge_stream_emits_version_only_invalidation(temp_app_env: Path, tmp_path: Path, monkeypatch) -> None:
    with _client_with_fixture(temp_app_env, tmp_path, monkeypatch) as client:
        client.get("/api/knowledge/topics")
        response = client.get("/api/knowledge/stream?once=true")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text.startswith("event: knowledge.updated\n")
    payload = json.loads(response.text.split("data: ", 1)[1])
    assert payload == {"type": "knowledge.updated", "version": payload["version"]}
    assert payload["version"] != "empty"
