# Python Main Backend Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Java Spring Boot main backend with a Python FastAPI backend while preserving the current vault-first research product behavior and API contract used by the Next.js frontend.

**Architecture:** Build a new Python backend inside `server/`, keep the current PostgreSQL schema and vault file conventions, and inline the existing LangGraph runtime from `agent-service`. Migrate behavior in vertical slices: platform/bootstrap, data model, vault/auth, research APIs, then remove Java runtime dependencies after verification.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, LangGraph, httpx, pypdf, pytest

---

### Task 1: Build Python server foundation

**Files:**
- Create: `server/pyproject.toml`
- Create: `server/app/main.py`
- Create: `server/app/core/config.py`
- Create: `server/app/core/deps.py`
- Create: `server/app/api/__init__.py`
- Create: `server/tests/test_health.py`
- Modify: `infra/docker-compose.yml`
- Modify: `README.md`
- Modify: `server/README.md`

- [ ] Write failing health and startup tests for the Python backend shell.
- [ ] Implement FastAPI app factory, config loading, and `/health`.
- [ ] Add Python packaging and runtime entrypoint for `server/`.
- [ ] Update local/dev docs to start Python backend instead of Maven.
- [ ] Run focused Python tests for the bootstrap slice.

### Task 2: Port database and vault infrastructure

**Files:**
- Create: `server/app/db/base.py`
- Create: `server/app/db/session.py`
- Create: `server/app/models/*.py`
- Create: `server/alembic.ini`
- Create: `server/alembic/env.py`
- Create: `server/alembic/versions/*.py`
- Create: `server/app/vault/service.py`
- Create: `server/app/vault/markdown.py`
- Create: `server/tests/test_vault_service.py`
- Create: `server/tests/test_db_models.py`
- Reuse logic from: `server/src/main/resources/db/migration/*.sql`

- [ ] Write failing tests for vault initialization, path safety, and atomic writes.
- [ ] Write failing tests for core SQLAlchemy models against the current schema semantics.
- [ ] Port DB models and session management.
- [ ] Port vault initialization and markdown rendering helpers.
- [ ] Port Flyway migrations into Alembic-managed Python migrations.
- [ ] Run the focused vault and model tests.

### Task 3: Port auth and owner session flow

**Files:**
- Create: `server/app/api/auth.py`
- Create: `server/app/services/auth_service.py`
- Create: `server/app/core/security.py`
- Create: `server/tests/test_auth_api.py`
- Reuse semantics from: `server/src/main/java/com/inkvault/server/auth/mock/*`

- [ ] Write failing API tests for login, logout, and `/api/auth/me`.
- [ ] Implement owner session cookie issuance and validation with existing cookie semantics.
- [ ] Implement the auth routes and dependency guards.
- [ ] Run auth tests and fix contract mismatches.

### Task 4: Port raw/ingest/wiki/ask data contracts and repositories

**Files:**
- Create: `server/app/schemas/research.py`
- Create: `server/app/repositories/research.py`
- Create: `server/tests/test_research_contracts.py`
- Reuse semantics from: `server/src/main/java/com/inkvault/server/research/ResearchApiModels.java`

- [ ] Write failing tests that assert the Python response/request models match the current frontend contract.
- [ ] Implement Pydantic schemas for dashboard, raw, ingest, wiki, and ask.
- [ ] Implement repository helpers for sources, topics, review items, ask turns, and legacy note imports.
- [ ] Run contract tests.

### Task 5: Port LangGraph runtime into the Python main backend

**Files:**
- Create: `server/app/agents/runtime.py`
- Create: `server/app/agents/graphs/ask.py`
- Create: `server/app/agents/graphs/compile.py`
- Create: `server/app/agents/fallback.py`
- Create: `server/tests/test_agent_runtime.py`
- Reuse logic from: `agent-service/app/*`

- [ ] Write failing tests for `ask` and `compile` runtime behavior.
- [ ] Move the current LangGraph sidecar logic into the new backend package.
- [ ] Preserve deterministic fallback behavior for missing model credentials.
- [ ] Run agent runtime tests.

### Task 6: Port research workspace service and APIs

**Files:**
- Create: `server/app/services/research_workspace.py`
- Create: `server/app/services/ingest_proposal.py`
- Create: `server/app/services/web_import.py`
- Create: `server/app/services/pdf_import.py`
- Create: `server/app/api/home.py`
- Create: `server/app/api/raw.py`
- Create: `server/app/api/ingest.py`
- Create: `server/app/api/wiki.py`
- Create: `server/app/api/ask.py`
- Create: `server/tests/test_research_api.py`
- Reuse logic from: `server/src/main/java/com/inkvault/server/research/*`

- [ ] Write failing API tests for `admin/home`, `raw`, `ingest`, `wiki`, `ask`, and ask writeback.
- [ ] Port raw import, proposal generation, review accept/reject, wiki persistence, and ask flows.
- [ ] Ensure accepted claims and wiki writes preserve provenance and never silently mutate canonical knowledge.
- [ ] Run the research API test suite.

### Task 7: Remove Java runtime path and merge deployment

**Files:**
- Modify: `infra/docker-compose.yml`
- Modify: `infra/.env.example`
- Modify: `web/scripts/fullstack-preflight.mjs`
- Modify: `web/scripts/run-fullstack-e2e.mjs`
- Modify: `web/tests/*` as needed for backend startup changes
- Delete or retire: `agent-service/`
- Delete or retire: Java/Maven server entrypoint files once Python path is verified

- [ ] Update dev and infra scripts to launch the new Python backend.
- [ ] Remove standalone agent-service from the primary runtime path.
- [ ] Retire Java backend startup assumptions from docs and scripts.
- [ ] Run frontend checks against the Python-backed flow.

### Task 8: Final verification

**Files:**
- Verify: `server/tests/*`
- Verify: `web/tests/*`
- Verify: root docs and runtime configs

- [ ] Run `pytest` in `server/`.
- [ ] Run `npm test` in `web/`.
- [ ] Run `npm run typecheck` in `web/`.
- [ ] Run `npm run lint` in `web/`.
- [ ] Run `npm run build` in `web/`.
- [ ] Review the diff for leftover Java runtime dependencies or stale docs.
