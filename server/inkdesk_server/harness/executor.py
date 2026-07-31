from __future__ import annotations

import asyncio
import json
import platform
import shutil
import tempfile
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from inkdesk_server.harness.tool_policy import ReadOnlyAuditToolPolicy, ToolDecision


class ExecutorError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


EmitCallback = Callable[[str, dict[str, Any]], Awaitable[None]]
AuthorizeCallback = Callable[[str, str, dict[str, Any]], Awaitable[bool]]
EvidenceCallback = Callable[[str, str, dict[str, Any], Any], Awaitable[tuple[str, Any]]]


@dataclass(slots=True)
class AgentExecutionRuntime:
    policy: ReadOnlyAuditToolPolicy
    emit: EmitCallback
    authorize: AuthorizeCallback
    record_evidence: EvidenceCallback
    denial_count: int = 0
    structured_denials: int = 0
    structured_missing: tuple[str, ...] = ()
    evidence_ids: set[str] = field(default_factory=set)
    policy_error: ExecutorError | None = None


class AgentExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    runId: str
    stageId: str
    evidenceRef: str
    evidenceRefs: tuple[str, ...] = ()
    profile: str
    prompt: str
    outputSchema: dict[str, Any]
    maxTurns: int = Field(default=3, ge=1, le=20)
    timeoutSeconds: float = Field(default=120.0, gt=0, le=1800)
    maxBudgetUsd: float = Field(default=0.75, gt=0, le=20)
    permissions: tuple[str, ...] = ()
    workspaceRef: str | None = None
    toolPolicyRef: str = "harness-audit-read-only-v1"
    cwd: str | None = None
    runtime: AgentExecutionRuntime | None = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def workspace_is_required(self) -> "AgentExecutionRequest":
        if not self.workspaceRef and not self.cwd:
            raise ValueError("workspaceRef is required")
        return self

    @property
    def workspace_path(self) -> Path:
        return Path(self.workspaceRef or self.cwd or ".").resolve()


# Transitional alias for code that imported the unpushed v0.2 draft.
ExecutionRequest = AgentExecutionRequest


class ExecutorEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    data: dict[str, Any] = Field(default_factory=dict)


@dataclass(slots=True)
class ExecutorSession:
    id: str
    request: AgentExecutionRequest
    state: Any = None


class AgentExecutorAdapter(Protocol):
    async def probe(self) -> dict[str, Any]: ...
    async def start(self, request: AgentExecutionRequest) -> ExecutorSession: ...
    def stream(self, session: ExecutorSession) -> AsyncIterator[ExecutorEvent]: ...
    async def cancel(self, session: ExecutorSession) -> None: ...
    async def close(self) -> None: ...


ExecutorAdapter = AgentExecutorAdapter
FakeHandler = Callable[[AgentExecutionRequest], Awaitable[dict[str, Any]] | dict[str, Any]]


class FakeExecutor:
    is_agent_runtime = False

    def __init__(self, handler: FakeHandler):
        self.handler = handler
        self.sessions: list[ExecutorSession] = []
        self.cancelled: set[str] = set()

    async def probe(self) -> dict[str, Any]:
        return {"available": True, "name": "fake", "capabilities": _agent_capabilities()}

    async def start(self, request: AgentExecutionRequest) -> ExecutorSession:
        session = ExecutorSession("fake-" + uuid4().hex[:12], request)
        self.sessions.append(session)
        return session

    async def stream(self, session: ExecutorSession) -> AsyncIterator[ExecutorEvent]:
        if session.id in self.cancelled:
            raise ExecutorError("EXECUTOR_CANCELLED", "Executor session was cancelled.")
        value = self.handler(session.request)
        if asyncio.iscoroutine(value):
            value = await value
        yield ExecutorEvent(type="delta", data={"text": json.dumps(value, ensure_ascii=False)})
        yield ExecutorEvent(type="result", data={"output": value})
        yield ExecutorEvent(
            type="session.completed",
            data={"turns": 1, "toolCount": 0, "denialCount": 0, "costStatus": "unavailable"},
        )

    async def cancel(self, session: ExecutorSession) -> None:
        self.cancelled.add(session.id)

    async def close(self) -> None:
        return None


