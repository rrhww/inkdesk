# F05 Durable Job Evidence

Run `pwsh -File scripts/f05/verify-durable-jobs.ps1` with `INKDESK_TEST_PGVECTOR_URL` pointing to an isolated PostgreSQL/pgvector instance. The verifier covers migration/schema alignment, PostgreSQL `SKIP LOCKED`, an independently spawned worker terminated while holding a lease, stale completion rejection, lease recovery, Compile compatibility, and guarded rollback.

Outputs are written only to `.local/f05-jobs/`. The manifest records the commit, aggregate test result, and checksum; it never includes payloads, Vault contents, credentials, or database URLs.

The durable backend is the default. `INKDESK_JOB_BACKEND=legacy` is an emergency single-process fallback only; it does not provide F05 delivery guarantees and must not run alongside the durable worker.
