from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from time import perf_counter

import pytest

from inkdesk_server.harness.evidence import EvidenceCollector
from inkdesk_server.harness.models import (
    Finding,
    FindingConfidence,
    FindingDimension,
    FindingSeverity,
    FindingStatus,
    RunStatus,
    StageEffect,
    WorkflowStage,
)
from inkdesk_server.harness.run_store import RunStore
from inkdesk_server.harness.scheduler import WorkflowScheduler


@pytest.mark.asyncio
async def test_workflow_runs_three_specialists_concurrently_before_lead() -> None:
    stages = [
        WorkflowStage("collect", kind="collect"),
        WorkflowStage("structure", dependencies=("collect",), kind="specialist"),
        WorkflowStage("testing", dependencies=("collect",), kind="specialist"),
        WorkflowStage("security", dependencies=("collect",), kind="specialist"),
        WorkflowStage(
            "lead",
            dependencies=("structure", "testing", "security"),
            kind="lead",
        ),
    ]
    started: dict[str, float] = {}
    finished: dict[str, float] = {}
    active_specialists = 0
    peak_specialists = 0

    async def runner(stage, dependencies):
        nonlocal active_specialists, peak_specialists
        started[stage.id] = perf_counter()
        if stage.kind == "specialist":
            active_specialists += 1
            peak_specialists = max(peak_specialists, active_specialists)
            await asyncio.sleep(0.03)
            active_specialists -= 1
        if stage.kind == "lead":
            assert set(dependencies) == {"structure", "testing", "security"}
        finished[stage.id] = perf_counter()
        return {"stage": stage.id}

    result = await WorkflowScheduler(max_concurrency=3).execute(stages, runner)

    assert peak_specialists == 3
    assert started["lead"] >= max(finished[name] for name in ("structure", "testing", "security"))
    assert result.stage_states["lead"] == "succeeded"


@pytest.mark.asyncio
async def test_vault_write_stages_are_serialized() -> None:
    active = 0
    peak = 0

    async def runner(stage, _dependencies):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.02)
        active -= 1
        return stage.id

    await WorkflowScheduler(max_concurrency=2).execute(
        [
            WorkflowStage("write-a", effect=StageEffect.VAULT_WRITE),
            WorkflowStage("write-b", effect=StageEffect.VAULT_WRITE),
        ],
        runner,
    )

    assert peak == 1


