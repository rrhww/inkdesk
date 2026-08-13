# F01 Execution Plan

Source plan: `docs/superpowers/plans/2026-07-11-f01-current-contract-recovery-baseline-implementation.md`.

## Scope and constraints

- Deliver behavior contracts and a real PostgreSQL/Vault recovery baseline without changing product behavior.
- Execute A -> B -> C in order. Do not advance after an unverified increment.
- Keep real evidence only in `.local/f01-baseline/`; commit only sanitized contracts and documentation.
- Preserve pre-existing worktree changes.

## Progress

1. [completed] A1: Manifest validation and restore guardrails (TDD).
2. [completed] A2: OpenAPI snapshot and critical behavioral contracts.
3. [in progress] A3: Representative-record snapshot is committed; PostgreSQL schema snapshot awaits the default Docker stack.
4. [in progress] B: Browser flow specification and full-stack runner are implemented; a real-browser baseline awaits the default Docker stack.
5. [in progress] C: Paired backup, isolated restore, verification, and documentation are implemented; a real Docker evidence run is blocked by external package-registry connectivity.
6. [pending] Complete end-to-end F01 acceptance checks after the default Docker stack can build and start.
