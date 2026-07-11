# F01 Baseline Tools

F01 captures behavior contracts and performs a PostgreSQL/Vault recovery drill before structural migration work. Committed contracts are under `docs/delivery/baselines/f01/`; real dumps, manifests, logs, checksums, and recovered files are only written below `.local/f01-baseline/`.

Default Docker mode reads `infra/docker-compose.local-docker.yml` and discovers service IDs, ports, database credentials, and the Vault mount at runtime. It never assumes a fixed container name, database name, or port. Docker mode requires the `local-postgres`, `local-server`, and `local-web` services to be running and healthy.

Run an entire new baseline evidence capture with:

```powershell
pwsh -File scripts/f01/capture-baseline.ps1 -Mode all
```

The recovery target database is generated with the `inkdesk_f01_restore_` prefix. The source database, PostgreSQL system databases, arbitrary database names, the active Vault, non-empty recovery directories, ZIP path traversal, symlinks, reparse points, and case-colliding archive entries are rejected.

`-Mode all` holds the source web/server services stopped across backup and restore to maintain a paired database/Vault snapshot, then restores their prior running state in `finally`. The isolated restore database and Vault target are removed by default. Use `-KeepRestoreTarget` only for investigation; the report records that decision.

Host mode requires explicit source database URL, Vault path, recovery database URL, and recovery Vault target. It intentionally does not infer host `pg_dump` or `pg_restore` paths.

Do not treat a skipped SQLite test as PostgreSQL evidence. `INKDESK_TEST_PGVECTOR_URL` is required for the integration suite. A missing value is an `ENVIRONMENT_ERROR`, not a known issue.
