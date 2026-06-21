from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from inkdesk_server.core.config import Settings
from inkdesk_server.health_service import HealthService
from inkdesk_server.vault import VaultService

MANIFEST_FILENAME = "manifest.json"
MAX_HISTORY_LIMIT = 100
DEFAULT_HISTORY_LIMIT = 20
EVALS_HEALTH_DIR = "evals/health"
RUNS_SUBDIR = "runs"


@dataclass
class HealthHistoryService:
    settings: Settings
    vault: VaultService

    def save_snapshot(self, scan_result: dict) -> dict:
        """Persist a health snapshot to evals/health/runs/<run-id>/manifest.json."""
        from inkdesk_server.health_rules import RULE_VERSION
        from inkdesk_server.vault import VaultService as VS

        run_id = self._generate_run_id()
        run_dir = f"{EVALS_HEALTH_DIR}/{RUNS_SUBDIR}/{run_id}"
        evaluated_at = scan_result.get("evaluatedAt", datetime.now(timezone.utc).isoformat())

        vault_service = self.vault
        vault_type = vault_service.get_status().get("vaultType", "unknown")

        # Trim findings to minimal serializable form
        safe_findings = []
        for f in scan_result.get("findings", []):
            safe_findings.append({
                "type": f["type"],
                "severity": f["severity"],
                "page": f["page"],
                "detail": f["detail"],
                "ruleId": f.get("ruleId"),
                "fingerprint": f.get("fingerprint"),
            })

        cat = scan_result.get("categoryCounts", {})
        manifest = {
            "healthRunId": run_id,
            "vaultType": vault_type,
            "ruleVersion": RULE_VERSION,
            "evaluatedAt": evaluated_at,
            "durationMs": scan_result.get("durationMs"),
            "healthScore": scan_result.get("healthScore"),
            "gateStatus": scan_result.get("gateStatus", "UNKNOWN"),
            "categoryCounts": {
                "error": cat.get("error", 0),
                "warning": cat.get("warning", 0),
                "info": cat.get("info", 0),
            },
            "totalPages": scan_result.get("summary", {}).get("totalPages", 0),
            "findingCount": len(safe_findings),
            "findings": safe_findings,
        }

        vault_service.write_vault_file(f"{run_dir}/{MANIFEST_FILENAME}",
                                       json.dumps(manifest, ensure_ascii=False, indent=2))
        return manifest

    def list_runs(self, limit: int = DEFAULT_HISTORY_LIMIT) -> list[dict]:
        """Return recent snapshots, newest first."""
        limit = min(max(limit, 1), MAX_HISTORY_LIMIT)
        runs_dir = self._runs_root()
        manifests = []
        for run_dir_path in sorted(runs_dir.glob("*"), reverse=True):
            if not run_dir_path.is_dir():
                continue
            mf = run_dir_path / MANIFEST_FILENAME
            if not mf.is_file():
                continue
            try:
                data = json.loads(mf.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError):
                continue
            manifests.append(data)
            if len(manifests) >= limit:
                break
        return manifests

    def get_run(self, run_id: str) -> dict | None:
        """Return a single snapshot manifest."""
        self._validate_run_id(run_id)
        mf_path = self._run_manifest_path(run_id)
        try:
            data = json.loads(mf_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            return None
        return data

    def diff(self, run_id_a: str, run_id_b: str) -> dict:
        """Compare two runs by fingerprint: new, continued, resolved."""
        a = self.get_run(run_id_a)
        b = self.get_run(run_id_b)
        if a is None or b is None:
            return {"error": "one or both runs not found"}

        fps_a = {f["fingerprint"]: f for f in a.get("findings", []) if f.get("fingerprint")}
        fps_b = {f["fingerprint"]: f for f in b.get("findings", []) if f.get("fingerprint")}

        keys_a = set(fps_a.keys())
        keys_b = set(fps_b.keys())

        new_keys = keys_b - keys_a
        continued_keys = keys_a & keys_b
        resolved_keys = keys_a - keys_b

        return {
            "newCount": len(new_keys),
            "continuedCount": len(continued_keys),
            "resolvedCount": len(resolved_keys),
            "new": [fps_b[k] for k in sorted(new_keys)],
            "continued": [fps_b[k] for k in sorted(continued_keys)],
            "resolved": [fps_a[k] for k in sorted(resolved_keys)],
        }

    def trend(self, limit: int = DEFAULT_HISTORY_LIMIT) -> dict:
        """Return current scan result and recent snapshots with diffs."""
        service = HealthService(self.settings, self.vault)
        current = service.scan()
        runs = self.list_runs(limit)

        summaries = []
        for i, run in enumerate(runs):
            diff = {"newCount": 0, "continuedCount": 0, "resolvedCount": 0}
            if i + 1 < len(runs):
                # Compare this run (older) with next (newer)
                diff = self._compute_diff_summary(run, runs[i + 1])
            summaries.append({
                "healthRunId": run["healthRunId"],
                "evaluatedAt": run["evaluatedAt"],
                "healthScore": run.get("healthScore"),
                "gateStatus": run.get("gateStatus", "UNKNOWN"),
                "totalPages": run.get("totalPages", 0),
                "findingCount": run.get("findingCount", 0),
                "diff": diff,
            })

        current_summary = {
            "healthRunId": None,
            "evaluatedAt": current.get("evaluatedAt"),
            "healthScore": current.get("healthScore"),
            "gateStatus": current.get("gateStatus", "UNKNOWN"),
            "totalPages": current.get("summary", {}).get("totalPages", 0),
            "findingCount": len(current.get("findings", [])),
            "diff": None,
        }

        return {
            "current": current_summary,
            "recent": summaries,
            "currentFindings": current.get("findings"),
        }

    def _compute_diff_summary(self, older: dict, newer: dict) -> dict:
        fps_old = {f["fingerprint"] for f in older.get("findings", []) if f.get("fingerprint")}
        fps_new = {f["fingerprint"] for f in newer.get("findings", []) if f.get("fingerprint")}
        return {
            "newCount": len(fps_new - fps_old),
            "continuedCount": len(fps_old & fps_new),
            "resolvedCount": len(fps_old - fps_new),
        }

    def _runs_root(self) -> Path:
        return self.vault.root / EVALS_HEALTH_DIR / RUNS_SUBDIR

    def _generate_run_id(self) -> str:
        now_utc = datetime.now(timezone.utc)
        ts = now_utc.strftime("%Y%m%dT%H%M%SZ")
        return f"health-{ts}"

    def _validate_run_id(self, run_id: str) -> None:
        if not run_id or not run_id.strip():
            raise ValueError("run_id is required")
        # Only allow alphanumeric, hyphens, underscores
        if not all(c.isalnum() or c in "_-." for c in run_id):
            raise ValueError(f"Invalid run_id: {run_id}")
        if len(run_id) > 200:
            raise ValueError("run_id too long")

    def _run_manifest_path(self, run_id: str) -> Path:
        return self._runs_root() / run_id / MANIFEST_FILENAME
