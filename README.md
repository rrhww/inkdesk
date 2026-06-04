# Inkdesk

> A private LLM-Wiki and skill-driven agent workbench.

Inkdesk is being shaped as a personal knowledge control plane for AI agents. It absorbs the product pattern described in "AI研发自动化：Wiki知识库+技能包": long-lived AI systems need a durable Wiki, explicit Skills, measurable evaluations, and a Harness that can safely coordinate agent work.

The product direction is:

```text
LLM-Wiki + Skill Workbench + Agent Harness
```

Inkdesk should not try to replace Claude Code, Codex, LangGraph, Obsidian, or future agent runtimes. Instead, it should manage the memory and workflow substrate they need:

```text
Inkdesk manages memory, skills, evaluations, run state, and review.
External agent runtimes execute work.
Vault Markdown remains portable and inspectable.
```

## Product Idea

Inkdesk is not a normal RAG app.

Traditional RAG answers from raw document chunks at query time. Inkdesk is moving toward a write-time knowledge system: sources are compiled into a living Markdown Wiki, queries can produce reviewable Wiki proposals, Skills turn repeated work into reusable workflows, and evaluation checks whether the system is getting better.

The internal research loop still matters:

```text
raw -> ingest -> wiki -> ask
```

- `raw/` stores original source material such as webpages, PDFs, imported notes, and future code or project context.
- `ingest` turns raw material into AI-generated proposals that the owner can accept or reject.
- `wiki/` stores accepted long-term knowledge as Markdown.
- `ask` answers from accepted Wiki first, then raw sources, and can send useful answers back into review.

The next product layer extends that loop:

```text
schema -> skills -> evals -> runs -> harness
```

- `schema/` defines how agents should maintain the Wiki.
- `skills/` stores reusable workflow instructions.
- `evals/` stores golden tasks and rubrics.
- `runs/` records agent outputs, decisions, and review state.
- `harness` coordinates multi-step work with gates, retries, and rollback records.

## Target Shape

The long-term vault layout should stay file-first and portable:

```text
vault/
  raw/        original source material
  wiki/       accepted long-term knowledge pages
  schema/     agent-facing maintenance rules
  skills/     reusable workflow instructions
  evals/      golden tasks, rubrics, and evaluation runs
  runs/       agent run records, outputs, and review state
```

The application sits on top of that vault:

```text
Raw Library
Ingest Review
Wiki Browser
Ask / Research Chat
Skill Workbench
Wiki Health
Evaluation Harness
Agent Run Console
```

PostgreSQL indexes files, queues proposals, stores workflow state, and caches read models. The accepted knowledge itself must remain recoverable from vault Markdown.

## Design Principles

- File-first: accepted knowledge should be readable and versionable outside Inkdesk.
- Review-first: AI can propose Wiki changes, but must not silently rewrite canonical knowledge.
- Skill-first: repeated workflows should be explicit files with inputs, context, output contracts, safety rules, and verification expectations.
- Runtime-agnostic: Inkdesk should be able to work with LangGraph now and external tools like Claude Code or Codex later.
- Evaluation-driven: Wiki and Skill changes should be judged with health checks and golden tasks, not vibes.
- Obsidian-compatible where useful: the vault should remain understandable in normal Markdown tools without making Obsidian a hard dependency.

## Current State

Implemented today:

- Single-owner private workspace and hidden login.
- Vault-first `raw -> ingest -> wiki -> ask` loop.
- Raw text, webpage, and PDF import.
- AI-generated review proposals with accept/reject flow.
- Accepted Wiki pages written back to vault Markdown.
- Ask-first workspace with citations, follow-up context, and writeback proposals.
- Claim-level metadata, source links, usage signals, and review state.
- Local Docker stack with Next.js, FastAPI, PostgreSQL, and pgvector.

In progress as product direction:

- Make Ask-to-Wiki proposal flow feel like a first-class memory-building action.
- Add `schema/` and `skills/` conventions to the vault.
- Add Skill Workbench for browsing, running, and exporting skills.
- Add Wiki Health checks for links, missing sources, missing frontmatter, stubs, and orphan pages.
- Add Evaluation Harness for golden tasks and skill/wiki version comparisons.
- Add Agent Harness only after review and evaluation paths are strong enough.

## Current Routes

- `/` redirects based on owner session.
- `/login` is the hidden owner login.
- `/app` is the Ask-first research workspace.
- `/app/raw` shows original vault material.
- `/app/ingest` shows pending AI proposals.
- `/app/wiki` shows accepted Wiki pages.
- `/app/wiki/[id]` shows a Wiki page with understanding, claims, questions, and sources.
- `/app/ask` is a compatibility alias for the Ask workspace.

Legacy routes such as `/app/inbox`, `/app/review`, `/app/topics`, and `/app/sources` are no longer formal product entry points.

## Tech Stack

- Frontend: `Next.js 16`, `React 19`, `TypeScript`, `Tailwind CSS`
- Backend: `FastAPI`, `Python 3.12`, `SQLAlchemy`, `LangGraph`
- Storage: `PostgreSQL + pgvector` for indexes and workflow state, plus mounted vault Markdown for raw/wiki truth
- Testing: `node:test`, `Vitest`, `Playwright`, `pytest`

## Quick Start

Prepare environment variables:

```bash
cp infra/.env.example infra/.env
```

Set at least:

```env
INKDESK_AUTH_SECRET=replace-with-a-long-random-secret
INKDESK_AGENT_RUNTIME=langgraph
INKDESK_AGENT_PROVIDER_PROFILE=openai
OPENAI_API_KEY=sk-xxxx
INKDESK_AGENT_MODEL=gpt-4.1-mini
INKDESK_EMBEDDING_PROVIDER_PROFILE=openai
INKDESK_EMBEDDING_MODEL=text-embedding-3-small
INKDESK_ENABLE_WEB_ASSIST=true
```

For DeepSeek:

```env
INKDESK_AGENT_RUNTIME=langgraph
INKDESK_AGENT_PROVIDER_PROFILE=deepseek
DEEPSEEK_API_KEY=sk-xxxx
INKDESK_AGENT_MODEL=deepseek-v4-flash
```

Start the local Docker stack:

```bash
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml up -d --build
```

Open:

- App: `http://localhost:3000/login`
- Backend health: `http://localhost:8080/actuator/health`

Default local owner:

- Email: `owner@inkdesk.local`
- Password: `inkdesk-owner`

Stop while keeping data:

```bash
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml down
```

Reset the local demo state:

```bash
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml down -v
```

## Verification

Backend:

```powershell
cd server
python -m pytest
```

Frontend:

```powershell
cd web
npm test
npm run typecheck
npm run lint
npm run build
npm run e2e
npm run e2e:fullstack
```

`npm run e2e` and `npm run e2e:fullstack` should be run serially because both trigger Next.js build/start flows.

## Related Design Notes

- [LLM-Wiki + Skill Workbench Product Design](docs/superpowers/specs/2026-06-04-llm-wiki-skill-workbench-design.md)
- [Product Vision](docs/product/product-vision.md)
- [System Overview](docs/architecture/system-overview.md)
- [Tooling and MCP](docs/architecture/tooling-and-mcp.md)
