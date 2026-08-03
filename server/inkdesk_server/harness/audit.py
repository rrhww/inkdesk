from __future__ import annotations

import asyncio
import json
import os
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from inkdesk_server.harness.evidence import EvidenceCollector
from inkdesk_server.harness.evidence_ledger import EvidenceLedger
from inkdesk_server.harness.executor import (
    AgentExecutionRequest,
    AgentExecutionRuntime,
    ExecutorAdapter,
    ExecutorError,
    ExecutorRegistry,
)
from inkdesk_server.harness.models import (
    AuditReport,
    EvidenceBundle,
    Finding,
    FindingDimension,
    PermissionRecord,
    PermissionStatus,
    RunRecord,
    RunStatus,
    StageEffect,
    StageStatus,
    WorkflowExecutionEvent,
    WorkflowStage,
    WorkflowStageResult,
    utc_now,
)
from inkdesk_server.harness.run_store import RunStore
from inkdesk_server.harness.scheduler import WorkflowScheduler
from inkdesk_server.harness.permissions import PermissionBroker, PermissionError
from inkdesk_server.harness.tool_policy import ReadOnlyAuditToolPolicy
from inkdesk_server.harness.workspace import WorkspaceManager


SPECIALISTS = {
    "specialist-structure": "Codebase Onboarding Engineer",
    "specialist-testing": "Test Automation Engineer",
    "specialist-security": "AI-Generated Code Security Auditor",
}
PROFILE_FILES = {
    "Codebase Onboarding Engineer": "codebase-onboarding-engineer.md",
    "Test Automation Engineer": "test-automation-engineer.md",
    "AI-Generated Code Security Auditor": "ai-generated-code-security-auditor.md",
    "Software Architect / Harness Lead": "software-architect.md",
}
DIMENSIONS = tuple(item.value for item in FindingDimension)
TERMINAL_STATUSES = {
    RunStatus.SUCCEEDED,
    RunStatus.FAILED,
    RunStatus.BLOCKED,
    RunStatus.CANCELLED,
    RunStatus.INTERRUPTED,
    RunStatus.STALE,
}