class DeterministicAuditExecutor(FakeExecutor):
    def __init__(self):
        super().__init__(self._respond)

    @staticmethod
    def _respond(request: AgentExecutionRequest) -> dict[str, Any]:
        if request.stageId == "lead-reconcile":
            return {
                "supportTrack": "Evidence-limited deterministic demonstration",
                "dimensionScores": {
                    "Task Understanding": 2,
                    "Controlled Execution": 2,
                    "Change Validation": 1,
                    "Reliable Delivery": 1,
                    "Learning Capture": 0,
                },
                "findings": [],
            }
        return {"specialist": request.profile, "observations": [], "candidateFindings": []}


@dataclass(slots=True)
class _ClaudeState:
    client: Any
    client_factory: Callable[[], Awaitable[Any]]
    started_at: float = field(default_factory=perf_counter)
    tool_count: int = 0
    closed: bool = False


class ClaudeExecutor:
    is_agent_runtime = True

    def __init__(self):
        self._sessions: dict[str, ExecutorSession] = {}
        self._live_probe: tuple[float, dict[str, Any]] | None = None

    async def probe(self) -> dict[str, Any]:
        try:
            import claude_agent_sdk
        except ImportError as exc:
            raise ExecutorError(
                "EXECUTOR_NOT_AVAILABLE",
                "Claude Agent SDK is not installed. Install the server claude extra.",
            ) from exc
        cli_path = shutil.which("claude")
        if not cli_path:
            raise ExecutorError("EXECUTOR_NOT_AVAILABLE", "Claude Code executable was not found on PATH.")
        return {
            "available": True,
            "name": "claude",
            "cliPath": cli_path,
            "sdkVersion": getattr(claude_agent_sdk, "__version__", "unknown"),
            "capabilities": _agent_capabilities(),
        }

    async def start(self, request: AgentExecutionRequest) -> ExecutorSession:
        await self.probe()
        try:
            from claude_agent_sdk import (
                ClaudeAgentOptions,
                ClaudeSDKClient,
                HookMatcher,
                PermissionResultDeny,
            )
        except ImportError as exc:
            raise ExecutorError("EXECUTOR_NOT_AVAILABLE", "Claude Agent SDK is not installed.") from exc

        session_id = "claude-" + uuid4().hex[:12]
        runtime = request.runtime

        async def pre_tool_use(hook_input: Any, _tool_use_id: str | None, _context: Any) -> dict[str, Any]:
            tool_name = str(hook_input.get("tool_name") or "")
            tool_input = hook_input.get("tool_input") or {}
            tool_use_id = str(hook_input.get("tool_use_id") or _tool_use_id or uuid4().hex)
            if runtime is None:
                return _hook_decision("deny", "Executor runtime policy is unavailable.")
            if tool_name == "StructuredOutput":
                missing = sorted(_referenced_evidence_ids(tool_input) - runtime.evidence_ids)
                if missing:
                    runtime.structured_denials += 1
                    runtime.structured_missing = tuple(missing)
                    await runtime.emit(
                        "output.invalid",
                        {"toolUseId": tool_use_id, "missingEvidence": missing},
                    )
                    if runtime.structured_denials > 1:
                        runtime.policy_error = ExecutorError(
                            "EXECUTOR_INVALID_OUTPUT",
                            "Claude returned unavailable evidence references after one correction attempt.",
                        )
                    return _hook_decision(
                        "deny",
                        "These evidence IDs are unavailable: " + ", ".join(missing) + ". Correct the output once.",
                    )
            result = runtime.policy.evaluate(tool_name, tool_input)
            if result.decision == ToolDecision.ALLOW:
                await runtime.emit("tool.started", {"toolUseId": tool_use_id, "tool": tool_name})
                return _hook_decision("allow", result.reason)
            if result.decision == ToolDecision.REVIEW:
                await runtime.emit(
                    "tool.requested",
                    {"toolUseId": tool_use_id, "tool": tool_name, "input": tool_input, "reason": result.reason},
                )
                allowed = await runtime.authorize(tool_use_id, tool_name, tool_input)
                if allowed:
                    await runtime.emit("tool.approved", {"toolUseId": tool_use_id, "tool": tool_name})
                    await runtime.emit("tool.started", {"toolUseId": tool_use_id, "tool": tool_name})
                    return _hook_decision("allow", "Approved once by the Inkdesk operator.")
                runtime.denial_count += 1
                await runtime.emit(
                    "tool_denied",
                    {"toolUseId": tool_use_id, "tool": tool_name, "input": tool_input, "reason": "Approval denied or expired."},
                )
                if runtime.denial_count > 5:
                    runtime.policy_error = ExecutorError(
                        "EXECUTOR_POLICY_VIOLATION", "Claude exceeded the denied-tool limit."
                    )
                return _hook_decision("deny", "Approval denied or expired; use an allowed read-only tool.")
            runtime.denial_count += 1
            await runtime.emit(
                "tool_denied",
                {"toolUseId": tool_use_id, "tool": tool_name, "input": tool_input, "reason": result.reason},
            )
            if runtime.denial_count > 5:
                runtime.policy_error = ExecutorError(
                    "EXECUTOR_POLICY_VIOLATION", "Claude exceeded the denied-tool limit."
                )
            return _hook_decision("deny", result.reason)

        async def post_tool_use(hook_input: Any, _tool_use_id: str | None, _context: Any) -> dict[str, Any]:
            tool_name = str(hook_input.get("tool_name") or "")
            tool_input = hook_input.get("tool_input") or {}
            tool_response = hook_input.get("tool_response")
            tool_use_id = str(hook_input.get("tool_use_id") or _tool_use_id or uuid4().hex)
            if runtime is None or tool_name == "StructuredOutput":
                return {}
            evidence_id, redacted = await runtime.record_evidence(
                tool_use_id, tool_name, tool_input, tool_response
            )
            state = self._sessions.get(session_id)
            if state and isinstance(state.state, _ClaudeState):
                state.state.tool_count += 1
            await runtime.emit(
                "tool.completed",
                {"toolUseId": tool_use_id, "tool": tool_name, "evidenceId": evidence_id},
            )
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "updatedToolOutput": redacted,
                    "additionalContext": f"Cite evidence ID {evidence_id} for claims derived from this tool result.",
                }
            }

        async def post_tool_failure(hook_input: Any, _tool_use_id: str | None, _context: Any) -> dict[str, Any]:
            if runtime is not None:
                await runtime.emit(
                    "tool.failed",
                    {
                        "toolUseId": str(hook_input.get("tool_use_id") or _tool_use_id or "unknown"),
                        "tool": str(hook_input.get("tool_name") or "unknown"),
                        "error": str(hook_input.get("error") or "Tool execution failed."),
                    },
                )
            return {}

        async def deny_unhandled(tool_name: str, _tool_input: dict[str, Any], _context: Any) -> Any:
            return PermissionResultDeny(message=f"Unhandled permission request denied: {tool_name}")

        is_lead = request.stageId == "lead-reconcile"
        governance_prompt = (
            "You are running inside the Inkdesk read-only audit Harness. "
            "For repository exploration, prefer Glob, Read, and Grep. "
            "Bash is only valid for a single command with no pipes, redirects, semicolons, command substitution, or environment assignment. "
            "Allowed Bash executables are git and rg. Allowed git subcommands are status, diff, log, show, ls-files, and rev-parse. "
            "Never use PowerShell cmdlets, ls, find, cat, test/build/package commands, network commands, or retry a denied command. "
            "A denied call consumes the session policy budget; immediately switch to Glob, Read, or Grep. "
            "Do not request writes, edits, delegation, web access, MCP, commits, pushes, or PRs."
        )
        options = ClaudeAgentOptions(
            tools=[] if is_lead else ["Read", "Glob", "Grep", "Bash"],
            allowed_tools=[],
            system_prompt={"type": "preset", "preset": "claude_code", "append": governance_prompt},
            disallowed_tools=["Write", "Edit", "NotebookEdit", "Task", "WebFetch", "WebSearch"],
            setting_sources=["user"],
            skills=[],
            mcp_servers={},
            strict_mcp_config=True,
            permission_mode="default",
            can_use_tool=None if is_lead else deny_unhandled,
            hooks={
                "PreToolUse": [HookMatcher(matcher=None, hooks=[pre_tool_use], timeout=100.0)],
                "PostToolUse": [HookMatcher(matcher=None, hooks=[post_tool_use], timeout=30.0)],
                "PostToolUseFailure": [HookMatcher(matcher=None, hooks=[post_tool_failure], timeout=30.0)],
            },
            cwd=request.workspace_path,
            cli_path=shutil.which("claude"),
            max_turns=request.maxTurns,
            max_budget_usd=request.maxBudgetUsd,
            fallback_model=None,
            include_partial_messages=True,
            include_hook_events=True,
            output_format={"type": "json_schema", "schema": request.outputSchema},
            enable_file_checkpointing=False,
            sandbox={
                "enabled": platform.system() != "Windows",
                "autoAllowBashIfSandboxed": False,
                "allowUnsandboxedCommands": False,
            },
            extra_args={
                "safe-mode": None,
                "disable-slash-commands": None,
                "no-session-persistence": None,
            },
        )
        async def client_factory() -> Any:
            last_error: Exception | None = None
            for attempt in range(2):
                client = ClaudeSDKClient(options=options)
                try:
                    await asyncio.wait_for(client.connect(), timeout=min(60.0, request.timeoutSeconds))
                    return client
                except Exception as exc:
                    last_error = exc
                    try:
                        await asyncio.wait_for(client.disconnect(), timeout=5.0)
                    except Exception:
                        pass
                    if attempt == 0:
                        if runtime is not None:
                            await runtime.emit(
                                "session.retrying",
                                {"attempt": 2, "reason": "EXECUTOR_CONNECT_FAILED"},
                            )
                        await asyncio.sleep(0.75)
            raise ExecutorError("EXECUTOR_FAILED", f"Claude session failed to connect: {last_error}") from last_error

        client = await client_factory()
        session = ExecutorSession(session_id, request, _ClaudeState(client, client_factory))
        self._sessions[session.id] = session
        return session

    async def live_probe(self, *, force: bool = False) -> dict[str, Any]:
        now = perf_counter()
        if not force and self._live_probe and now - self._live_probe[0] < 900:
            return {**self._live_probe[1], "cached": True}
        with tempfile.TemporaryDirectory(prefix="inkdesk-claude-probe-") as raw_root:
            root = Path(raw_root).resolve()
            nonce = uuid4().hex
            (root / "nonce.txt").write_text(nonce, encoding="utf-8")

            async def emit(_event_type: str, _data: dict[str, Any]) -> None:
                return None

            async def authorize(_tool_use_id: str, _tool: str, _tool_input: dict[str, Any]) -> bool:
                return False

            async def record_evidence(
                _tool_use_id: str,
                _tool_name: str,
                _tool_input: dict[str, Any],
                tool_response: Any,
            ) -> tuple[str, Any]:
                return "E-A-000000000000", tool_response

            runtime = AgentExecutionRuntime(
                policy=ReadOnlyAuditToolPolicy(root),
                emit=emit,
                authorize=authorize,
                record_evidence=record_evidence,
            )
            request = AgentExecutionRequest(
                runId="run-probe",
                stageId="specialist-probe",
                evidenceRef="probe",
                profile="Executor Capability Probe",
                prompt=(
                    "Use the Read tool to read nonce.txt from the current workspace. "
                    "Return the exact content in the requested structured output."
                ),
                outputSchema={
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"nonce": {"type": "string"}},
                    "required": ["nonce"],
                },
                maxTurns=2,
                timeoutSeconds=45,
                maxBudgetUsd=0.10,
                workspaceRef=str(root),
                runtime=runtime,
            )
            session = await self.start(request)
            output: dict[str, Any] | None = None
            summary: dict[str, Any] = {}
            async for event in self.stream(session):
                if event.type == "result":
                    output = event.data.get("output")
                elif event.type == "session.completed":
                    summary = event.data
            if not isinstance(output, dict) or output.get("nonce") != nonce or int(summary.get("toolCount") or 0) < 1:
                raise ExecutorError(
                    "EXECUTOR_CAPABILITY_MISMATCH",
                    "The active Claude Code provider did not complete a streamed Read tool call with structured output.",
                )
            result = {
                "available": True,
                "live": True,
                "cached": False,
                "capabilities": _agent_capabilities(),
                "toolLoopVerified": True,
                "structuredOutputVerified": True,
                "costStatus": summary.get("costStatus", "unavailable"),
            }
            self._live_probe = (perf_counter(), result)
            return result

    async def stream(self, session: ExecutorSession) -> AsyncIterator[ExecutorEvent]:
        try:
            from claude_agent_sdk import AssistantMessage, ResultMessage, StreamEvent, TextBlock
        except ImportError as exc:
            raise ExecutorError("EXECUTOR_NOT_AVAILABLE", "Claude Agent SDK is not installed.") from exc
        state: _ClaudeState = session.state
        output: dict[str, Any] | None = None
        result_message: Any = None
        correction_sent = False
        try:
            async with asyncio.timeout(session.request.timeoutSeconds):
                for attempt in range(2):
                    output = None
                    result_message = None
                    prompt = session.request.prompt
                    try:
                        while True:
                            correction_required = False
                            await state.client.query(prompt)
                            async for message in state.client.receive_response():
                                runtime = session.request.runtime
                                if runtime is not None and runtime.policy_error is not None:
                                    raise runtime.policy_error
                                if isinstance(message, AssistantMessage):
                                    for block in message.content:
                                        if isinstance(block, TextBlock) and block.text:
                                            yield ExecutorEvent(type="delta", data={"text": block.text})
                                elif isinstance(message, StreamEvent):
                                    event = getattr(message, "event", {})
                                    delta = event.get("delta", {}) if isinstance(event, dict) else {}
                                    text = delta.get("text") if isinstance(delta, dict) else None
                                    if text:
                                        yield ExecutorEvent(type="delta", data={"text": str(text)})
                                elif isinstance(message, ResultMessage):
                                    result_message = message
                                    structured = getattr(message, "structured_output", None)
                                    if isinstance(structured, dict):
                                        output = structured
                                    elif getattr(message, "is_error", False):
                                        if (
                                            runtime is not None
                                            and runtime.structured_denials == 1
                                            and runtime.structured_missing
                                            and not correction_sent
                                        ):
                                            correction_sent = True
                                            correction_required = True
                                        else:
                                            result = str(getattr(message, "result", "Claude failed."))
                                            raise ExecutorError(_claude_error_code(result), result)
                            if output is not None:
                                break
                            if correction_required:
                                prompt = _structured_correction_prompt(session.request.runtime)
                                continue
                            raise ExecutorError(
                                "EXECUTOR_INVALID_OUTPUT",
                                "Claude did not return structured output.",
                            )
                        break
                    except ExecutorError as exc:
                        if attempt == 0 and exc.code in {"EXECUTOR_FAILED", "EXECUTOR_RATE_LIMITED"}:
                            runtime = session.request.runtime
                            if runtime is not None:
                                await runtime.emit(
                                    "session.retrying",
                                    {"attempt": 2, "reason": exc.code},
                                )
                            await self._replace_client(session)
                            await asyncio.sleep(0.5)
                            continue
                        await self._disconnect(session)
                        raise
        except TimeoutError as exc:
            await self.cancel(session)
            raise ExecutorError("EXECUTOR_TIMEOUT", "Claude session exceeded its timeout.") from exc
        except ExecutorError:
            raise
        except Exception as exc:
            await self._disconnect(session)
            raise ExecutorError("EXECUTOR_FAILED", f"Claude session failed: {exc}") from exc
        if output is None:
            await self._disconnect(session)
            raise ExecutorError("EXECUTOR_INVALID_OUTPUT", "Claude did not return structured output.")
        yield ExecutorEvent(type="result", data={"output": output})
        total_cost = getattr(result_message, "total_cost_usd", None)
        yield ExecutorEvent(
            type="session.completed",
            data={
                "turns": getattr(result_message, "num_turns", None),
                "toolCount": state.tool_count,
                "denialCount": session.request.runtime.denial_count if session.request.runtime else 0,
                "durationMs": round((perf_counter() - state.started_at) * 1000, 3),
                "costStatus": "available" if total_cost is not None else "unavailable",
                "totalCostUsd": total_cost,
                "providerSessionId": getattr(result_message, "session_id", None),
            },
        )
        await self._disconnect(session)

    async def cancel(self, session: ExecutorSession) -> None:
        state = session.state
        if not isinstance(state, _ClaudeState) or state.closed:
            return
        try:
            await asyncio.wait_for(state.client.interrupt(), timeout=5.0)
        except Exception:
            pass
        await self._disconnect(session)

    async def close(self) -> None:
        await asyncio.gather(
            *(self.cancel(session) for session in tuple(self._sessions.values())),
            return_exceptions=True,
        )
        self._sessions.clear()

    async def _replace_client(self, session: ExecutorSession) -> None:
        state = session.state
        if not isinstance(state, _ClaudeState):
            raise ExecutorError("EXECUTOR_FAILED", "Claude session state is unavailable for retry.")
        try:
            await asyncio.wait_for(state.client.disconnect(), timeout=10.0)
        except Exception:
            pass
        state.client = await state.client_factory()
        state.closed = False
        self._sessions[session.id] = session

    async def _disconnect(self, session: ExecutorSession) -> None:
        state = session.state
        if not isinstance(state, _ClaudeState) or state.closed:
            return
        state.closed = True
        try:
            await asyncio.wait_for(state.client.disconnect(), timeout=10.0)
        except Exception:
            pass
        self._sessions.pop(session.id, None)


