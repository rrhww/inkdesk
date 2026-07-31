# ADR-003: Governed Agent Executor

- Status: Accepted
- Date: 2026-08-02
- Supersedes: ADR-002

## Context

Treating Claude Code as an empty-tool structured-output client removed the
agent behavior Inkdesk is intended to govern. Granting unrestricted access
would make audit evidence and side effects impossible to prove.

## Decision

Inkdesk is the Harness and Claude Code is an Agent Executor. Inkdesk owns
workflow stages, frozen workspaces, tool policy, approvals, evidence, gates,
persistence, and cancellation. Claude Code owns the multi-turn reasoning and
built-in tool loop inside those boundaries.

Each audit Specialist receives a fresh ClaudeSDKClient session and an
independent detached worktree at the Run source HEAD. Specialists may use
Read, Glob, Grep, and policy-governed Bash. Lead synthesis receives the frozen
Evidence Ledger and no repository tools. Task delegation, writes, project
scripts, network access, MCP, push, and PR operations remain unavailable.

PreToolUse hooks enforce every tool call even when user settings contain allow
rules. Human approval can allow one policy-classified read-only command; it
cannot cross the Capability hard boundary. PostToolUse hooks redact results,
persist Agent Evidence, and return a stable evidence reference to the model.

Claude Code loads the active user Provider through safe mode so CCSwitch can
route to DeepSeek without Inkdesk reading credentials. A live nonce probe must
verify streaming tool use and structured output. Capability mismatch fails
closed and never falls back to a chat completion.

## Consequences

The audit exercises a real Agent runtime while preserving a provably unchanged
source repository. Temporary worktrees and approval state add lifecycle
complexity. Code repair remains a separate workflow that can reuse the same
executor protocol with a different workspace and tool policy.