class HarnessAuditError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class HarnessAuditRuntime:
    def __init__(
        self,
        *,
        vault_root: Path,
        repo_root: Path,
        graph_refresh: Callable[[str], Any],
        executor_registry: ExecutorRegistry | None = None,
        work_root: Path | None = None,
    ):
        self.vault_root = Path(vault_root).resolve()
        self.repo_root = Path(repo_root).resolve()
        self.graph_refresh = graph_refresh
        self.store = RunStore(self.vault_root)
        self.executors = executor_registry or ExecutorRegistry()
        self.permissions = PermissionBroker()
        self.workspaces = WorkspaceManager(self.repo_root, work_root)
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._sessions: dict[str, list[tuple[ExecutorAdapter, Any]]] = {}

    async def create_run(self, capability_id: str, inputs: dict[str, Any], executor: str) -> RunRecord:
        if capability_id != "harness-audit":
            raise HarnessAuditError("CAPABILITY_NOT_FOUND", f"Capability not found: {capability_id}")
        depth = str(inputs.get("depth") or "quick")
        target = str(inputs.get("target") or "repository")
        if target != "repository":
            raise HarnessAuditError("INVALID_TARGET", "harness-audit only supports target=repository.")
        if depth not in {"quick", "normal"}:
            raise HarnessAuditError("INVALID_DEPTH", "depth must be quick or normal.")
        requested_repo = inputs.get("repoPath")
        if requested_repo and Path(str(requested_repo)).expanduser().resolve() != self.repo_root:
            raise HarnessAuditError(
                "REPOSITORY_NOT_AUTHORIZED",
                "repoPath must match the server's configured INKDESK_REPO_ROOT.",
            )
        adapter = self.executors.get(executor)
        await adapter.probe()
        collector = EvidenceCollector(self.repo_root)
        head = collector.current_head()
        persisted_inputs = {"target": target, "depth": depth}
        record = self.store.create_run(
            capability_id,
            executor,
            persisted_inputs,
            head,
            source_dirty=collector.is_dirty(),
        )
        record = self.store.update_run(
            record.id,
            stageStates={stage.id: StageStatus.PENDING for stage in self._workflow()},
        )
        cancel_event = asyncio.Event()
        self._cancel_events[record.id] = cancel_event
        task = asyncio.create_task(self._execute(record.id, adapter, cancel_event))
        self._tasks[record.id] = task
        task.add_done_callback(lambda _task, run_id=record.id: self._tasks.pop(run_id, None))
        return record

    async def cancel(self, run_id: str) -> RunRecord:
        record = self.store.get_run(run_id)
        if record.status in TERMINAL_STATUSES:
            return record
        self._cancel_events.setdefault(run_id, asyncio.Event()).set()
        await self.permissions.cancel_run(run_id)
        for adapter, session in self._sessions.get(run_id, []):
            await adapter.cancel(session)
        await self.store.append_event(run_id, "run.cancel.requested", {})
        return self.store.get_run(run_id)

    async def close(self) -> None:
        for event in self._cancel_events.values():
            event.set()
        run_ids = set(self._cancel_events) | set(self._sessions)
        await asyncio.gather(
            *(self.permissions.cancel_run(run_id) for run_id in run_ids),
            return_exceptions=True,
        )
        await asyncio.gather(
            *(
                adapter.cancel(session)
                for sessions in tuple(self._sessions.values())
                for adapter, session in tuple(sessions)
            ),
            return_exceptions=True,
        )
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks.values()), return_exceptions=True)
        await self.executors.close()
        self.workspaces.close()

    def list_permissions(
        self,
        run_id: str,
        status: PermissionStatus | None = None,
    ) -> list[PermissionRecord]:
        self.store.get_run(run_id)
        return self.permissions.list(run_id, status)

    async def decide_permission(
        self,
        run_id: str,
        permission_id: str,
        *,
        allow: bool,
        reason: str | None = None,
    ) -> PermissionRecord:
        self.store.get_run(run_id)
        record = next(
            (item for item in self.permissions.list(run_id) if item.id == permission_id),
            None,
        )
        if record is None:
            raise PermissionError("PERMISSION_NOT_FOUND", "Permission request was not found for this run.")
        updated = await self.permissions.decide(permission_id, allow=allow, reason=reason)
        await self.store.append_event(
            run_id,
            "executor.tool.approved" if allow else "executor.tool_denied",
            updated.model_dump(mode="json"),
        )
        return updated

    async def _execute(
        self,
        run_id: str,
        adapter: ExecutorAdapter,
        cancel_event: asyncio.Event,
    ) -> None:
        record = self.store.update_run(run_id, status=RunStatus.RUNNING)
        await self.store.append_event(
            run_id,
            "run.opened",
            {"executor": record.executor, "repoHead": record.sourceHead, "capabilityId": record.capabilityId},
        )
        stages = self._workflow()
        ledger: EvidenceLedger | None = None

        async def on_event(event: WorkflowExecutionEvent) -> None:
            if not event.stage_id:
                return
            event_type = "stage.succeeded" if event.type == "stage.completed" else event.type
            status = {
                "stage.started": StageStatus.RUNNING,
                "stage.succeeded": StageStatus.SUCCEEDED,
                "stage.failed": StageStatus.FAILED,
            }.get(event_type)
            current = self.store.get_run(run_id)
            states = dict(current.stageStates)
            if status is not None:
                states[event.stage_id] = status
                self.store.update_run(run_id, stageStates=states)
            await self.store.append_event(
                run_id,
                event_type,
                {"stageId": event.stage_id, **dict(event.data)},
            )

        async def runner(
            stage: WorkflowStage,
            dependencies: Mapping[str, WorkflowStageResult],
        ) -> Any:
            nonlocal ledger
            if cancel_event.is_set():
                raise HarnessAuditError("RUN_CANCELLED", "Run was cancelled.")
            if stage.id == "preflight":
                if not (self.repo_root / ".git").exists():
                    raise HarnessAuditError("REPOSITORY_NOT_GIT", "Audit target must be a Git repository.")
                if record.executor == "claude":
                    await self.store.append_event(run_id, "executor.probe.started", {"executor": "claude"})
                    result = await self.executors.probe("claude", live=True)
                    await self.store.append_event(run_id, "executor.probe.completed", result)
                return {"repo": self.repo_root.name}
            if stage.id == "collect-evidence":
                bundle = EvidenceCollector(self.repo_root).collect(
                    run_id,
                    depth=str(record.inputs["depth"]),
                )
                path = self.store.write_json(run_id, "evidence.json", bundle)
                ledger = EvidenceLedger(self.store, run_id, bundle)
                await self.store.append_event(
                    run_id,
                    "artifact.written",
                    {
                        "kind": "evidence",
                        "path": path.relative_to(self.vault_root).as_posix(),
                        "repoHead": bundle.repoHead,
                    },
                )
                return bundle
            if stage.id in SPECIALISTS:
                bundle = dependencies["collect-evidence"].output
                if not getattr(adapter, "is_agent_runtime", False):
                    output = await self._execute_agent(
                        run_id,
                        stage.id,
                        SPECIALISTS[stage.id],
                        adapter,
                        bundle,
                        self._specialist_prompt(SPECIALISTS[stage.id], bundle),
                        _specialist_schema(),
                        workspace=self.repo_root,
                        ledger=ledger,
                    )
                    self._validate_candidate_references(output, bundle)
                    return output
                lease = self.workspaces.acquire(run_id, stage.id, bundle.repoHead)
                await self.store.append_event(
                    run_id,
                    "workspace.prepared",
                    {"stageId": stage.id, "workspaceId": lease.id, "repoHead": lease.repo_head},
                )
                try:
                    output = await self._execute_agent(
                        run_id,
                        stage.id,
                        SPECIALISTS[stage.id],
                        adapter,
                        bundle,
                        self._specialist_prompt(SPECIALISTS[stage.id], bundle),
                        _specialist_schema(),
                        workspace=lease.path,
                        ledger=ledger,
                    )
                    self._validate_candidate_references(output, bundle)
                    return output
                finally:
                    self.workspaces.release(lease)
                    await self.store.append_event(
                        run_id,
                        "workspace.released",
                        {"stageId": stage.id, "workspaceId": lease.id},
                    )
            if stage.id == "lead-reconcile":
                bundle = dependencies["collect-evidence"].output
                specialist_outputs = {
                    key: dependencies[key].output
                    for key in SPECIALISTS
                }
                output = await self._execute_agent(
                    run_id,
                    stage.id,
                    "Software Architect / Harness Lead",
                    adapter,
                    bundle,
                    self._lead_prompt(bundle, specialist_outputs),
                    _lead_schema(self._lead_evidence_ids(bundle, specialist_outputs)),
                    workspace=self.workspaces.work_root,
                    ledger=ledger,
                )
                return self._normalize_report(run_id, bundle, output)
            if stage.id == "validate-findings":
                bundle = dependencies["collect-evidence"].output
                report = dependencies["lead-reconcile"].output
                self._validate_report(report, bundle)
                self.store.write_json(run_id, "findings.json", report)
                for finding in report.findings:
                    await self.store.append_event(
                        run_id,
                        "finding.created",
                        finding.model_dump(mode="json"),
                    )
                await self.store.append_event(
                    run_id,
                    "artifact.validated",
                    {"kind": "findings", "count": len(report.findings)},
                )
                return report
            if stage.id == "write-report":
                report = dependencies["validate-findings"].output
                bundle = dependencies["collect-evidence"].output
                stale = EvidenceCollector(self.repo_root).current_head() != bundle.repoHead
                markdown = self._render_report(report, bundle, stale=stale)
                run_report = self.store.write_text(run_id, "report.md", markdown)
                proposal = self._write_proposal(markdown, run_id, bundle, stale=stale)
                relative_path = proposal.relative_to(self.vault_root).as_posix()
                run_relative_path = run_report.relative_to(self.vault_root).as_posix()
                self.store.update_run(
                    run_id,
                    status=RunStatus.STALE if stale else RunStatus.RUNNING,
                    reportPath=relative_path,
                )
                await self.store.append_event(
                    run_id,
                    "artifact.written",
                    {
                        "kind": "report",
                        "path": relative_path,
                        "relativePath": relative_path,
                        "runPath": run_relative_path,
                        "stale": stale,
                    },
                )
                return {"path": relative_path, "stale": stale}
            if stage.id == "graph-refresh":
                result = dependencies["write-report"].output
                self.graph_refresh(f"harness-audit:{run_id}")
                return result
            raise HarnessAuditError("UNKNOWN_STAGE", f"Unknown workflow stage: {stage.id}")

        try:
            result = await WorkflowScheduler(max_concurrency=3).execute(
                stages,
                runner,
                on_event=on_event,
                cancel_event=cancel_event,
            )
            final = self.store.get_run(run_id)
            status = (
                RunStatus.CANCELLED
                if cancel_event.is_set()
                else RunStatus.STALE if final.status == RunStatus.STALE else RunStatus.SUCCEEDED
            )
            self.store.update_run(
                run_id,
                status=status,
                stageStates=dict(result.stage_states),
            )
            terminal_event = {
                RunStatus.CANCELLED: "run.cancelled",
                RunStatus.STALE: "run.stale",
                RunStatus.SUCCEEDED: "run.succeeded",
            }[status]
            await self.store.append_event(run_id, terminal_event, {"reportPath": self.store.get_run(run_id).reportPath})
        except (HarnessAuditError, ExecutorError) as exc:
            status = RunStatus.CANCELLED if exc.code in {"RUN_CANCELLED", "EXECUTOR_CANCELLED"} else RunStatus.FAILED
            current = self.store.get_run(run_id)
            terminal_stage = StageStatus.CANCELLED if status == RunStatus.CANCELLED else StageStatus.BLOCKED
            states = {
                stage_id: terminal_stage if stage_status in {StageStatus.PENDING, StageStatus.READY} else stage_status
                for stage_id, stage_status in current.stageStates.items()
            }
            self.store.update_run(
                run_id,
                status=status,
                stageStates=states,
                error={"code": exc.code, "message": exc.message},
            )
            await self.store.append_event(run_id, "run.cancelled" if status == RunStatus.CANCELLED else "run.failed", {"code": exc.code, "message": exc.message})
        except asyncio.CancelledError:
            self.store.update_run(run_id, status=RunStatus.INTERRUPTED)
            await self.store.append_event(run_id, "run.interrupted", {})
            raise
        except Exception as exc:
            self.store.update_run(
                run_id,
                status=RunStatus.FAILED,
                error={"code": "HARNESS_INTERNAL_ERROR", "message": str(exc)},
            )
            await self.store.append_event(run_id, "run.failed", {"code": "HARNESS_INTERNAL_ERROR", "message": str(exc)})
        finally:
            active_sessions = tuple(self._sessions.get(run_id, ()))
            if active_sessions:
                await asyncio.gather(
                    *(adapter.cancel(session) for adapter, session in active_sessions),
                    return_exceptions=True,
                )
            await self.store.append_event(run_id, "stream.end", {"status": self.store.get_run(run_id).status.value})
            self._cancel_events.pop(run_id, None)
            self._sessions.pop(run_id, None)

    async def _execute_agent(
        self,
        run_id: str,
        stage_id: str,
        profile: str,
        adapter: ExecutorAdapter,
        bundle: EvidenceBundle,
        prompt: str,
        output_schema: dict[str, Any],
        *,
        workspace: Path,
        ledger: EvidenceLedger | None,
    ) -> dict[str, Any]:
        is_lead = stage_id == "lead-reconcile"
        timeout_seconds = (
            300 if bundle.depth == "quick" else 480
        ) if is_lead else (
            360 if bundle.depth == "quick" else 600
        )
        async def emit(event_type: str, data: dict[str, Any]) -> None:
            persisted_type = "executor.tool_denied" if event_type == "tool_denied" else f"executor.{event_type}"
            await self.store.append_event(
                run_id,
                persisted_type,
                {"stageId": stage_id, "sessionId": session_ref["id"], **data},
            )

        session_ref = {"id": "pending"}

        async def authorize(tool_use_id: str, tool: str, tool_input: dict[str, Any]) -> bool:
            permission = await self.permissions.request(
                run_id=run_id,
                stage_id=stage_id,
                session_id=session_ref["id"],
                tool_use_id=tool_use_id,
                tool=tool,
                tool_input=tool_input,
            )
            await self.store.append_event(
                run_id,
                "executor.tool.requested",
                permission.model_dump(mode="json"),
            )
            allowed = await self.permissions.wait(permission.id)
            return allowed

        async def record_evidence(
            tool_use_id: str,
            tool_name: str,
            tool_input: dict[str, Any],
            tool_response: Any,
        ) -> tuple[str, Any]:
            if ledger is None:
                raise ExecutorError("EVIDENCE_LEDGER_UNAVAILABLE", "Agent evidence ledger is unavailable.")
            evidence_id, redacted = await ledger.record_tool_result(
                stage_id=stage_id,
                session_id=session_ref["id"],
                tool_use_id=tool_use_id,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_response=tool_response,
            )
            runtime.evidence_ids.add(evidence_id)
            return evidence_id, redacted

        runtime = AgentExecutionRuntime(
            policy=ReadOnlyAuditToolPolicy(workspace),
            emit=emit,
            authorize=authorize,
            record_evidence=record_evidence,
            evidence_ids=set(bundle.evidence_ids),
        )
        request = AgentExecutionRequest(
            runId=run_id,
            stageId=stage_id,
            evidenceRef=f".inkdesk/runs/{run_id}/evidence.json",
            evidenceRefs=tuple(sorted(bundle.evidence_ids)),
            profile=profile,
            prompt=prompt,
            outputSchema=output_schema,
            maxTurns=6 if is_lead else (16 if bundle.depth == "quick" else 20),
            timeoutSeconds=timeout_seconds,
            maxBudgetUsd=2.0 if is_lead else 3.0,
            permissions=(),
            workspaceRef=str(workspace),
            runtime=runtime,
        )
        session = await adapter.start(request)
        session_ref["id"] = session.id
        self._sessions.setdefault(run_id, []).append((adapter, session))
        await self.store.append_event(
            run_id,
            "executor.session.started",
            {"stageId": stage_id, "sessionId": session.id, "profile": profile},
        )
        output: dict[str, Any] | None = None
        stream_completed = False
        try:
            async for event in adapter.stream(session):
                if event.type == "delta":
                    await self.store.append_event(
                        run_id,
                        "executor.delta",
                        {"stageId": stage_id, "sessionId": session.id, **event.data},
                    )
                elif event.type == "tool_denied":
                    await self.store.append_event(
                        run_id,
                        "executor.tool_denied",
                        {"stageId": stage_id, "sessionId": session.id, **event.data},
                    )
                elif event.type == "result":
                    candidate = event.data.get("output")
                    if isinstance(candidate, dict):
                        output = candidate
                elif event.type == "session.completed":
                    summary = {"stageId": stage_id, "sessionId": session.id, **event.data}
                    await self.store.append_event(run_id, "executor.session.completed", summary)
                    current = self.store.get_run(run_id)
                    self.store.update_run(run_id, sessionSummaries=[*current.sessionSummaries, summary])
                    if ledger is not None and getattr(adapter, "is_agent_runtime", False):
                        await ledger.record_session_summary(summary)
            stream_completed = True
        finally:
            if not stream_completed:
                await adapter.cancel(session)
            active = self._sessions.get(run_id)
            if active is not None:
                try:
                    active.remove((adapter, session))
                except ValueError:
                    pass
        if output is None:
            raise ExecutorError("EXECUTOR_INVALID_OUTPUT", f"{profile} returned no structured result.")
        return output

    @staticmethod
    def _validate_candidate_references(output: dict[str, Any], bundle: EvidenceBundle) -> None:
        available = bundle.evidence_ids
        for raw in output.get("candidateFindings") or []:
            missing = sorted(set(raw.get("evidence") or []) - available)
            if missing:
                raise HarnessAuditError(
                    "FINDINGS_INVALID",
                    f"Specialist referenced unavailable evidence: {', '.join(missing)}",
                )

    @staticmethod
    def _workflow() -> tuple[WorkflowStage, ...]:
        specialist_dependencies = ("collect-evidence",)
        return (
            WorkflowStage("preflight"),
            WorkflowStage("collect-evidence", ("preflight",)),
            WorkflowStage("specialist-structure", specialist_dependencies),
            WorkflowStage("specialist-testing", specialist_dependencies),
            WorkflowStage("specialist-security", specialist_dependencies),
            WorkflowStage("lead-reconcile", ("collect-evidence", *SPECIALISTS.keys())),
            WorkflowStage("validate-findings", ("collect-evidence", "lead-reconcile")),
            WorkflowStage("write-report", ("collect-evidence", "validate-findings"), effect=StageEffect.VAULT_WRITE),
            WorkflowStage("graph-refresh", ("write-report",), effect=StageEffect.VAULT_WRITE),
        )

    @staticmethod
    def _specialist_prompt(profile: str, bundle: EvidenceBundle) -> str:
        return (
            f"You are the {profile}. Perform a read-only audit of the frozen repository workspace. "
            "Use the available Read, Glob, Grep, and policy-governed Bash tools to inspect relevant evidence. "
            "Each completed tool call returns an Evidence ID in additional context; cite those IDs exactly. "
            "The Seed Evidence Bundle below is orientation, not a limit on autonomous exploration. "
            "Do not infer unobserved runtime behavior. "
            "Return only the requested structured output.\n\n"
            f"PROFILE:\n{_profile_guidance(profile)}\n\n"
            + json.dumps(bundle.model_dump(mode="json"), ensure_ascii=False)
        )

    @staticmethod
    def _lead_prompt(bundle: EvidenceBundle, outputs: dict[str, Any]) -> str:
        evidence_view = HarnessAuditRuntime._lead_evidence_view(bundle, outputs)
        return (
            "You are the Harness Lead, derived from Better Harness Findings Quality Gates and Agent Work Loop. "
            "Reconcile the three specialist outputs. Deduplicate by consequence and cause chain, reject claims "
            "without supplied evidence, freeze severity, and score all five dimensions from 0 to 4 independently "
            "of finding counts. Evidence arrays must contain exact supplied evidence IDs only, with no annotations "
            "or descriptions appended. Session Evidence is unavailable and must not be invented. Return only structured output.\n\n"
            f"PROFILE:\n{_profile_guidance('Software Architect / Harness Lead')}\n\n"
            f"GATES:\n{_vendor_root().joinpath('better-harness-agent-work-loop.md').read_text(encoding='utf-8')}\n\n"
            f"EVIDENCE:\n{json.dumps(evidence_view, ensure_ascii=False)}\n\n"
            f"SPECIALISTS:\n{json.dumps(outputs, ensure_ascii=False)}"
        )

    @staticmethod
    def _lead_evidence_ids(bundle: EvidenceBundle, outputs: dict[str, Any]) -> set[str]:
        referenced = {
            evidence_id
            for output in outputs.values()
            for finding in output.get("candidateFindings") or []
            for evidence_id in finding.get("evidence") or []
        }
        deterministic = {
            item.id
            for envelope in bundle.envelopes.values()
            for item in envelope.evidence
            if item.collector == "deterministic"
        }
        return referenced | deterministic

    @staticmethod
    def _lead_evidence_view(bundle: EvidenceBundle, outputs: dict[str, Any]) -> dict[str, Any]:
        allowed = HarnessAuditRuntime._lead_evidence_ids(bundle, outputs)
        return {
            "schemaVersion": bundle.schemaVersion,
            "runId": bundle.runId,
            "repoHead": bundle.repoHead,
            "sessionEvidenceStatus": bundle.sessionEvidenceStatus.value,
            "envelopes": {
                name: {
                    "status": envelope.status.value,
                    "summaryFacts": envelope.summaryFacts,
                    "evidence": [
                        {
                            "id": item.id,
                            "source": item.source,
                            "contentHash": item.contentHash,
                            "collector": item.collector,
                            "stageId": item.stageId,
                            "toolName": item.toolName,
                            "excerpt": item.excerpt[:2000],
                        }
                        for item in envelope.evidence
                        if item.id in allowed
                    ],
                }
                for name, envelope in bundle.envelopes.items()
            },
        }

    @staticmethod
    def _normalize_report(run_id: str, bundle: EvidenceBundle, output: dict[str, Any]) -> AuditReport:
        return AuditReport.model_validate(
            {
                "runId": run_id,
                "repoHead": bundle.repoHead,
                "generatedAt": utc_now(),
                "supportTrack": output.get("supportTrack") or "Undetermined",
                "dimensionScores": output.get("dimensionScores") or {},
                "findings": output.get("findings") or [],
            }
        )

    @staticmethod
    def _validate_report(report: AuditReport, bundle: EvidenceBundle) -> None:
        if set(item.value for item in report.dimensionScores) != set(DIMENSIONS):
            raise HarnessAuditError("FINDINGS_INVALID", "All five dimension scores are required.")
        if any(score < 0 or score > 4 for score in report.dimensionScores.values()):
            raise HarnessAuditError("FINDINGS_INVALID", "Dimension scores must be between 0 and 4.")
        seen_ids: set[str] = set()
        seen_keys: set[tuple[str, str]] = set()
        for finding in report.findings:
            if finding.id in seen_ids:
                raise HarnessAuditError("FINDINGS_INVALID", f"Duplicate finding id: {finding.id}")
            seen_ids.add(finding.id)
            key = (finding.title.casefold().strip(), finding.causeChain.casefold().strip())
            if key in seen_keys:
                raise HarnessAuditError("FINDINGS_INVALID", f"Duplicate finding content: {finding.id}")
            seen_keys.add(key)
            missing = finding.validate_evidence_ids(bundle.evidence_ids)
            if missing:
                raise HarnessAuditError(
                    "FINDINGS_INVALID",
                    f"Finding {finding.id} cites unknown evidence: {', '.join(missing)}",
                )

    def _write_proposal(
        self,
        markdown: str,
        run_id: str,
        bundle: EvidenceBundle,
        *,
        stale: bool,
    ) -> Path:
        output_dir = (self.vault_root / "wiki" / "generated").resolve()
        output_dir.relative_to(self.vault_root)
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", self.repo_root.name).strip("-.") or "repository"
        target = output_dir / f"{stem}-harness-audit.md"
        source = f"repository:{self.repo_root.name}"
        if target.exists():
            existing = target.read_text(encoding="utf-8")
            frontmatter = _frontmatter(existing)
            if frontmatter.get("generatedBy") != "inkdesk" or frontmatter.get("source") != source:
                raise HarnessAuditError("ARTIFACT_CONFLICT", f"Refusing to overwrite protected artifact: {target.name}")
        prefix = (
            "---\n"
            "generatedBy: inkdesk\n"
            f"source: {source}\n"
            "capability: harness-audit\n"
            f"runId: {run_id}\n"
            f"repoHead: {bundle.repoHead}\n"
            f"stale: {'true' if stale else 'false'}\n"
            "---\n"
        )
        temporary = target.with_suffix(target.suffix + ".tmp")
        try:
            temporary.write_text(prefix + markdown, encoding="utf-8", newline="\n")
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()
        return target

    def _render_report(self, report: AuditReport, bundle: EvidenceBundle, *, stale: bool) -> str:
        status = "STALE: repository HEAD changed during the audit." if stale else "Frozen at the repository HEAD shown below."
        scores = "\n".join(
            f"| {dimension.value} | {report.dimensionScores[dimension]} / 4 |"
            for dimension in FindingDimension
        )
        findings = []
        for finding in report.findings:
            findings.append(
                f"## {finding.id}: {finding.title}\n\n"
                f"- Dimension: {finding.dimension.value}\n"
                f"- Severity: {finding.severity.value}\n"
                f"- Confidence: {finding.confidence.value}\n"
                f"- Owner: {finding.owner}\n"
                f"- Consequence: {finding.consequence}\n"
                f"- Cause chain: {finding.causeChain}\n"
                f"- Evidence: {', '.join(finding.evidence)}\n"
                f"- Expected artifact: {finding.expectedArtifact}\n"
                f"- Repair scope: {finding.repairScope}\n"
                f"- Verifiers: {', '.join(finding.verifiers)}\n"
                f"- Status: {finding.status.value}\n"
            )
        finding_text = "\n".join(findings) if findings else "## Findings\n\nNo evidence-supported findings were retained."
        return (
            f"# {self.repo_root.name} Harness Audit\n\n"
            f"> {status}\n\n"
            f"- Run: `{report.runId}`\n"
            f"- Repository HEAD: `{report.repoHead}`\n"
            f"- Generated: `{report.generatedAt}`\n"
            f"- Support track: {report.supportTrack}\n"
            f"- Session evidence: `{bundle.sessionEvidenceStatus.value}`\n\n"
            "## Five-Dimension Score\n\n"
            "| Dimension | Score |\n| --- | --- |\n"
            f"{scores}\n\n"
            "```mermaid\n"
            "sequenceDiagram\n"
            "  participant Inkdesk\n"
            "  participant Evidence\n"
            "  participant Specialists\n"
            "  participant Lead\n"
            "  Inkdesk->>Evidence: Collect versioned repository evidence\n"
            "  Inkdesk->>Specialists: Start three isolated read-only sessions\n"
            "  Specialists-->>Lead: Candidate findings\n"
            "  Lead-->>Inkdesk: Frozen scores and findings\n"
            "```\n\n"
            f"{finding_text}\n"
        )


