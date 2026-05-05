# Inkvault

> A single-owner, private, vault-first LLM Wiki.

Inkvault is being shaped around a simple research loop:

```text
raw -> ingest -> wiki
```

`raw/` stores imported webpages, PDFs, and migrated internal notes. `ingest` is the AI proposal and human review workflow. `wiki/` stores the accepted knowledge pages that become long-term memory.

The vault is the source of truth. The database indexes files, queues ingest proposals, and caches read models, but accepted knowledge must be recoverable from vault markdown.

## Product Model

- Private single-owner workspace, protected by a hidden owner login.
- No public publishing surface in the primary product.
- No plans module in the primary product.
- AI may suggest wiki creation or patches, but it never silently edits canonical knowledge.
- Every accepted claim must preserve provenance back to raw source material.

## Current App Shape

- `/app`: Today Vault Panel
- `/app/raw`: raw materials in the vault
- `/app/ingest`: AI-generated proposals awaiting accept/reject
- `/app/wiki`: accepted knowledge pages
- `/app/wiki/[id]`: wiki page detail with understanding, claims, questions, and sources
- `/app/ask`: grounded questions over wiki first, raw second

Legacy routes such as `/app/inbox`, `/app/review`, `/app/topics`, and `/app/sources` are compatibility redirects only.

## Tech Stack

- Frontend: `Next.js 15`, `React 19`, `TypeScript`, `Tailwind CSS`
- Backend: `FastAPI`, `Python 3.12`, `SQLAlchemy`, `LangGraph`
- Storage: PostgreSQL for indexes and workflow state, configurable local vault for markdown files
- Testing: `node:test`, `Vitest`, `Playwright`, `pytest`

## Quick Start

```powershell
Copy-Item infra/.env.example infra/.env
Copy-Item web/.env.local.example web/.env.local
```

Set a strong `INKVAULT_AUTH_SECRET` and optionally set the vault root:

```powershell
$env:INKVAULT_AUTH_SECRET='replace-with-a-long-random-secret'
$env:INKVAULT_VAULT_ROOT='C:\path\to\inkvault-vault'
$env:INKVAULT_AGENT_PROVIDER_PROFILE='openai' # or 'deepseek'
```

Start infrastructure:

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

Start the backend:

```powershell
cd server
python -m pip install -e .[dev]
python -m uvicorn inkvault_server.main:app --host 0.0.0.0 --port 8080
```

Start the frontend:

```powershell
cd web
npm install
npm run dev
```

Open `http://localhost:3000/login`.

Demo owner credentials:

- email: `owner@inkvault.local`
- password: `inkvault-owner`

## Verification

```powershell
cd server
python -m pytest
```

```powershell
cd web
npm test
npm run typecheck
npm run lint
npm run build
```
