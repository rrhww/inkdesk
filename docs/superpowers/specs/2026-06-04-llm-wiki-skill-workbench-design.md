# LLM-Wiki + Skill Workbench Product Design

## Context

Inkdesk is currently shaped as a vault-first private knowledge system with this core loop:

```text
raw -> ingest -> wiki -> ask
```

The article "AI研发自动化：Wiki知识库+技能包" describes a related but more execution-oriented pattern:

```text
Sources -> LLM-Wiki -> Schema -> Skills -> Agent Runtime -> Evaluation -> Harness
```

The article's useful insight is not that Inkdesk should copy a Claude Code workflow directly. Its stronger lesson is that long-lived AI systems need four durable layers:

- A file-first knowledge base that can be inspected, versioned, and edited outside the product.
- A schema layer that teaches agents how to maintain the knowledge base.
- A skill layer that turns repeated work into explicit, reusable procedures.
- An evaluation and harness layer that checks quality before increasing autonomy.

Inkdesk should absorb this structure while keeping its own product direction: a private owner workbench that makes the system usable every day.

## Product Position

Inkdesk should become the control plane for a personal LLM-Wiki and skill-driven agent workspace.

```text
Inkdesk manages memory, skills, evaluations, run state, and review.
Claude Code, Codex, LangGraph, or other runtimes may execute work.
Obsidian or a normal editor may inspect and edit the vault.
```

The product should not try to replace every agent runtime. Instead, it should make the memory and workflow substrate reliable, visible, and reusable.

## Goals

- Make the existing vault model more explicitly compatible with LLM-Wiki practice.
- Treat skills as first-class product objects, not hidden prompts inside application code.
- Preserve file-system portability so advanced users can use Obsidian, Git, Claude Code, or Codex directly.
- Add quality governance through wiki health checks and skill evaluation.
- Keep human review in the loop before canonical wiki changes are accepted.

## Non-Goals

- Do not build a fully autonomous agent execution system in the first iteration.
- Do not require Obsidian, Claude Code, or any single vendor runtime for core product use.
- Do not silently let AI rewrite accepted wiki knowledge.
- Do not turn the MVP into a multi-user team KB product.
- Do not expose public publishing or collaboration surfaces as part of this effort.

## Target Shape

Inkdesk should evolve toward this layered model:

```text
Vault
  raw/        original source material, read-only truth source
  wiki/       accepted long-term knowledge pages
  schema/     agent-facing rules for maintaining the wiki
  skills/     reusable workflow instructions
  evals/      golden tasks, rubrics, and evaluation runs
  runs/       agent run records, outputs, and review state

Application
  Raw Library
  Ingest Review
  Wiki Browser
  Ask / Research Chat
  Skill Workbench
  Wiki Health
  Evaluation Harness
  Agent Run Console
```

The application can continue using PostgreSQL for indexes, queues, and cached read models. Vault Markdown remains the recoverable source of truth.

## Core Concepts

### LLM-Wiki

The wiki is not a document dump. It is a compiled knowledge layer created from raw sources and improved over time.

Knowledge should enter the wiki through reviewable proposals:

```text
raw source -> ingest proposal -> human review -> accepted wiki patch
```

Ask and research chat should also be able to produce proposals:

```text
ask answer -> save insight -> ingest proposal -> human review -> wiki patch
```

### Schema

Schema files are agent-facing operating rules. They explain how the wiki should be maintained.

Initial schema files should cover:

- Directory conventions.
- Wiki page templates.
- Source citation and provenance rules.
- Ingest proposal rules.
- Query answer rules.
- Wiki lint and health rules.

These files should live in the vault so they can be used by Inkdesk, Codex, Claude Code, or other agents.

### Skills

Skills are reusable workflow procedures. They should be stored as files and surfaced in the UI.

Initial product skills should be modest and knowledge-centered:

- Ingest Source.
- Patch Wiki Page.
- Answer From Wiki.
- Create Research Brief.
- Run Wiki Health Check.
- Extract Reusable Insight From Chat.

Later, if Inkdesk expands back into software delivery workflows, it can add development skills:

- Write Technical Plan.
- Review Technical Plan.
- Implement From Plan.
- Prepare Test Plan.
- Diagnose Issue.

The important shift is that a skill is not just a prompt. It is a named workflow with inputs, required context, output contract, safety rules, and verification expectations.

### Evaluation Harness

Inkdesk needs a lightweight evaluation layer before it increases autonomy.

The first evaluation harness should support:

- Golden tasks stored as Markdown or JSON.
- Rubrics that describe expected answer quality.
- Isolated evaluation runs that do not mutate canonical wiki files.
- Basic score records and comparison between runs.

The first version does not need statistically rigorous scoring. It only needs to make improvement visible and prevent blind prompt drift.

### Wiki Health

Wiki Health is the quality dashboard for the vault.

Initial checks:

- Missing source references.
- Broken internal links.
- Orphan wiki pages.
- Very short pages that are likely stubs.
- Duplicate titles or duplicate aliases.
- Pages without required frontmatter.
- Accepted wiki pages whose referenced raw source is missing.

