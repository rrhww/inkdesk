from __future__ import annotations

import asyncio
import json
from pathlib import Path
from time import perf_counter

import pytest
import httpx
from fastapi.testclient import TestClient

from inkdesk_server.core.config import get_settings
from inkdesk_server.graph_index import GraphIndexRuntime
from inkdesk_server.schemas import SkillRunInputs, SkillRunRequest
from inkdesk_server.tech_solution import (
    SkillExecutionError,
    TechSolutionRuntime,
    _safe_relative_repo_path,
    validate_solution_document,
)


def request_for(path: Path, title: str = "Mock Interview") -> SkillRunRequest:
    return SkillRunRequest(
        inputs=SkillRunInputs(
            requirement="# Mock Interview\n\nBuild an observable interview workflow.",
            sourcePath=str(path),
            sourceTitle=title,
        ),
        maxConcurrency=4,
    )


async def collect(runtime: TechSolutionRuntime, request: SkillRunRequest):
    return [item async for item in runtime.stream(request)]


def configure_repo(monkeypatch: pytest.MonkeyPatch, repo_root: Path) -> None:
    monkeypatch.setenv("INKDESK_REPO_ROOT", str(repo_root))
    get_settings.cache_clear()


def configure_provider(monkeypatch: pytest.MonkeyPatch, repo_root: Path) -> None:
    configure_repo(monkeypatch, repo_root)
    monkeypatch.setenv("INKDESK_AGENT_RUNTIME", "provider")
    monkeypatch.setenv("INKDESK_AGENT_API_KEY", "test-key")
    get_settings.cache_clear()


def test_skill_contract_is_active_and_uses_generated_proposal_path() -> None:
    contract_path = Path(__file__).parents[1] / "vault" / "skills" / "tech-solution" / "contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    assert contract["status"] == "active"
    assert contract["outputs"][0]["location"] == "wiki/generated/<prd-stem>-tech-solution.md"
    assert contract["writePolicy"]["canonicalWiki"] == "proposal-only"
    assert all(item["name"] != "dev_run" for item in contract["contextRequirements"])


def test_skill_runtime_loads_bounded_reference_and_template_resources(temp_app_env) -> None:
    settings = get_settings()
    runtime = TechSolutionRuntime(settings, lambda: GraphIndexRuntime(settings).current(), lambda _: None)

    context = runtime._skill_context()

    assert "references/architecture-patterns.md" in context
    assert "templates/solution-template.md" in context
    assert "sequenceDiagram" in context


def test_skill_hard_gate_requires_initialized_vault(temp_app_env, tmp_path) -> None:
    settings = get_settings()
    runtime = TechSolutionRuntime(settings, lambda: GraphIndexRuntime(settings).current(), lambda _: None)
    temp_app_env.rmdir()

    with pytest.raises(SkillExecutionError) as error:
        runtime.preflight("tech-solution", request_for(tmp_path / "prd.md"))

    assert error.value.code == "VAULT_NOT_INITIALIZED"


def test_tech_solution_dag_has_four_parallel_investigations_before_synthesis(temp_app_env) -> None:
    settings = get_settings()
    runtime = TechSolutionRuntime(settings, lambda: GraphIndexRuntime(settings).current(), lambda _: None)
    tasks = runtime._build_tasks()

    assert [task.id for task in tasks[:4]] == [
        "requirement-analysis",
        "knowledge-analysis",
        "repository-analysis",
        "security-analysis",
    ]
    assert set(tasks[-1].dependencies) == {task.id for task in tasks[:4]}