@pytest.mark.asyncio
async def test_run_store_persists_monotonic_events_and_reads_after_sequence(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    run = store.create_run("harness-audit", "claude", {"depth": "quick"}, "abc123")

    first = await store.append_event(run.id, "run.opened", {"executor": "claude"})
    second = await store.append_event(run.id, "stage.started", {"stageId": "collect"})

    assert (first.sequence, second.sequence) == (1, 2)
    assert [event.sequence for event in store.read_events(run.id, after=1)] == [2]
    assert (tmp_path / ".inkdesk" / "runs" / run.id / "events.jsonl").is_file()


def test_run_store_marks_running_runs_interrupted_on_startup(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    run = store.create_run("harness-audit", "claude", {}, "abc123")
    store.update_run(run.id, status=RunStatus.RUNNING)

    recovered = RunStore(tmp_path)

    assert recovered.get_run(run.id).status == RunStatus.INTERRUPTED


@pytest.mark.asyncio
async def test_run_store_redacts_real_secrets_without_corrupting_inkdesk_paths(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    run = store.create_run("harness-audit", "claude", {}, "abc123")
    event = await store.append_event(
        run.id,
        "executor.delta",
        {
            "text": "\n".join(
                [
                    "inkdesk-v020 tokenCount=7 secretary",
                    "sk-abcdefghijklmnopqrstuvwxyz012345",
                    "Authorization: Bearer bearer-secret-value",
                    '{"authorization":"Bearer json-secret-value"}',
                    "PASSWORD=hunter2",
                    "DATABASE_URL=postgres://db-user:db-password@example.com/app",
                    "AWS_SECRET_ACCESS_KEY=aws-secret-value",
                    "OPENAI_API_KEY=openai-secret-value",
                    "SERVICE_TOKEN=service-token-value",
                    "https://uri-user:uri-password@example.com/private",
                    "-----BEGIN PRIVATE KEY-----\nprivate-key-material\n-----END PRIVATE KEY-----",
                ]
            ),
            "headers": {"Authorization": "Bearer structured-bearer-secret"},
            "environment": {
                "PASSWORD": "structured-password",
                "DATABASE_URL": "postgres://structured-user:structured-password@example.com/app",
                "AWS_SECRET_ACCESS_KEY": "structured-aws-secret",
                "apiKey": "structured-api-key",
                "accessToken": "structured-access-token",
                "databaseUrl": "postgres://camel-user:camel-password@example.com/app",
                "tokenCount": 7,
                "secretary": "keep-this-value",
            },
        },
    )
    persisted = (tmp_path / ".inkdesk" / "runs" / run.id / "events.jsonl").read_text(encoding="utf-8")
    for secret in (
        "sk-abcdefghijklmnopqrstuvwxyz012345",
        "bearer-secret-value",
        "json-secret-value",
        "hunter2",
        "db-user:db-password",
        "aws-secret-value",
        "openai-secret-value",
        "service-token-value",
        "uri-user:uri-password",
        "private-key-material",
        "structured-bearer-secret",
        "structured-password",
        "structured-user",
        "structured-aws-secret",
        "structured-api-key",
        "structured-access-token",
        "camel-user",
        "camel-password",
    ):
        assert secret not in json.dumps(event.data)
        assert secret not in persisted
    assert "[REDACTED]" in event.data["text"]
    assert "inkdesk-v020 tokenCount=7 secretary" in event.data["text"]
    assert event.data["headers"]["Authorization"] == "[REDACTED]"
    assert event.data["environment"]["tokenCount"] == 7
    assert event.data["environment"]["secretary"] == "keep-this-value"


def test_evidence_collector_stays_inside_tracked_repository_and_redacts_secrets(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "AGENTS.md").write_text(
        "\n".join(
            [
                "Run pytest. token=sk-abcdefghijklmnopqrstuvwxyz",
                "Authorization: Bearer evidence-bearer-secret",
                "PASSWORD=evidence-password",
                "DATABASE_URL=postgres://evidence-user:evidence-db-password@example.com/app",
                "AWS_SECRET_ACCESS_KEY=evidence-aws-secret",
                "-----BEGIN PRIVATE KEY-----",
                "evidence-private-key",
                "-----END PRIVATE KEY-----",
                "Keep inkdesk-v020 tokenCount=7 secretary intact.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("# Demo\n", encoding="utf-8")
    (repo / ".env").write_text("SECRET=do-not-read\n", encoding="utf-8")
    (repo / ".agents").mkdir()
    (repo / ".agents" / "credentials.json").write_text('{"token":"do-not-inventory"}\n', encoding="utf-8")
    (repo / ".agents" / "secrets.yaml").write_text("token: do-not-inventory\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "AGENTS.md", "README.md", ".agents/credentials.json", ".agents/secrets.yaml"],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "commit", "-m", "test(repo): 创建测试夹具"], cwd=repo, check=True, capture_output=True)

    bundle = EvidenceCollector(repo).collect("run-1", depth="quick")

    assert bundle.repoHead
    assert bundle.sessionEvidenceStatus == "unavailable"
    all_evidence = [item for lane in bundle.envelopes.values() for item in lane.evidence]
    assert all(".env" not in item.source for item in all_evidence)
    excerpts = "\n".join(item.excerpt for item in all_evidence)
    assert "credentials.json" not in excerpts
    assert "secrets.yaml" not in excerpts
    for secret in (
        "sk-abcdefghijklmnopqrstuvwxyz",
        "evidence-bearer-secret",
        "evidence-password",
        "evidence-user:evidence-db-password",
        "evidence-aws-secret",
        "evidence-private-key",
    ):
        assert secret not in excerpts
    assert any("[REDACTED]" in item.excerpt for item in all_evidence)
    assert "inkdesk-v020 tokenCount=7 secretary" in excerpts
    assert all(item.repoHead == bundle.repoHead for item in all_evidence)


def test_evidence_collector_reads_frozen_head_not_dirty_worktree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "rrhww.useUpstreamCommitStyle", "true"], cwd=repo, check=True)
    (repo / "README.md").write_text("# Committed\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "test(fixture): freeze evidence"], cwd=repo, check=True, capture_output=True)
    (repo / "README.md").write_text("# Dirty change\n", encoding="utf-8")

    bundle = EvidenceCollector(repo).collect("run-1", depth="quick")
    excerpts = [item.excerpt for envelope in bundle.envelopes.values() for item in envelope.evidence]
    assert any("# Committed" in excerpt for excerpt in excerpts)
    assert all("Dirty change" not in excerpt for excerpt in excerpts)


def test_findings_reject_unknown_evidence_ids() -> None:
    finding = Finding(
        id="F-001",
        dimension=FindingDimension.CHANGE_VALIDATION,
        severity=FindingSeverity.MEDIUM,
        confidence=FindingConfidence.HIGH,
        title="CI is not exercised",
        consequence="Regressions can merge without a repeatable check.",
        causeChain="No workflow evidence was found.",
        owner="repository",
        evidence=["missing-evidence"],
        expectedArtifact="A required CI workflow",
        repairScope="Add one workflow for the supported test commands.",
        verifiers=["A pull request reports the workflow as required and passing."],
        status=FindingStatus.OPEN,
    )

    assert finding.validate_evidence_ids({"present-evidence"}) == ["missing-evidence"]