def _frontmatter(content: str) -> dict[str, str]:
    if not content.startswith("---\n"):
        return {}
    end = content.find("\n---\n", 4)
    if end < 0:
        return {}
    values: dict[str, str] = {}
    for line in content[4:end].splitlines():
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip()
    return values


def _vendor_root() -> Path:
    return Path(__file__).resolve().parent / "vendor"


def _profile_guidance(profile: str) -> str:
    name = PROFILE_FILES[profile]
    return (_vendor_root() / "profiles" / name).read_text(encoding="utf-8")


def _finding_schema(evidence_ids: set[str]) -> dict[str, Any]:
    string = {"type": "string", "minLength": 1}
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string", "pattern": r"^F-[0-9]{3,}$"},
            "dimension": {"type": "string", "enum": list(DIMENSIONS)},
            "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "title": string,
            "consequence": string,
            "causeChain": string,
            "owner": string,
            "evidence": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string", "enum": sorted(evidence_ids)},
            },
            "expectedArtifact": string,
            "repairScope": string,
            "verifiers": {"type": "array", "minItems": 1, "items": string},
            "status": {"type": "string", "enum": ["open", "deferred", "verified"]},
        },
        "required": [
            "id", "dimension", "severity", "confidence", "title", "consequence",
            "causeChain", "owner", "evidence", "expectedArtifact", "repairScope",
            "verifiers", "status",
        ],
    }


def _specialist_schema() -> dict[str, Any]:
    finding = _finding_schema(set())
    finding["properties"]["evidence"]["items"] = {
        "type": "string",
        "pattern": r"^E-(?:A-)?[A-Fa-f0-9]{12}$",
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "specialist": {"type": "string"},
            "observations": {"type": "array", "items": {"type": "string"}},
            "candidateFindings": {"type": "array", "items": finding},
        },
        "required": ["specialist", "observations", "candidateFindings"],
    }


def _lead_schema(_evidence_ids: set[str]) -> dict[str, Any]:
    finding = _finding_schema(set())
    finding["properties"]["evidence"]["items"] = {
        "type": "string",
        "pattern": r"^E-(?:A-)?[A-Fa-f0-9]{12}$",
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "supportTrack": {"type": "string"},
            "dimensionScores": {
                "type": "object",
                "additionalProperties": False,
                "properties": {dimension: {"type": "integer", "minimum": 0, "maximum": 4} for dimension in DIMENSIONS},
                "required": list(DIMENSIONS),
            },
            "findings": {"type": "array", "items": finding},
        },
        "required": ["supportTrack", "dimensionScores", "findings"],
    }