@pytest.mark.asyncio
async def test_deterministic_skill_writes_valid_artifact_and_refreshes_graph(
    temp_app_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    prd = repo_root / "examples" / "mock-interview-prd.md"
    prd.parent.mkdir(parents=True)
    prd.write_text("# Mock Interview\n\nBuild an observable interview workflow.\n", encoding="utf-8")
    configure_repo(monkeypatch, repo_root)
    settings = get_settings()
    graph = GraphIndexRuntime(settings)
    graph.refresh("test")
    runtime_events: list[tuple[str, dict]] = []
    runtime = TechSolutionRuntime(
        settings,
        graph.current,
        graph.refresh,
        lambda event, data: runtime_events.append((event, dict(data))),
    )
    runtime.preflight("tech-solution", request_for(prd))

    events = await collect(runtime, request_for(prd))
    await runtime.close()
    graph.stop()

    names = [item.event for item in events]
    assert names[0] == "stream.open"
    assert names[-1] == "stream.end"
    assert "artifact.validated" in names
    assert "artifact.written" in names
    assert "result" in names
    result = next(item for item in events if item.event == "result")
    artifact = Path(str(result.data["artifactPath"]))
    assert artifact == temp_app_env / "wiki" / "generated" / "mock-interview-prd-tech-solution.md"
    content = artifact.read_text(encoding="utf-8")
    assert validate_solution_document(content, "examples/mock-interview-prd.md") == []

    snapshot = graph.current()
    solution_id = "vault:wiki/generated/mock-interview-prd-tech-solution.md"
    prd_id = "repo:examples/mock-interview-prd.md"
    assert any(node.id == solution_id and node.kind == "solution" for node in snapshot.nodes)
    assert any(edge.source == solution_id and edge.target == prd_id for edge in snapshot.edges)
    assert runtime_events[0] == ("node.active", {"nodeId": prd_id, "skillId": "tech-solution"})
    assert runtime_events[-1] == ("node.idle", {"nodeId": prd_id, "skillId": "tech-solution"})


@pytest.mark.asyncio
async def test_investigations_really_run_concurrently_and_synthesis_waits(
    temp_app_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    prd = repo_root / "mock.md"
    repo_root.mkdir()
    prd.write_text("# Mock\n", encoding="utf-8")
    configure_repo(monkeypatch, repo_root)
    settings = get_settings()
    graph = GraphIndexRuntime(settings)
    graph.refresh("test")
    runtime = TechSolutionRuntime(settings, graph.current, graph.refresh)
    original = runtime._task_tokens
    started: dict[str, float] = {}
    finished: dict[str, float] = {}

    async def delayed(task, request, dependencies, source_reference):
        started[task.id] = perf_counter()
        if task.id != "synthesis":
            await asyncio.sleep(0.04)
        async for token in original(task, request, dependencies, source_reference):
            yield token
        finished[task.id] = perf_counter()

    monkeypatch.setattr(runtime, "_task_tokens", delayed)
    events = await collect(runtime, request_for(prd, "Mock"))
    await runtime.close()
    graph.stop()

    assert not any(item.event == "stream.error" for item in events)
    investigations = [
        "requirement-analysis",
        "knowledge-analysis",
        "repository-analysis",
        "security-analysis",
    ]
    assert max(started[name] for name in investigations) - min(started[name] for name in investigations) < 0.03
    assert started["synthesis"] >= max(finished[name] for name in investigations)


def test_provider_mode_fails_preflight_without_api_key(temp_app_env, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INKDESK_AGENT_RUNTIME", "langgraph")
    monkeypatch.setenv("INKDESK_AGENT_API_KEY", "")
    get_settings.cache_clear()
    settings = get_settings()
    runtime = TechSolutionRuntime(settings, lambda: GraphIndexRuntime(settings).current(), lambda _: None)

    with pytest.raises(SkillExecutionError) as error:
        runtime.preflight("tech-solution", request_for(tmp_path / "prd.md"))

    assert error.value.code == "PROVIDER_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_provider_gets_one_repair_attempt_before_writing(
    temp_app_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    prd = repo_root / "prd.md"
    prd.write_text("# PRD\n", encoding="utf-8")
    configure_provider(monkeypatch, repo_root)
    settings = get_settings()
    graph = GraphIndexRuntime(settings)
    graph.refresh("test")
    runtime = TechSolutionRuntime(settings, graph.current, graph.refresh)
    request = request_for(prd, "PRD")
    valid = runtime._deterministic_document(request, {}, "prd.md")
    repair_calls = 0

    async def provider_tokens(prompt: str):
        nonlocal repair_calls
        if prompt.startswith("Repair this Markdown"):
            repair_calls += 1
            yield valid
        elif prompt.startswith("Write a complete Chinese Markdown"):
            yield "# incomplete"
        else:
            yield "analysis"

    monkeypatch.setattr(runtime, "_provider_tokens", provider_tokens)
    runtime.preflight("tech-solution", request)
    events = await collect(runtime, request)
    await runtime.close()
    graph.stop()

    assert repair_calls == 1
    validated = next(item for item in events if item.event == "artifact.validated")
    assert validated.data["repaired"] is True
    assert (temp_app_env / "wiki" / "generated" / "prd-tech-solution.md").is_file()


@pytest.mark.asyncio
async def test_provider_second_invalid_output_fails_closed_without_artifact(
    temp_app_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    prd = repo_root / "prd.md"
    prd.write_text("# PRD\n", encoding="utf-8")
    configure_provider(monkeypatch, repo_root)
    settings = get_settings()
    graph = GraphIndexRuntime(settings)
    graph.refresh("test")
    runtime = TechSolutionRuntime(settings, graph.current, graph.refresh)

    async def invalid_tokens(_prompt: str):
        yield "# still incomplete"

    monkeypatch.setattr(runtime, "_provider_tokens", invalid_tokens)
    events = await collect(runtime, request_for(prd, "PRD"))
    await runtime.close()
    graph.stop()

    error = next(item for item in events if item.event == "stream.error")
    assert error.data["code"] == "ARTIFACT_VALIDATION_FAILED"
    assert not (temp_app_env / "wiki" / "generated" / "prd-tech-solution.md").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [429, 503])
async def test_provider_http_failures_use_stable_stream_error(
    temp_app_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    status_code: int,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    prd = repo_root / "prd.md"
    prd.write_text("# PRD\n", encoding="utf-8")
    configure_provider(monkeypatch, repo_root)
    settings = get_settings()
    graph = GraphIndexRuntime(settings)
    graph.refresh("test")
    runtime = TechSolutionRuntime(settings, graph.current, graph.refresh)

    async def failed_tokens(_prompt: str):
        request = httpx.Request("POST", "https://provider.example/chat/completions")
        response = httpx.Response(status_code, request=request)
        raise httpx.HTTPStatusError("provider failed", request=request, response=response)
        yield "unreachable"

    monkeypatch.setattr(runtime, "_provider_tokens", failed_tokens)
    events = await collect(runtime, request_for(prd, "PRD"))
    await runtime.close()
    graph.stop()

    error = next(item for item in events if item.event == "stream.error")
    assert error.data == {
        "sequence": error.data["sequence"],
        "code": "PROVIDER_ERROR",
        "message": f"Provider request failed with HTTP {status_code}.",
    }


@pytest.mark.asyncio
async def test_provider_timeout_uses_stable_stream_error(
    temp_app_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    prd = repo_root / "prd.md"
    prd.write_text("# PRD\n", encoding="utf-8")
    configure_provider(monkeypatch, repo_root)
    settings = get_settings()
    graph = GraphIndexRuntime(settings)
    graph.refresh("test")
    runtime = TechSolutionRuntime(settings, graph.current, graph.refresh)

    async def timed_out(_prompt: str):
        raise httpx.ReadTimeout("timeout")
        yield "unreachable"

    monkeypatch.setattr(runtime, "_provider_tokens", timed_out)
    events = await collect(runtime, request_for(prd, "PRD"))
    await runtime.close()
    graph.stop()

    error = next(item for item in events if item.event == "stream.error")
    assert error.data["code"] == "PROVIDER_ERROR"
    assert error.data["message"] == "Provider request failed."


@pytest.mark.asyncio
async def test_artifact_conflict_returns_stable_error_and_preserves_existing_file(
    temp_app_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    prd = repo_root / "prd.md"
    prd.write_text("# PRD\n", encoding="utf-8")
    configure_repo(monkeypatch, repo_root)
    target = temp_app_env / "wiki" / "generated" / "prd-tech-solution.md"
    target.parent.mkdir(parents=True)
    original = "---\ntitle: Human document\n---\n# Keep me\n"
    target.write_text(original, encoding="utf-8")
    settings = get_settings()
    graph = GraphIndexRuntime(settings)
    graph.refresh("test")
    runtime = TechSolutionRuntime(settings, graph.current, graph.refresh)

    events = await collect(runtime, request_for(prd, "PRD"))
    await runtime.close()
    graph.stop()

    error = next(item for item in events if item.event == "stream.error")
    assert error.data["code"] == "ARTIFACT_CONFLICT"
    assert target.read_text(encoding="utf-8") == original
    assert not list(target.parent.glob("*.tmp"))


def test_context_path_policy_skips_secrets_dependencies_and_binary_files() -> None:
    assert _safe_relative_repo_path("src/service.py")
    assert not _safe_relative_repo_path(".env")
    assert not _safe_relative_repo_path("config/production.secrets.yaml")
    assert not _safe_relative_repo_path("node_modules/lib/index.js")
    assert not _safe_relative_repo_path("build/app.jar")
    assert not _safe_relative_repo_path("../outside.py")


def test_skill_api_returns_structured_preflight_errors_and_named_sse(temp_app_env, tmp_path) -> None:
    from inkdesk_server.main import create_app

    payload = request_for(tmp_path / "api-prd.md").model_dump()
    with TestClient(create_app()) as client:
        missing = client.post("/api/skills/unknown/stream", json=payload)
        success = client.post("/api/skills/tech-solution/stream", json=payload)

    assert missing.status_code == 404
    assert missing.json()["code"] == "SKILL_NOT_FOUND"
    assert success.status_code == 200
    assert success.headers["content-type"].startswith("text/event-stream")
    assert success.text.startswith("event: stream.open\n")
    assert "event: artifact.validated\n" in success.text
    assert "event: artifact.written\n" in success.text
    assert "event: result\n" in success.text
    assert success.text.endswith("event: stream.end\ndata:") is False


def test_solution_validation_rejects_partial_or_mismatched_output() -> None:
    findings = validate_solution_document(
        "---\ntitle: Bad\ngeneratedBy: someone-else\nsource: other.md\n---\n# Bad\n",
        "prd.md",
    )

    assert "generatedBy must be inkdesk" in findings
    assert "source does not match the PRD" in findings
    assert "missing Mermaid sequenceDiagram" in findings


def test_atomic_write_failure_leaves_no_partial_file(
    temp_app_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    prd = repo_root / "prd.md"
    prd.write_text("# PRD\n", encoding="utf-8")
    configure_repo(monkeypatch, repo_root)
    settings = get_settings()
    runtime = TechSolutionRuntime(settings, lambda: GraphIndexRuntime(settings).current(), lambda _: None)
    request = request_for(prd, "PRD")
    document = runtime._deterministic_document(request, {}, "prd.md")

    def fail_replace(_source, _target):
        raise OSError("disk failed")

    monkeypatch.setattr("inkdesk_server.tech_solution.os.replace", fail_replace)
    with pytest.raises(SkillExecutionError) as error:
        runtime._write_artifact(document, request, "prd.md")

    output_dir = temp_app_env / "wiki" / "generated"
    assert error.value.code == "ARTIFACT_WRITE_FAILED"
    assert not (output_dir / "prd-tech-solution.md").exists()
    assert not list(output_dir.glob("*.tmp"))
