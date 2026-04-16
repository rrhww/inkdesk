# Inkdesk

> A personal operating system for long-running projects.

Inkdesk is an open repository for building a personal main system around long-running work.

It is not a public blog with a private dashboard bolted on. The core of Inkdesk is a private system for thinking, planning, recalling context, and moving projects forward. Public publishing exists as a derived output layer.

At the current MVP stage, Inkdesk includes:

- an `Agent Console` as the main entry after login
- a `Knowledge` system for notes and long-term context
- a `Plans` system for tasks and project execution
- `Search / Recall` for bringing past context back into the current workflow
- a `Publish` module for turning mature internal knowledge into public output
- a public reading surface at `/` and `/articles/[slug]`

## Why Inkdesk

Most personal tools stop at one of these layers:

- note-taking
- task management
- publishing
- AI chat

Inkdesk tries to connect them into one working system.

The goal is to make a tool that helps a single owner:

- think clearly
- organize knowledge over time
- decide the next step in a project
- keep public output connected to real internal work

## Who It Is For

Inkdesk is currently best suited for:

- indie builders running long-term personal projects
- researchers, writers, or developers who need notes, plans, and recall in one place
- people who want a private working system first, and publishing second

It is currently **not** designed for:

- teams or multi-user collaboration
- enterprise workflows
- a polished hosted SaaS experience

## Current Status

Inkdesk is in active MVP development.

- Product stage: `MVP / work in progress`
- Product model: `main system first, public output second`
- Auth model: `single-owner`
- Stability: `interfaces and copy may still change`
- Deployment target: `self-host / local-first development`

If you are evaluating the repository, the best way to think about it today is:

> a serious personal system under active construction, not a finished product

## Core Concepts

### 1. Main System

The long-term center of Inkdesk is `/app`.

This is where the high-value behaviors live:

- memory
- planning
- recall
- execution
- agent-assisted organization

### 2. Output Layer

The public surface is intentionally secondary.

It exists to:

- publish selected knowledge
- share public writing
- expose project links

It does **not** define the product's core identity.

### 3. Knowledge As Source of Truth

Notes are not treated as isolated documents.

They are the knowledge substrate that powers:

- agent suggestions
- search and recall
- plan linking
- publishing decisions

## Features

### Main system

- `Agent Console` at `/app`
- `Knowledge Hub` at `/app/library`
- `Plans` at `/app/plans`
- `Search / Recall` at `/app/search`
- `Note Editor` at `/app/notes/[id]`
- `Publish Console` at `/app/publish`

### Public output

- public home at `/`
- public article page at `/articles/[slug]`
- private owner entry at `/login`

### Current routing behavior

- unauthenticated visitors who open `/` see the public output page
- authenticated owners who open `/` are redirected to `/app`
- unauthenticated access to `/app/*` is redirected to `/login`

## Tech Stack

### Frontend

- `Next.js 15`
- `React 19`
- `TypeScript`
- `Tailwind CSS`

### Backend

- `Spring Boot 3`
- `Java 17`
- `Spring Security`
- `Spring Data JPA`
- `Flyway`

### Infrastructure

- `PostgreSQL`
- `MinIO` for local object storage
- `Tencent COS` as the planned production storage target
- `Docker Compose`

### Testing

- `node:test`
- `Vitest`
- `Playwright`

## Repository Structure

```text
.
├─ docs/     product, design, architecture, delivery, ops docs
├─ web/      Next.js frontend
├─ server/   Spring Boot backend
├─ infra/    Docker Compose, env templates, deployment config
├─ scripts/  helper scripts
└─ assets/   design exports and project assets
```

## Quick Start

### Requirements

- `Node.js 20+`
- `npm`
- `Java 17`
- `Docker`

### 1. Copy environment templates

```powershell
Copy-Item infra/.env.example infra/.env
Copy-Item web/.env.local.example web/.env.local
Copy-Item server/src/main/resources/application-local.yml.example server/src/main/resources/application-local.yml
```

Then set `inkdesk.auth.secret` in:

```text
server/src/main/resources/application-local.yml
```

### 2. Start infrastructure

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

### 3. Start the backend

```powershell
cd server
.\mvnw.cmd spring-boot:run -Dspring-boot.run.profiles=local
```

### 4. Start the frontend

```powershell
cd web
npm install
npm run dev
```

### 5. Open the app

- public output: `http://localhost:3000`
- owner login: `http://localhost:3000/login`
- backend health: `http://localhost:8080/actuator/health`
- MinIO console: `http://localhost:9001`

### Demo owner credentials

- email: `owner@inkdesk.local`
- password: `inkdesk-owner`

When `server/` runs with the `local` profile, the owner account and sample workspace data are seeded automatically if they do not already exist.

## Development

### Frontend tests

```powershell
cd web
npm test
```

### Frontend e2e

```powershell
cd web
npm run e2e
```

### Local full-stack acceptance

```powershell
cd web
npm run e2e:fullstack
```

This command expects `PostgreSQL + MinIO + Spring Boot` to already be running locally, waits for the backend health check, and reports local blocker hints if Docker, PostgreSQL, or Spring Boot are not ready.

### Backend tests

```powershell
cd server
.\mvnw.cmd test
```

## Documentation

If you want to understand the product before reading code, start here:

1. [MVP PRD](docs/product/mvp-prd.md)
2. [User Stories](docs/product/user-stories.md)
3. [Information Architecture](docs/design/information-architecture.md)
4. [Page Inventory](docs/design/page-inventory.md)
5. [System Overview](docs/architecture/system-overview.md)
6. [Tech Decisions](docs/architecture/tech-decisions.md)
7. [MVP Roadmap](docs/delivery/mvp-roadmap.md)
8. [Deploy Guide](docs/ops/deploy-guide.md)
9. [Local Full-Stack Acceptance](docs/delivery/local-fullstack-acceptance.md)

The repository treats docs as the source of truth:

- significant product changes should be reflected in docs
- chat history is not the source of truth
- architecture, design, and implementation should stay aligned

## Roadmap

Near-term direction:

- deepen the `Agent Console` as the real system hub
- improve long-term memory and recall flows
- make plans more execution-oriented
- keep publishing as a clean derived capability
- evolve Inkdesk toward a more complete personal operating system

## Contributing

Contributions are welcome, especially around:

- product thinking for personal systems
- UX for single-user knowledge and planning tools
- frontend architecture and interaction design
- backend API design for long-term personal workflows

Before opening a large PR, please prefer opening an issue or discussion first.

Project conventions:

- keep changes focused
- update docs when product or architecture meaning changes
- avoid treating the public layer as the product core
- prefer clear, maintainable implementation over premature complexity

## License

This repository does **not** currently include a `LICENSE` file.

If you plan to make the project formally open source, you should add one before public release. Until then, please do not assume reuse, modification, or commercial rights beyond normal GitHub viewing and collaboration expectations.

## Repository

- GitHub: `https://github.com/rrhww/inkdesk.git`
