from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class ToolDecision(StrEnum):
    ALLOW = "allow"
    REVIEW = "review"
    DENY = "deny"


@dataclass(frozen=True, slots=True)
class ToolPolicyResult:
    decision: ToolDecision
    reason: str


_READ_TOOLS = {"Read", "Glob", "Grep"}
_DENIED_TOOLS = {
    "Write",
    "Edit",
    "MultiEdit",
    "NotebookEdit",
    "Task",
    "WebFetch",
    "WebSearch",
}
_SAFE_GIT = {"status", "diff", "log", "show", "ls-files", "rev-parse"}
_SHELL_META = re.compile(r"[;&|<>`$\r\n]|%[A-Za-z_][A-Za-z0-9_]*%")
_SECRET_PART = re.compile(r"^(?:\.env(?:\..*)?|credentials?|secrets?|id_rsa|id_ed25519)$", re.I)
_SKIPPED_PARTS = {".git", ".aws", ".ssh", "node_modules", ".venv", "dist", "build", ".next", "target"}


class ReadOnlyAuditToolPolicy:
    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root).resolve()

    def evaluate(self, tool_name: str, tool_input: dict[str, Any]) -> ToolPolicyResult:
        if tool_name == "StructuredOutput":
            return ToolPolicyResult(ToolDecision.ALLOW, "Structured output protocol tool.")
        if tool_name in _DENIED_TOOLS or tool_name.startswith("mcp__"):
            return ToolPolicyResult(ToolDecision.DENY, "Tool is outside the read-only audit capability.")
        if tool_name in _READ_TOOLS:
            return self._evaluate_path_tool(tool_input)
        if tool_name == "Bash":
            return self._evaluate_bash(str(tool_input.get("command") or ""))
        return ToolPolicyResult(ToolDecision.DENY, "Unknown tools are denied by default.")

    def _evaluate_path_tool(self, tool_input: dict[str, Any]) -> ToolPolicyResult:
        if "pattern" in tool_input and self._pattern_escapes_workspace(str(tool_input.get("pattern") or "")):
            return ToolPolicyResult(ToolDecision.DENY, "Search pattern escapes the frozen audit workspace.")
        raw = next(
            (tool_input.get(name) for name in ("file_path", "path") if tool_input.get(name)),
            None,
        )
        if raw is None:
            candidate = self.workspace_root
        else:
            candidate = Path(str(raw))
            if not candidate.is_absolute():
                candidate = self.workspace_root / candidate
        try:
            resolved = candidate.resolve(strict=False)
            resolved.relative_to(self.workspace_root)
        except (OSError, ValueError):
            return ToolPolicyResult(ToolDecision.DENY, "Path escapes the frozen audit workspace.")
        relative = resolved.relative_to(self.workspace_root)
        if any(part.casefold() in _SKIPPED_PARTS for part in relative.parts):
            return ToolPolicyResult(ToolDecision.DENY, "Path belongs to a denied repository area.")
        if any(_SECRET_PART.match(part) for part in relative.parts):
            if relative.name.casefold().endswith(".example"):
                return ToolPolicyResult(ToolDecision.ALLOW, "Example configuration is readable.")
            return ToolPolicyResult(ToolDecision.DENY, "Potential credential files are not audit evidence.")
        return ToolPolicyResult(ToolDecision.ALLOW, "Path is inside the frozen audit workspace.")

    @staticmethod
    def _pattern_escapes_workspace(pattern: str) -> bool:
        candidate = Path(pattern)
        return candidate.is_absolute() or ".." in candidate.parts or pattern.startswith("~")

    def _evaluate_bash(self, command: str) -> ToolPolicyResult:
        if not command.strip():
            return ToolPolicyResult(ToolDecision.DENY, "Empty commands are denied.")
        if _SHELL_META.search(command):
            return ToolPolicyResult(ToolDecision.DENY, "Shell composition and redirection are denied.")
        try:
            parts = shlex.split(command, posix=True)
        except ValueError:
            return ToolPolicyResult(ToolDecision.DENY, "Command could not be parsed safely.")
        if not parts:
            return ToolPolicyResult(ToolDecision.DENY, "Empty commands are denied.")
        executable = Path(parts[0]).name.casefold()
        if executable == "git" and len(parts) >= 2:
            cursor = 1
            if parts[cursor] == "-C":
                if len(parts) < 4:
                    return ToolPolicyResult(ToolDecision.DENY, "git -C requires a workspace path and subcommand.")
                candidate = Path(parts[cursor + 1])
                if not candidate.is_absolute():
                    candidate = self.workspace_root / candidate
                try:
                    candidate.resolve(strict=False).relative_to(self.workspace_root)
                except (OSError, ValueError):
                    return ToolPolicyResult(ToolDecision.DENY, "git -C path escapes the audit workspace.")
                cursor += 2
            operation = parts[cursor].casefold()
            if operation in _SAFE_GIT:
                if any(
                    arg.startswith("--output")
                    or arg.startswith("--exec=")
                    or arg.startswith("--upload-pack=")
                    or arg in {
                        "-o",
                        "--exec",
                        "--upload-pack",
                        "--ext-diff",
                        "--textconv",
                        "--no-index",
                        "--paginate",
                    }
                    for arg in parts[cursor + 1 :]
                ):
                    return ToolPolicyResult(ToolDecision.DENY, "Git output and execution options are denied.")
                return ToolPolicyResult(ToolDecision.ALLOW, f"Read-only git {operation} command.")
            return ToolPolicyResult(ToolDecision.DENY, "Git write and network operations are denied.")
        if executable in {"rg", "rg.exe"}:
            if any(arg in {"--pre", "--pre-glob"} for arg in parts[1:]):
                return ToolPolicyResult(ToolDecision.DENY, "rg preprocessors are denied.")
            for arg in parts[1:]:
                if arg.startswith("-") or arg == ".":
                    continue
                candidate = Path(arg)
                if candidate.is_absolute() or ".." in candidate.parts:
                    return ToolPolicyResult(ToolDecision.DENY, "rg paths must remain inside the audit workspace.")
            if any(arg in {"--files-with-matches", "--files-without-match"} for arg in parts[1:]):
                return ToolPolicyResult(ToolDecision.REVIEW, "Read-only rg variant requires one-time approval.")
            return ToolPolicyResult(ToolDecision.ALLOW, "Read-only repository search command.")
        if executable in {"ls", "dir", "pwd", "wc", "head", "tail"}:
            return ToolPolicyResult(ToolDecision.REVIEW, "Read-only shell query requires one-time approval.")
        return ToolPolicyResult(ToolDecision.DENY, "Executable is not on the read-only audit allowlist.")
