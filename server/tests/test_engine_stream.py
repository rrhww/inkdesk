from __future__ import annotations

from time import perf_counter

import pytest
from fastapi.testclient import TestClient

from inkdesk_server.core.config import get_settings
from inkdesk_server.engine import EngineRuntime
from inkdesk_server.graph_index import GraphSnapshot
from inkdesk_server.schemas import EngineCommandRequest, EngineTaskRequest


@pytest.mark.asyncio
async def test_engine_stream_opens_before_execution_and_uses_two_ordered_queues(temp_app_env) -> None:
    runtime = EngineRuntime(get_settings(), GraphSnapshot.empty)
    request = EngineCommandRequest(
        command="analyze the repository",
        tasks=[
            EngineTaskRequest(id="kb", kind="kb_match"),
            EngineTaskRequest(id="repo", kind="repo_analysis"),
            EngineTaskRequest(id="merge", kind="synthesis", dependencies=["kb", "repo"]),
        ],
    )

    started = perf_counter()
    stream = runtime.stream(request)
    first = await anext(stream)
    ttft = perf_counter() - started
    remaining = [item async for item in stream]
    await runtime.close()

    items = [first, *remaining]
    assert first.event == "stream.open"
    assert ttft < 0.18
    assert any(item.event == "token" for item in items)
    assert any(item.event == "result" for item in items)
    assert items[-1].event == "stream.end"
    sequences = [int(item.data["sequence"]) for item in items]
    assert sequences == list(range(1, len(sequences) + 1))
    result = next(item for item in items if item.event == "result")
    assert result.data["completedOrder"][-1] == "merge"


def test_engine_sse_endpoint_streams_default_parallel_plan_without_job_tables(temp_app_env) -> None:
    from inkdesk_server.main import create_app

    with TestClient(create_app()) as client:
        response = client.post("/api/engine/stream", json={"command": "inspect graph security"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text.startswith("event: stream.open\n")
    assert "event: token\n" in response.text
    assert "event: result\n" in response.text
    assert "event: stream.end\n" in response.text


def test_engine_rejects_old_persisted_job_payload_shape(temp_app_env) -> None:
    from inkdesk_server.main import create_app

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/engine/stream",
            json={"command": "x", "jobId": "legacy", "databaseLock": True},
        )

    assert response.status_code == 422
