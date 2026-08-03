from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

import pytest

from inkdesk_server.harness.evidence import EvidenceCollector
from inkdesk_server.harness.evidence_ledger import EvidenceLedger
from inkdesk_server.harness.permissions import PermissionBroker, PermissionError
from inkdesk_server.harness.run_store import RunStore
from inkdesk_server.harness.tool_policy import ReadOnlyAuditToolPolicy, ToolDecision
from inkdesk_server.harness.workspace import WorkspaceManager


def _repo(path: Path) -> Path:
    path.mkdir()
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    subprocess.run(["git", "config", "rrhww.useUpstreamCommitStyle", "true"], cwd=path, check=True)
    (path / "README.md").write_text("# Fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "test: fixture"], cwd=path, check=True, capture_output=True)
    return path


def test_read_only_policy_enforces_paths_commands_and_review_boundary(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    policy = ReadOnlyAuditToolPolicy(workspace)

    assert policy.evaluate("Read", {"file_path": str(workspace / "README.md")}).decision == ToolDecision.ALLOW
    assert policy.evaluate("Read", {"file_path": str(tmp_path / "secret.txt")}).decision == ToolDecision.DENY
    assert policy.evaluate("Read", {"file_path": str(workspace / ".env")}).decision == ToolDecision.DENY
    assert policy.evaluate("Glob", {"pattern": "../**/*.py"}).decision == ToolDecision.DENY
    assert policy.evaluate("Glob", {"pattern": str(tmp_path / "**" / "*.py")}).decision == ToolDecision.DENY
    assert policy.evaluate("Bash", {"command": "git status --short"}).decision == ToolDecision.ALLOW
    assert policy.evaluate(
        "Bash", {"command": f'git -C "{workspace}" status --short'}
    ).decision == ToolDecision.ALLOW
    assert policy.evaluate(
        "Bash", {"command": f'git -C "{tmp_path}" status --short'}
    ).decision == ToolDecision.DENY
    assert policy.evaluate("Bash", {"command": "git commit -am unsafe"}).decision == ToolDecision.DENY
    assert policy.evaluate("Bash", {"command": "git -C $HOME status"}).decision == ToolDecision.DENY
    assert policy.evaluate("Bash", {"command": "git log --paginate"}).decision == ToolDecision.DENY
    assert policy.evaluate("Bash", {"command": "rg TODO | head"}).decision == ToolDecision.DENY
    assert policy.evaluate("Bash", {"command": "ls"}).decision == ToolDecision.REVIEW
    assert policy.evaluate("WebFetch", {"url": "https://example.com"}).decision == ToolDecision.DENY


@pytest.mark.asyncio
async def test_permission_broker_allows_once_and_rejects_replay() -> None:
    broker = PermissionBroker(timeout_seconds=1)
    record = await broker.request(
        run_id="run-test",
        stage_id="specialist-structure",
        session_id="session-test",
        tool_use_id="tool-test",
        tool="Bash",
        tool_input={"command": "ls"},
    )
    waiter = asyncio.create_task(broker.wait(record.id))
    resolved = await broker.decide(record.id, allow=True)
    assert resolved.status == "allowed"
    assert await waiter is True
    with pytest.raises(PermissionError) as error:
        await broker.decide(record.id, allow=True)
    assert error.value.code == "PERMISSION_NOT_PENDING"


@pytest.mark.asyncio
async def test_permission_broker_expires_to_deny() -> None:
    broker = PermissionBroker(timeout_seconds=0.01)
    record = await broker.request(
        run_id="run-test",
        stage_id="specialist-testing",
        session_id="session-test",
        tool_use_id="tool-test",
        tool="Bash",
        tool_input={"command": "ls"},
    )
    assert await broker.wait(record.id) is False
    assert broker.list("run-test")[0].status == "expired"


def test_workspace_manager_freezes_head_and_removes_worktree(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    (repo / "dirty.txt").write_text("not committed", encoding="utf-8")
    manager = WorkspaceManager(repo, tmp_path / "workspaces")
    lease = manager.acquire("run-test", "specialist-structure", head)
    assert (lease.path / "README.md").is_file()
    assert not (lease.path / "dirty.txt").exists()
    manager.release(lease)
    assert not lease.path.exists()
    worktrees = subprocess.run(
        ["git", "worktree", "list", "--porcelain"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout
    assert str(lease.path) not in worktrees


def test_workspace_manager_startup_preserves_unregistered_directories(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    work_root = tmp_path / "workspaces"
    unrelated = work_root / "operator-owned"
    unrelated.mkdir(parents=True)
    marker = unrelated / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    manager = WorkspaceManager(repo, work_root)

    assert marker.read_text(encoding="utf-8") == "keep"
    manager.close()


@pytest.mark.asyncio
async def test_agent_evidence_is_redacted_before_persistence(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    vault = tmp_path / "vault"
    vault.mkdir()
    store = RunStore(vault)
    run = store.create_run("harness-audit", "fake", {}, EvidenceCollector(repo).current_head())
    bundle = EvidenceCollector(repo).collect(run.id)
    ledger = EvidenceLedger(store, run.id, bundle)

    evidence_id, redacted = await ledger.record_tool_result(
        stage_id="specialist-security",
        session_id="session-test",
        tool_use_id="tool-test",
        tool_name="Read",
        tool_input={"file_path": "config.txt"},
        tool_response={"content": "Authorization: Bearer sk-super-secret-value"},
    )

    assert evidence_id.startswith("E-A-")
    assert "sk-super-secret-value" not in json.dumps(redacted)
    persisted = (vault / ".inkdesk" / "runs" / run.id / "evidence.json").read_text(encoding="utf-8")
    assert "sk-super-secret-value" not in persisted
    assert evidence_id in persisted
