# F01 Progress Log

## 2026-07-11

- Read the confirmed F01 implementation plan and selected the A -> B -> C execution order.
- Started A1. No F01 production code exists yet; next action is to add the specified failing guardrail and manifest tests.
- A1 Red: the new tests failed because `baseline_contracts` did not exist.
- A1 Green: implemented manifest/known-issue validation and restore guardrails. `python -m pytest tests/baseline/test_manifest_validation.py tests/baseline/test_restore_guardrails.py -q` passed (26 tests). `git check-ignore -v .local/f01-baseline/example/backup/postgres.dump` confirmed the root ignore rule.
- Started A2: inspect existing app factory isolation before adding OpenAPI exporter tests.
- Completed F01 contract, guardrail, fingerprint, archive, restore-read-path, baseline test, browser-flow, and capture orchestration implementation. Baseline tests currently pass locally; real evidence remains intentionally uncommitted under `.local/`.
- Default Docker F01 execution remains blocked outside the codebase: `local-postgres` cannot install `postgresql-17-pgvector` because Debian/PGDG APT responses terminate with HTTP 500, and `auth.docker.io:443` is not TCP-reachable. Do not mark F01 complete until a new default `capture-baseline.ps1 -Mode all` run produces real PostgreSQL/Vault evidence.
