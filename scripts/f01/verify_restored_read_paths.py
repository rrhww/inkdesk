"""Read F01 recovery endpoints using an isolated app configuration without emitting record data."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


READ_PATHS = [
    "/actuator/health",
    "/api/vault/status",
    "/api/raw",
    "/api/ingest",
    "/api/wiki",
    "/api/runs",
    "/api/compile/queue",
]


def verify_read_paths(database_url: str, vault_root: Path) -> dict[str, Any]:
    os.environ["INKDESK_DB_URL"] = database_url
    os.environ["INKDESK_VAULT_ROOT"] = str(vault_root)
    os.environ["INKDESK_AGENT_RUNTIME"] = "deterministic"
    os.environ["INKDESK_ENABLE_LOCAL_SEED"] = "false"
    os.environ["INKDESK_ENABLE_WEB_ASSIST"] = "false"

    from inkdesk_server import compile_worker
    from inkdesk_server.research import ResearchWorkspaceService

    class NoopCompileWorker:
        def start(self) -> None:
            return None

        def stop(self) -> None:
            return None

        def enqueue(self, _task_id: str) -> None:
            return None

    compile_worker.get_compile_worker = lambda _settings: NoopCompileWorker()  # type: ignore[assignment]
    ResearchWorkspaceService.bootstrap_seed_data = lambda _service: None
    ResearchWorkspaceService.ensure_research_seed_state = lambda _service: None
    from fastapi.testclient import TestClient
    from inkdesk_server.main import app

    statuses: list[dict[str, Any]] = []
    with TestClient(app, cookies={"inkdesk_owner_session": "owner"}) as client:
        for path in READ_PATHS:
            response = client.get(path)
            statuses.append({"path": path, "statusCode": response.status_code, "status": "PASS" if response.status_code == 200 else "FAIL"})
    return {"paths": statuses, "status": "PASS" if all(item["status"] == "PASS" for item in statuses) else "FAIL"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--vault-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    result = verify_read_paths(arguments.database_url, arguments.vault_root)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
