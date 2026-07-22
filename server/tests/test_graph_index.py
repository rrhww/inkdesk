from __future__ import annotations

import asyncio
import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter, sleep
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from watchdog.events import FileModifiedEvent

from inkdesk_server.core.config import get_settings
from inkdesk_server.graph_index import DirectoryScanner, GraphEventBus, GraphNode, GraphSnapshot, MarkdownChangeHandler


def test_directory_scanner_builds_file_backed_graph(
    temp_app_env: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    wiki_root = temp_app_env / "wiki"
    wiki_root.mkdir(parents=True)
    repo_root.mkdir()
    (wiki_root / "core.md").write_text(
        "---\ntitle: Core Concept\ntype: concept\nstatus: stable\n---\n# Core Concept\nLinks to [[api-contract]] and [[missing-node]].\n",
        encoding="utf-8",
    )
    (wiki_root / "api-contract.md").write_text(
        "---\ntitle: API Contract\ntype: interface\n---\n# API Contract\nThe public boundary.\n",
        encoding="utf-8",
    )
    (repo_root / "tech-solution.md").write_text(
        "---\ntitle: Streaming Solution\ntype: tech-solution\n---\n# Streaming Solution\nDepends on [[Core Concept]].\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("INKDESK_REPO_ROOT", str(repo_root))
    get_settings.cache_clear()

    scanner = DirectoryScanner(get_settings())
    first = scanner.scan()

    nodes = {node.label: node for node in first.nodes}
    assert nodes["Core Concept"].kind == "concept"
    assert nodes["API Contract"].kind == "class"
    assert nodes["Streaming Solution"].kind == "solution"
    assert any(node.kind == "missing" and node.label == "missing-node" for node in first.nodes)
    assert any(edge.source == nodes["Core Concept"].id and edge.target == nodes["API Contract"].id for edge in first.edges)
    assert scanner.snapshot_path.is_file()

    (repo_root / "tech-solution.md").unlink()
    second = scanner.scan()
    assert second.version != first.version

    assert scanner.read_document(nodes["Core Concept"]).startswith("---\ntitle: Core Concept")
    with pytest.raises(FileNotFoundError):
        scanner.read_document(
            GraphNode(
                id="vault:../secret.md",
                label="Secret",
                kind="document",
                path="../secret.md",
                source="vault",
                status="indexed",
                summary="",
            )
        )


def test_graph_api_filters_vault_nodes_and_reads_snapshot_documents(temp_app_env: Path) -> None:
    from inkdesk_server.main import create_app

    wiki_root = temp_app_env / "wiki"
    wiki_root.mkdir(parents=True)
    (wiki_root / "core.md").write_text(
        "---\ntitle: Core Concept\ntype: concept\n---\n# Core Concept\nLinks to [[api-contract]].\n",
        encoding="utf-8",
    )
    (wiki_root / "api-contract.md").write_text(
        "---\ntitle: API Contract\ntype: interface\n---\n# API Contract\nThe public boundary.\n",
        encoding="utf-8",
    )

    with TestClient(create_app()) as client:
        payload = {"nodes": []}
        for _ in range(50):
            response = client.get("/api/graph", params={"source": "vault"})
            assert response.status_code == 200
            payload = response.json()
            if payload["nodes"]:
                break
            sleep(0.02)

        assert {node["label"] for node in payload["nodes"]} == {"API Contract", "Core Concept"}
        assert len(payload["edges"]) == 1

        core_node = next(node for node in payload["nodes"] if node["label"] == "Core Concept")
        document = client.get("/api/graph/document", params={"nodeId": core_node["id"]})
        assert document.status_code == 200
        assert document.json()["sourcePath"] == "wiki/core.md"
        assert "Links to [[api-contract]]" in document.json()["content"]

        unknown = client.get("/api/graph/document", params={"nodeId": "vault:../secret.md"})
        assert unknown.status_code == 404


def test_graph_api_starts_without_a_database(temp_app_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INKDESK_DB_URL", "postgresql+psycopg://unavailable.invalid/inkdesk")
    get_settings.cache_clear()
    from inkdesk_server.main import create_app

    with TestClient(create_app()) as client:
        assert client.get("/health").json() == {"status": "ok", "state": "in-memory"}
        assert client.get("/api/graph").status_code == 200


@pytest.mark.asyncio
async def test_graph_event_bus_delivers_cross_thread_update_under_ttft_budget() -> None:
    bus = GraphEventBus()
    bus.attach_loop(asyncio.get_running_loop())
    queue = bus.subscribe()
    snapshot = GraphSnapshot(
        version="v1",
        generated_at=datetime.now(UTC).isoformat(),
        nodes=(GraphNode("vault:wiki/core.md", "Core", "concept", "wiki/core.md", "vault", "stable", ""),),
        edges=(),
    )

    started = perf_counter()
    publisher = threading.Thread(target=bus.publish, args=(snapshot, "test"))
    publisher.start()
    publisher.join()
    event = await asyncio.wait_for(queue.get(), timeout=0.18)

    assert perf_counter() - started < 0.18
    assert event["event"] == "graph.updated"
    assert event["snapshot"]["version"] == "v1"
    bus.unsubscribe(queue)


def test_graph_sse_emits_memory_snapshot_without_waiting_for_scan(temp_app_env: Path) -> None:
    from inkdesk_server.main import create_app

    wiki_root = temp_app_env / "wiki"
    wiki_root.mkdir(parents=True)
    (wiki_root / "core.md").write_text("# Core\n", encoding="utf-8")

    with TestClient(create_app()) as client:
        client.get("/api/graph")
        started = perf_counter()
        response = client.get("/api/graph/stream?once=true&source=vault")
        elapsed = perf_counter() - started
        invalid = client.get("/api/graph/stream?once=true&source=unknown")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text.startswith("event: graph.snapshot\n")
    payload = json.loads(response.text.split("data: ", 1)[1])
    assert payload["nodes"]
    assert {node["source"] for node in payload["nodes"]} == {"vault"}
    assert invalid.status_code == 400
    assert elapsed < 0.18


def test_markdown_event_handler_ignores_non_markdown_changes() -> None:
    runtime = Mock()
    handler = MarkdownChangeHandler(runtime)

    handler.on_any_event(FileModifiedEvent("C:/repo/module.py"))
    handler.on_any_event(FileModifiedEvent("C:/repo/tech-solution.md"))

    runtime.schedule_refresh.assert_called_once_with("modified:tech-solution.md")