class ExecutorRegistry:
    def __init__(self, overrides: dict[str, AgentExecutorAdapter] | None = None):
        self._adapters: dict[str, AgentExecutorAdapter] = {
            "claude": ClaudeExecutor(),
            "deterministic": DeterministicAuditExecutor(),
            **(overrides or {}),
        }

    def get(self, name: str) -> AgentExecutorAdapter:
        normalized = name.strip().lower()
        if normalized == "codex":
            raise ExecutorError("EXECUTOR_NOT_AVAILABLE", "Codex Executor is reserved for a later release.")
        try:
            return self._adapters[normalized]
        except KeyError as exc:
            raise ExecutorError("EXECUTOR_NOT_AVAILABLE", f"Executor is not available: {name}") from exc

    async def close(self) -> None:
        for adapter in self._adapters.values():
            await adapter.close()

    async def probe(self, name: str, *, live: bool = False, force: bool = False) -> dict[str, Any]:
        adapter = self.get(name)
        if live:
            live_probe = getattr(adapter, "live_probe", None)
            if live_probe is None:
                raise ExecutorError("EXECUTOR_CAPABILITY_MISMATCH", "Executor does not support live probing.")
            return await live_probe(force=force)
        return await adapter.probe()


def _hook_decision(decision: str, reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }


