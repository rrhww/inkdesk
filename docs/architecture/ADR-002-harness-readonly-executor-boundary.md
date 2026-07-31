# ADR-002: Harness Read-Only Executor Boundary

- Status: Superseded by ADR-003
- Date: 2026-07-30
- Supersedes: the permission defaults proposed in `docs/development/specs/2026-07-10-coding-interactive-sse-design.md`

## Context

The earlier coding-session proposal allowed `bypassPermissions`, disabled the
sandbox, and treated direct writes to the current working directory as a fast
execution mode. Those defaults are incompatible with an evidence-grade audit:
they combine model judgment, evidence acquisition, tool authorization, and
workspace mutation in one trust boundary.

## Decision

Inkdesk owns evidence collection, workflow scheduling, persistence, gates, and
authorized Vault writes. Executors receive a versioned Evidence Bundle and an
output schema. The `harness-audit-v1` Claude sessions use:

- fresh sessions for each Specialist and a separate Lead session;
- the Claude Code user setting source only for Provider credentials and model
  mapping, with native `--safe-mode` disabling CLAUDE.md, Skills, plugins,
  hooks, MCP servers, commands, agents, and other user customizations;
- no SDK-provided Skills, no MCP servers, no session persistence, and no
  fallback model;
- an empty tool set and a deny callback for every unexpected tool request;
- explicit turn, timeout, and cost budgets;
- no workspace write, shell, network, push, PR, or repair capability.

The repository path is accepted only when it equals the server-configured
`INKDESK_REPO_ROOT`. Inkdesk reads tracked paths through bounded structured Git
calls. It does not read user home directories, private Claude/Codex sessions,
secret files, dependency trees, or build output.

Inkdesk does not parse or copy Provider credentials. Claude Code resolves its
own user Provider configuration, including CCSwitch-managed third-party API
profiles, inside safe mode. The Executor still supplies an empty tool set and
empty MCP configuration, so Provider selection does not expand Agent authority.

Run events and evidence are redacted before persistence. Evidence records retain
source, content hash, capture time, and repository HEAD. A HEAD change during a
run marks the result `stale`; the report cannot claim to describe current code.

## Consequences

This version cannot modify code or automatically repair a Finding. That is
intentional. A later write-capable workflow must use an isolated worktree,
per-Finding authorization, explicit human approval, and independent validation.
There is no compatibility mode that restores `bypassPermissions`.
