from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from inkdesk_server.harness.audit import HarnessAuditRuntime
from inkdesk_server.harness.executor import (
    AgentExecutionRuntime,
    ClaudeExecutor,
    ExecutionRequest,
    ExecutorError,
    ExecutorEvent,
    ExecutorRegistry,
    ExecutorSession,
    FakeExecutor,
    _claude_error_code,
)
from inkdesk_server.harness.models import (
    EvidenceBundle,
    EvidenceEnvelope,
    EvidenceItem,
    EvidenceStatus,
    RunStatus,
)
from inkdesk_server.harness.tool_policy import ReadOnlyAuditToolPolicy


def _git_repo(path: Path) -> Path:
    path.mkdir()
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    subprocess.run(["git", "config", "rrhww.useUpstreamCommitStyle", "true"], cwd=path, check=True)
    (path / "README.md").write_text("# Example\n", encoding="utf-8")
    (path / "AGENTS.md").write_text("# Rules\nRead only.\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "test(fixture): initialize repository"], cwd=path, check=True, capture_output=True)
    return path


@pytest.mark.asyncio
async def test_audit_uses_three_parallel_sessions_then_lead_and_writes_only_vault(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "repo")
    vault = tmp_path / "vault"
    vault.mkdir()
    started: list[str] = []
    active = 0
    max_active = 0

    async def respond(request):
        nonlocal active, max_active
        started.append(request.stageId)
        if request.stageId.startswith("specialist-"):
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.04)
            active -= 1
            return {"specialist": request.profile, "observations": [], "candidateFindings": []}
        assert active == 0
        return {
            "supportTrack": "fixture",
            "dimensionScores": {
                "Task Understanding": 2,
                "Controlled Execution": 2,
                "Change Validation": 1,
                "Reliable Delivery": 1,
                "Learning Capture": 0,
            },
            "findings": [],
        }

    fake = FakeExecutor(respond)
    runtime = HarnessAuditRuntime(
        vault_root=vault,
        repo_root=repo,
        graph_refresh=lambda _: None,
        executor_registry=ExecutorRegistry({"fake": fake}),
    )
    before = subprocess.run(["git", "status", "--porcelain"], cwd=repo, check=True, capture_output=True, text=True).stdout
    run = await runtime.create_run("harness-audit", {"target": "repository", "depth": "quick"}, "fake")
    for _ in range(100):
        current = runtime.store.get_run(run.id)
        if current.status in {RunStatus.SUCCEEDED, RunStatus.FAILED}:
            break
        await asyncio.sleep(0.02)
    await runtime.close()

    current = runtime.store.get_run(run.id)
    assert current.status == RunStatus.SUCCEEDED, current.error
    assert max_active == 3
    assert started[-1] == "lead-reconcile"
    session_timeouts = {session.request.stageId: session.request.timeoutSeconds for session in fake.sessions}
    assert session_timeouts["specialist-structure"] == 360
    assert session_timeouts["specialist-testing"] == 360
    assert session_timeouts["specialist-security"] == 360
    assert session_timeouts["lead-reconcile"] == 300
    evidence_path = vault / ".inkdesk" / "runs" / run.id / "evidence.json"
    assert evidence_path.is_file()
    evidence_event = next(
        event
        for event in runtime.store.read_events(run.id)
        if event.type == "artifact.written" and event.data.get("kind") == "evidence"
    )
    assert evidence_event.data["path"] == f".inkdesk/runs/{run.id}/evidence.json"
    evidence_document = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence_ids = {
        item["id"]
        for envelope in evidence_document["envelopes"].values()
        for item in envelope["evidence"]
    }
    for session in fake.sessions:
        findings_property = "findings" if session.request.stageId == "lead-reconcile" else "candidateFindings"
        evidence_items = session.request.outputSchema["properties"][findings_property]["items"]["properties"]["evidence"]["items"]
        if session.request.stageId == "lead-reconcile":
            assert evidence_items["pattern"] == r"^E-(?:A-)?[A-Fa-f0-9]{12}$"
        else:
            assert evidence_items["pattern"].startswith("^E-")
    assert (vault / ".inkdesk" / "runs" / run.id / "findings.json").is_file()
    assert (vault / ".inkdesk" / "runs" / run.id / "report.md").is_file()
    assert (vault / "wiki" / "generated" / "repo-harness-audit.md").is_file()
    report_event = next(
        event
        for event in runtime.store.read_events(run.id)
        if event.type == "artifact.written" and event.data.get("kind") == "report"
    )
    assert report_event.data["path"] == "wiki/generated/repo-harness-audit.md"
    assert report_event.data["relativePath"] == "wiki/generated/repo-harness-audit.md"
    assert report_event.data["runPath"] == f".inkdesk/runs/{run.id}/report.md"
    assert "[USER_HOME]" not in json.dumps(report_event.data)
    after = subprocess.run(["git", "status", "--porcelain"], cwd=repo, check=True, capture_output=True, text=True).stdout
    assert after == before