Later checks:

- Contradiction candidates.
- Stale pages.
- Overlapping concepts that should be merged.
- Concepts mentioned often but not promoted to pages.
- Skills whose outputs repeatedly fail review.

## User Experience

### Owner Home

The owner home should eventually show the system as a living workbench:

- Recent sources added.
- Ingest proposals waiting for review.
- Wiki health score and top issues.
- Recent ask insights that can be saved.
- Recent skill runs.
- Suggested maintenance tasks.

### Skill Workbench

The Skill Workbench should let the owner:

- Browse available skills.
- See what each skill is for.
- Start a skill run with the right inputs.
- Review the produced output.
- Accept, reject, or revise proposed wiki changes.
- Export compatible skill files for external agent tools where possible.

The UI should hide prompt-file complexity by default, but the underlying files should remain inspectable.

### Ask to Wiki

Ask should become a memory-building interface, not only a question-answering interface.

After a useful answer, the owner should be able to choose:

- Keep as chat only.
- Save as a new wiki proposal.
- Patch an existing wiki page.
- Create a follow-up research task.

The default should stay safe: no silent canonical edits.

## Data Flow

### Source Ingest

```text
Owner adds raw source
Backend stores raw markdown and metadata
Agent creates ingest proposal
Owner reviews proposal
Accepted proposal writes wiki markdown
Database indexes wiki page and source links
```

### Skill Run

```text
Owner starts skill
Inkdesk resolves required vault context
Runtime executes skill in a controlled run
Output is saved under runs/
Any wiki change is converted into a proposal
Owner reviews before acceptance
```

### Wiki Health

```text
Owner or schedule starts health check
Rules scan vault files
Results are saved as a health run
UI shows score, issues, and suggested fixes
Fixes become proposals, not silent edits
```

## Architecture Notes

### Vault Layout

The vault should remain portable. A future vault may contain:

```text
raw/
wiki/
schema/
skills/
evals/
runs/
```

Existing deployments do not need to migrate immediately. The first implementation can create missing directories lazily.

### Database Role

PostgreSQL should continue to store:

- Index records.
- Review queue state.
- Ask history.
- Skill run metadata.
- Evaluation run metadata.
- Health issue summaries.

The database should not become the only place where accepted knowledge exists.

### Runtime Role

The first implementation can use the existing backend agent runtime. The design should not assume one permanent runtime.

Possible runtimes:

- Existing LangGraph backend.
- Codex or Claude Code through exported files and manual execution.
- Future local agent runners.

Inkdesk owns orchestration state and review. The runtime owns execution.

## Safety Rules

- AI-generated wiki changes must become reviewable proposals.
- Accepted wiki pages must preserve provenance to raw sources or prior accepted pages.
- Skill runs must record input, resolved context, output, and acceptance state.
- Evaluation runs must not mutate canonical wiki files.
- External tool execution should be optional and explicitly started by the owner.

## Suggested Phases

### Phase 1: LLM-Wiki Alignment

- Add vault-level `schema/` and `skills/` conventions.
- Document initial schema files.
- Add Ask-to-Wiki proposal flow.
- Add basic wiki health checks.

### Phase 2: Skill Workbench

- Add skill list UI.
- Add skill detail pages.
- Add skill run records.
- Convert outputs into reviewable proposals.
- Support exportable skill files.

### Phase 3: Evaluation Harness

- Add golden task storage.
- Add evaluation run records.
- Add simple rubric scoring.
- Compare skill or wiki versions across runs.

### Phase 4: Agent Harness

- Add multi-step run orchestration.
- Add gates between stages.
- Add rollback and retry records.
- Allow higher autonomy only where evaluation and review history support it.

## Acceptance Criteria For This Design Direction

- A new contributor can explain how Inkdesk differs from a normal RAG app.
- A vault can be opened outside Inkdesk without losing core knowledge.
- A skill can be inspected as a file and also launched from the UI.
- Ask can produce a wiki proposal without silently editing accepted knowledge.
- Wiki health can identify at least broken links, orphan pages, missing sources, and missing frontmatter.
- The architecture remains compatible with external agent runtimes rather than locked to one provider.

## Open Decisions

- Whether `skills/` should use Codex/Claude-style `SKILL.md` directories from the start or a simpler Inkdesk-native frontmatter format.
- Whether `evals/` should be Markdown-first or JSON-first.
- Whether runs should be stored primarily in the vault, the database, or both.
- How much Obsidian-specific metadata should be supported without making Obsidian a dependency.

## Recommendation

Use a hybrid model:

```text
Markdown-first files for portability.
Database indexes for product speed and workflow state.
UI-first review for safety.
Runtime-agnostic skill execution for future flexibility.
```

This lets Inkdesk absorb the strongest idea from the article: durable knowledge and reusable skills compound over time. It also keeps Inkdesk's own advantage: turning that expert workflow into a coherent personal workbench instead of a pile of files and command-line rituals.
