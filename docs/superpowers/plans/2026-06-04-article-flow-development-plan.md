# Article-Flow Development Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `omni-superdev` first. Use `superpowers:test-driven-development` for implementation tasks, `ui-ux-pro-max` for product-surface changes, and `webapp-testing` for local browser verification. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Develop Inkdesk according to the article-inspired flow: `Sources -> LLM-Wiki -> Schema -> Skills -> Agent Runtime -> Evaluation -> Harness`.

**Architecture:** Keep Inkdesk as the control plane. Vault Markdown stores durable knowledge and workflow files; PostgreSQL stores indexes, queues, run state, and cached read models; LangGraph or external runtimes execute work; Inkdesk owns review, health, evaluation, and promotion gates.

**Tech Stack:** Next.js 16, React 19, TypeScript, FastAPI, SQLAlchemy, LangGraph, PostgreSQL + pgvector, Vault Markdown, pytest, Vitest, node:test, Playwright

---

## Article Flow

The development sequence is:

```text
Sources -> LLM-Wiki -> Schema -> Skills -> Agent Runtime -> Evaluation -> Harness
```

Inkdesk already has part of `Sources -> LLM-Wiki`:

```text
raw -> ingest -> wiki -> ask
```

The next work should extend that existing loop into the article-style system instead of jumping straight to autonomous agents.

## Execution Principle

- Build durable layers before autonomy.
- Keep every AI write behind review unless an evaluation-backed gate explicitly permits it.
- Store accepted knowledge and reusable workflow definitions as files.
- Treat external tools such as Claude Code, Codex, Cursor, Obsidian, and LangGraph as runtimes or editors, not as the source of truth.
- Promote autonomy only after wiki health and evaluation runs show the workflow is reliable.

## Phase 1: Sources And LLM-Wiki Alignment

**Goal:** Make the current `raw -> ingest -> wiki -> ask` loop conform to a durable LLM-Wiki workflow.

**Current baseline:**

- `raw/` stores text, web, PDF, and migrated notes.
- `ingest` creates reviewable proposals.
- Accepted proposals write `wiki/*.md`.
- Ask can cite wiki/raw and create writeback proposals.

**Build next:**

- [ ] Add explicit `/api/ask/{id}/deposit` while keeping `/api/ask/{id}/writeback` compatible.
- [ ] Support whole-answer deposit.
- [ ] Support selected-excerpt deposit.
- [ ] Keep all Ask deposits entering ingest review.
- [ ] Make the Ask UI use `沉淀这次回答` as a fixed primary action.
- [ ] Add first wiki health checks: missing frontmatter, missing source references, broken internal links, orphan pages.

**Implementation plan:** [Ask-to-Deposit Main Flow Implementation Plan](2026-06-04-ask-to-deposit-main-flow.md)

**Acceptance criteria:**

- A user can import sources, review proposals, accept wiki pages, ask questions, and deposit useful answers back into review.
- Wiki files remain readable outside Inkdesk.
- Ask deposit never silently edits canonical wiki files.
- Wiki health can report at least the first four structural issues.

## Phase 2: Vault Schema Layer

**Goal:** Add agent-facing schema files that define how the LLM-Wiki should be maintained.

**Build:**

- [ ] Create lazy vault directories: `schema/`, `skills/`, `evals/`, `runs/`.
- [ ] Add initial schema files:
  - `schema/vault-layout.md`
  - `schema/wiki-page-template.md`
  - `schema/source-citation-rules.md`
  - `schema/ingest-proposal-rules.md`
  - `schema/ask-answer-rules.md`
  - `schema/wiki-health-rules.md`
- [ ] Add backend helpers to ensure these directories and default schema files exist.
- [ ] Add UI read-only browser for schema files, or expose them under an early Workbench section.

**Acceptance criteria:**

- A fresh local vault can initialize schema files without manual setup.
- The schema files can be opened in Obsidian or any Markdown editor.
- Backend tests prove initialization is idempotent.

## Phase 3: Skill Repository And Skill Workbench

**Goal:** Treat skills as first-class workflow files, not hidden prompts inside code.