@pytest.mark.asyncio
async def test_runtime_close_interrupts_active_executor_sessions(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "repo")
    vault = tmp_path / "vault"
    vault.mkdir()

    class HangingExecutor:
        is_agent_runtime = False

        def __init__(self) -> None:
            self.sessions: list[ExecutorSession] = []
            self.cancelled: set[str] = set()
            self.released = asyncio.Event()

        async def probe(self):
            return {"available": True, "capabilities": []}

        async def start(self, request):
            session = ExecutorSession(f"hanging-{len(self.sessions)}", request)
            self.sessions.append(session)
            return session

        async def stream(self, session):
            await self.released.wait()
            if session.id in self.cancelled:
                raise ExecutorError("EXECUTOR_CANCELLED", "cancelled")
            yield ExecutorEvent(type="result", data={"output": {}})

        async def cancel(self, session):
            self.cancelled.add(session.id)
            self.released.set()

        async def close(self):
            self.released.set()

    executor = HangingExecutor()
    runtime = HarnessAuditRuntime(
        vault_root=vault,
        repo_root=repo,
        graph_refresh=lambda _: None,
        executor_registry=ExecutorRegistry({"hanging": executor}),
    )
    await runtime.create_run("harness-audit", {"target": "repository", "depth": "quick"}, "hanging")
    for _ in range(100):
        if len(executor.sessions) == 3:
            break
        await asyncio.sleep(0.01)

    await asyncio.wait_for(runtime.close(), timeout=1)

    assert len(executor.sessions) == 3
    assert executor.cancelled == {session.id for session in executor.sessions}


def test_run_api_persists_events_and_supports_last_event_id(temp_app_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.main import create_app

    repo = _git_repo(temp_app_env.parent / "repo")
    monkeypatch.setenv("INKDESK_REPO_ROOT", str(repo))
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/runs",
            json={
                "capabilityId": "harness-audit",
                "inputs": {"target": "repository", "depth": "quick"},
                "executor": "deterministic",
            },
        )
        assert response.status_code == 202
        run_id = response.json()["runId"]
        for _ in range(100):
            detail = client.get(f"/api/runs/{run_id}").json()
            if detail["status"] in {"succeeded", "failed", "stale"}:
                break
            import time

            time.sleep(0.02)
        assert detail["status"] == "succeeded", detail.get("error")
        events = client.get(f"/api/runs/{run_id}/events", headers={"Last-Event-ID": "2"})
        assert events.status_code == 200
        assert "id: 1\n" not in events.text
        assert "id: 3\n" in events.text
        assert "event: stream.end\n" in events.text
        assert client.get(f"/api/runs/{run_id}/report").json()["content"].startswith("# repo Harness Audit")
        assert client.get(f"/api/runs/{run_id}/permissions", params={"status": "pending"}).json() == []
        unknown = client.post(
            f"/api/runs/{run_id}/permissions/perm-unknown/decision",
            json={"decision": "allow_once"},
        )
        assert unknown.status_code == 404
        assert unknown.json()["code"] == "PERMISSION_NOT_FOUND"


def test_codex_executor_is_reserved_but_not_claimed() -> None:
    with pytest.raises(ExecutorError, match="later release") as error:
        ExecutorRegistry().get("codex")
    assert error.value.code == "EXECUTOR_NOT_AVAILABLE"


