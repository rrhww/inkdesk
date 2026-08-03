---
name: harness-audit
description: Audit a repository's coding-agent harness from bounded, versioned evidence. Use when assessing task guidance, controlled execution, validation, delivery gates, or learning capture before enabling autonomous code changes. Do not use for implementing fixes or changing the repository.
license: MIT
compatibility: Requires an Inkdesk Harness Runtime and Claude Code with safe-mode support for real execution.
metadata:
  owner: inkdesk
  upstream: QoderAI/better-harness
allowed-tools: Read Glob Grep Bash
---

# Harness Audit

Audit the outer coding-agent system without changing the target repository.

## Workflow

1. Accept the versioned Seed Evidence Bundle and a frozen repository workspace assembled by Inkdesk.
2. Run exactly three fresh specialist analyses in parallel:
   project structure, test and delivery evidence, and security boundaries.
3. Autonomously collect bounded repository evidence with Inkdesk-governed read-only tools. Do not delegate or infer unavailable behavior.
4. Reconcile all specialist candidates once after all three specialists finish.
5. Freeze supported Findings before calculating scores or writing reader-facing copy.
6. Produce machine-valid `findings.json` and a Markdown report. Do not repair findings.

## Evidence Rules

- Tie every Finding to Seed or Agent Evidence IDs present in the frozen ledger.
- Preserve missing and partial evidence as explicit uncertainty.
- Keep disagreement at lower confidence instead of inventing consensus.
- Treat configured assets as configuration evidence, not proof they ran.
- Stop when the repository HEAD no longer matches the bundle.

## Finding Rules

- Assign one primary Agent Work Loop dimension.
- Include consequence, cause chain, smallest owner, expected artifact, bounded repair scope, and verifiers.
- Merge candidates only when target, consequence, owner, and repair route are the same.
- Do not drop an eligible Finding to reach a preferred report length.

Read [agent-work-loop.md](references/agent-work-loop.md) for dimensions and
[findings-quality-gates.md](references/findings-quality-gates.md) before lead reconciliation.
