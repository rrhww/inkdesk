# AGENTS.md

## Repository Direction

Inkdesk is a local-first **Knowledge Context Runtime** for R&D work: the topic
knowledge board (`/app/wiki`) is the primary product surface, Vault Markdown is
the long-term source of truth, and the MVP runs on the file system plus derived
indexes — do not reintroduce a PostgreSQL business database for the knowledge
board. The knowledge graph, DAG engine, tech-solution skill, and Harness audit
are supporting capabilities. See `docs/product/产品愿景.md`,
`docs/architecture/领域模型.md`, and
`docs/superpowers/plans/2026-08-04-inkdesk-codex-integrated-long-term-roadmap.md`
for the authoritative direction.

## Skill Policy

Do not invoke `omni-superdev` or any `superpowers:*` skill for work in this repository. This project-level rule takes precedence over default skill routing and applies to all tasks in the repository.

## Engineering Rules

- Read the minimal local context required for the task.
- Keep changes scoped and avoid unrelated refactors.
- For bug fixes, write the failing test first, confirm it fails for the expected reason, then fix the bug.
- For user-visible changes in `web/**`, review the affected flow in a real browser before signoff.
- For documentation screenshots in Markdown, avoid fixed `height` attributes on `<img>` tags; prefer Markdown images or width-only HTML so previews preserve aspect ratio.
- Never commit secrets or credentials.
- Keep `.env*.example` files synchronized with required environment variables.