def test_lead_context_keeps_seed_and_referenced_agent_evidence_only() -> None:
    def evidence(evidence_id: str, *, collector: str, excerpt: str) -> EvidenceItem:
        return EvidenceItem(
            id=evidence_id,
            source=f"fixture://{evidence_id}",
            contentHash=evidence_id,
            capturedAt="2026-08-02T00:00:00+00:00",
            repoHead="abc123",
            excerpt=excerpt,
            collector=collector,
            stageId="specialist-structure" if collector == "agent-tool" else None,
            toolName="Read" if collector == "agent-tool" else None,
        )

    seed = evidence("E-seed00000001", collector="deterministic", excerpt="seed evidence")
    referenced = evidence("E-A-reference001", collector="agent-tool", excerpt="referenced evidence")
    unrelated = evidence("E-A-unrelated001", collector="agent-tool", excerpt="unrelated evidence")
    bundle = EvidenceBundle(
        runId="run-test",
        target="repository",
        depth="quick",
        repoHead="abc123",
        capturedAt="2026-08-02T00:00:00+00:00",
        sessionEvidenceStatus=EvidenceStatus.AVAILABLE,
        envelopes={
            "projectHarness": EvidenceEnvelope(
                status=EvidenceStatus.AVAILABLE,
                summaryFacts=["fixture summary"],
                evidence=[seed, referenced, unrelated],
            )
        },
    )
    specialist_outputs = {
        "specialist-structure": {
            "candidateFindings": [{"evidence": [referenced.id]}],
        }
    }

    allowed = HarnessAuditRuntime._lead_evidence_ids(bundle, specialist_outputs)
    view = HarnessAuditRuntime._lead_evidence_view(bundle, specialist_outputs)
    prompt = HarnessAuditRuntime._lead_prompt(bundle, specialist_outputs)
    visible_ids = {
        item["id"]
        for envelope in view["envelopes"].values()
        for item in envelope["evidence"]
    }

    assert allowed == {seed.id, referenced.id}
    assert visible_ids == allowed
    assert seed.id in prompt
    assert referenced.id in prompt
    assert unrelated.id not in prompt
    assert "unrelated evidence" not in prompt


def test_claude_auth_failure_has_stable_error_code() -> None:
    assert _claude_error_code("Not logged in. Please run /login") == "EXECUTOR_AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_claude_executor_loads_only_user_provider_in_safe_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict = {}

    class FakeOptions:
        def __init__(self, **values):
            captured["options"] = values

    class FakeResultMessage:
        is_error = False
        structured_output = {"result": "ok"}

    class FakeAssistantMessage:
        content = []

    class FakeClient:
        def __init__(self, options):
            captured["instance"] = options

        async def connect(self):
            captured["connected"] = True

        async def query(self, prompt):
            captured["prompt"] = prompt

        async def receive_response(self):
            yield FakeAssistantMessage()
            yield FakeResultMessage()

        async def disconnect(self):
            captured["disconnected"] = True

        async def interrupt(self):
            captured["interrupted"] = True

    class FakeHookMatcher:
        def __init__(self, **values):
            self.__dict__.update(values)

    class FakePermissionResultDeny:
        def __init__(self, message=""):
            self.message = message

    placeholder = type("Placeholder", (), {})
    monkeypatch.setitem(
        sys.modules,
        "claude_agent_sdk",
        SimpleNamespace(
            AssistantMessage=FakeAssistantMessage,
            ClaudeAgentOptions=FakeOptions,
            ClaudeSDKClient=FakeClient,
            HookMatcher=FakeHookMatcher,
            PermissionResultDeny=FakePermissionResultDeny,
            ResultMessage=FakeResultMessage,
            StreamEvent=placeholder,
            TextBlock=placeholder,
            __version__="test",
        ),
    )
    monkeypatch.setattr("inkdesk_server.harness.executor.shutil.which", lambda _name: "claude")
    async def noop_emit(_event, _data):
        return None
    async def deny(_tool_use_id, _tool, _input):
        return False
    async def evidence(_tool_use_id, _tool, _input, output):
        return "E-A-000000000000", output
    request = ExecutionRequest(
        runId="run-test",
        stageId="specialist-security",
        evidenceRef=".inkdesk/runs/run-test/evidence.json",
        profile="Security Auditor",
        prompt="Audit the evidence.",
        outputSchema={"type": "object"},
        cwd=str(tmp_path),
        runtime=AgentExecutionRuntime(
            policy=ReadOnlyAuditToolPolicy(tmp_path),
            emit=noop_emit,
            authorize=deny,
            record_evidence=evidence,
        ),
    )

    executor = ClaudeExecutor()
    session = await executor.start(request)
    pre_hook = captured["options"]["hooks"]["PreToolUse"][0].hooks[0]
    denied = await pre_hook(
        {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "unsafe.txt")}, "tool_use_id": "tool-write"},
        "tool-write",
        {"signal": None},
    )
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    invalid_output = await pre_hook(
        {
            "tool_name": "StructuredOutput",
            "tool_input": {"candidateFindings": [{"evidence": ["E-A-deadbeef0000"]}]},
            "tool_use_id": "tool-output",
        },
        "tool-output",
        {"signal": None},
    )
    assert invalid_output["hookSpecificOutput"]["permissionDecision"] == "deny"
    events = [event async for event in executor.stream(session)]

    options = captured["options"]
    assert options["setting_sources"] == ["user"]
    assert options["tools"] == ["Read", "Glob", "Grep", "Bash"]
    assert options["allowed_tools"] == []
    assert options["mcp_servers"] == {}
    assert options["strict_mcp_config"] is True
    assert options["skills"] == []
    assert options["extra_args"] == {
        "safe-mode": None,
        "disable-slash-commands": None,
        "no-session-persistence": None,
    }
    assert "env" not in options
    assert options["permission_mode"] == "default"
    assert captured["connected"] is True
    assert captured["disconnected"] is True
    assert events[-2].data == {"output": {"result": "ok"}}


