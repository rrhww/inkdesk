# F01 Findings

- F01 must use `infra/docker-compose.local-docker.yml` and discover all runtime values from Compose/runtime state.
- Existing full-stack runner currently selects only `tests/e2e/local-fullstack.spec.ts`.
- Existing test fixtures use a temporary SQLite database, a temporary Vault, and the deterministic agent runtime.
- The worktree has pre-existing changes in `AGENTS.md`, `web/next-env.d.ts`, preview artifacts, local scripts/logs, and an untracked UI directory. They are outside F01 scope.