def _agent_capabilities() -> list[str]:
    return ["agent-loop", "tool-use", "streaming", "interrupt", "structured-output", "hooks"]


def _referenced_evidence_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "evidence" and isinstance(item, list):
                found.update(str(candidate) for candidate in item if isinstance(candidate, str))
            else:
                found.update(_referenced_evidence_ids(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_referenced_evidence_ids(item))
    return found


def _structured_correction_prompt(runtime: AgentExecutionRuntime | None) -> str:
    if runtime is None:
        return "Return the corrected structured output now."
    invalid = ", ".join(runtime.structured_missing)
    allowed = ", ".join(sorted(runtime.evidence_ids))
    return (
        "Your previous StructuredOutput was rejected because it cited unavailable Evidence IDs. "
        f"Invalid IDs: {invalid}. Allowed exact Evidence IDs: {allowed}. "
        "Do not add, remove, or rewrite any Evidence ID prefix. Return the corrected structured output now "
        "without calling repository tools."
    )


def _claude_error_code(message: str) -> str:
    normalized = message.casefold()
    if "not logged in" in normalized or "please run /login" in normalized or "authentication" in normalized:
        return "EXECUTOR_AUTH_REQUIRED"
    if "rate limit" in normalized or "429" in normalized:
        return "EXECUTOR_RATE_LIMITED"
    if "tool_use" in normalized or "structured output" in normalized:
        return "EXECUTOR_CAPABILITY_MISMATCH"
    return "EXECUTOR_FAILED"