@pytest.mark.asyncio
async def test_claude_executor_still_denies_real_tools(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    policy = ReadOnlyAuditToolPolicy(tmp_path)
    assert policy.evaluate("Read", {"file_path": str(tmp_path / "README.md")}).decision == "allow"
    assert policy.evaluate("Write", {"file_path": str(tmp_path / "README.md")}).decision == "deny"
    assert policy.evaluate("Task", {"prompt": "delegate"}).decision == "deny"


@pytest.mark.asyncio
async def test_claude_executor_corrects_invalid_evidence_in_same_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict = {"clients": [], "prompts": []}

    class FakeOptions:
        def __init__(self, **values):
            self.values = values
            captured["options"] = values

    class FakeResultMessage:
        def __init__(self, *, error: bool, output=None, result=None):
            self.is_error = error
            self.structured_output = output
            self.result = result
            self.total_cost_usd = None
            self.num_turns = 1
            self.session_id = "provider-session"

    class FakeClient:
        def __init__(self, options):
            self.options = options
            captured["clients"].append(self)

        async def connect(self):
            return None

        async def query(self, prompt):
            captured["prompts"].append(prompt)

        async def receive_response(self):
            if len(captured["prompts"]) == 1:
                yield FakeResultMessage(error=True, result=None)
            else:
                yield FakeResultMessage(error=False, output={"result": "corrected"})

        async def disconnect(self):
            return None

        async def interrupt(self):
            return None

    class FakeHookMatcher:
        def __init__(self, **values):
            self.__dict__.update(values)

    class FakePermissionResultDeny:
        def __init__(self, message=""):
            self.message = message

    placeholder = type("Placeholder", (), {})
    monkeypatch.setitem(
        sys.modules,
        "claude_agent_sdk",
        SimpleNamespace(
            AssistantMessage=placeholder,
            ClaudeAgentOptions=FakeOptions,
            ClaudeSDKClient=FakeClient,
            HookMatcher=FakeHookMatcher,
            PermissionResultDeny=FakePermissionResultDeny,
            ResultMessage=FakeResultMessage,
            StreamEvent=placeholder,
            TextBlock=placeholder,
            __version__="test",
        ),
    )
    monkeypatch.setattr("inkdesk_server.harness.executor.shutil.which", lambda _name: "claude")

    async def noop_emit(_event, _data):
        return None

    async def deny(_tool_use_id, _tool, _input):
        return False

    async def evidence(_tool_use_id, _tool, _input, output):
        return "E-A-tool00000001", output

    runtime = AgentExecutionRuntime(
        policy=ReadOnlyAuditToolPolicy(tmp_path),
        emit=noop_emit,
        authorize=deny,
        record_evidence=evidence,
        evidence_ids={"E-seed00000001"},
    )
    executor = ClaudeExecutor()
    session = await executor.start(
        ExecutionRequest(
            runId="run-test",
            stageId="specialist-structure",
            evidenceRef="evidence.json",
            profile="Structure",
            prompt="Audit.",
            outputSchema={"type": "object"},
            cwd=str(tmp_path),
            runtime=runtime,
        )
    )
    pre_hook = captured["options"]["hooks"]["PreToolUse"][0].hooks[0]
    await pre_hook(
        {
            "tool_name": "StructuredOutput",
            "tool_input": {"candidateFindings": [{"evidence": ["E-A-seed00000001"]}]},
            "tool_use_id": "tool-output",
        },
        "tool-output",
        {"signal": None},
    )

    events = [event async for event in executor.stream(session)]

    assert len(captured["clients"]) == 1
    assert len(captured["prompts"]) == 2
    assert "E-A-seed00000001" in captured["prompts"][1]
    assert "E-seed00000001" in captured["prompts"][1]
    assert next(event for event in events if event.type == "result").data["output"] == {"result": "corrected"}