**Build:**

- [ ] Define Inkdesk skill file format.
- [ ] Decide whether v1 uses `skills/<skill-name>/SKILL.md` or a simpler Markdown frontmatter format.
- [ ] Seed initial skills:
  - `ingest-source`
  - `patch-wiki-page`
  - `answer-from-wiki`
  - `create-research-brief`
  - `run-wiki-health-check`
  - `extract-insight-from-chat`
- [ ] Add Skill Workbench list page.
- [ ] Add skill detail page showing purpose, inputs, context, output contract, safety rules, and verification.
- [ ] Add export path for Codex/Claude-compatible skill files where possible.

**Acceptance criteria:**

- A skill is inspectable as a file and visible in the UI.
- A user can understand what a skill does without reading application code.
- No skill can directly mutate wiki; outputs become proposals or run records.

## Phase 4: Agent Runtime Runs

**Goal:** Add controlled skill runs with traceable inputs, outputs, and review state.

**Build:**

- [ ] Add run records in database.
- [ ] Add `runs/` vault output convention.
- [ ] Add API to start a skill run.
- [ ] Store resolved context, runtime choice, output, errors, and proposed wiki changes.
- [ ] Convert wiki-changing outputs into ingest proposals.
- [ ] Add Agent Run Console for recent runs.

**Acceptance criteria:**

- A skill run can be reproduced from recorded input/context/output.
- Runtime errors do not pollute wiki.
- Proposed wiki changes still pass through review.

## Phase 5: Evaluation Layer

**Goal:** Add golden tasks and rubrics before increasing autonomy.

**Build:**

- [ ] Add `evals/golden-tasks/` storage.
- [ ] Add rubric file format.
- [ ] Add evaluation run records.
- [ ] Allow isolated evaluation runs that do not mutate canonical wiki.
- [ ] Compare skill/wiki versions across runs.
- [ ] Add promotion gate fields for skill version, schema version, and runtime configuration.

**Acceptance criteria:**

- Evaluation runs are visible and repeatable.
- A failed evaluation cannot change accepted wiki.
- Changes to skills or schema can be compared before promotion.

## Phase 6: Harness And Autonomy Gates

**Goal:** Only after the previous layers are stable, add multi-step harness behavior.

**Build:**

- [ ] Add staged run orchestration.
- [ ] Add gates between stages.
- [ ] Add retry and rollback records.
- [ ] Add manual approval checkpoints.
- [ ] Allow higher autonomy only for workflows with passing evaluation history.

**Acceptance criteria:**

- Harness records every stage decision.
- Owner can pause, reject, retry, or roll back a run.
- Higher autonomy is opt-in and evaluation-backed.

## Current Priority

Start with Phase 1.

The immediate implementation target is still Ask deposit, but the reason is now different:

```text
Ask deposit is the LLM-Wiki write path required before Schema, Skills, Evaluation, and Harness can compound safely.
```

Do not start Skill Workbench implementation until Phase 1 has:

- Whole-answer deposit.
- Selected-excerpt deposit.
- Review-first proposal flow.
- Basic wiki health checks.

## Commit Strategy

Recommended sequence:

```bash
git commit -m "feat: add ask deposit endpoint"
git commit -m "feat: support selected ask deposit"
git commit -m "feat: make ask deposit the primary action"
git commit -m "feat: add basic wiki health checks"
git commit -m "feat: initialize vault schema directories"
git commit -m "feat: add initial skill repository"
```

## Out Of Scope Until Later Phases

- External MCP server before Skill Workbench exists.
- Autonomous multi-step runs before evaluation exists.
- Silent wiki writes.
- Team/multi-user knowledge base behavior.
- Obsidian-specific hard dependency.

## Reference Documents

- [LLM-Wiki + Skill Workbench Product Design](../specs/2026-06-04-llm-wiki-skill-workbench-design.md)
- [Ask-to-Deposit Main Flow Implementation Plan](2026-06-04-ask-to-deposit-main-flow.md)
- [Product Roadmap](../../product/product-roadmap.md)
