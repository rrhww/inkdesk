from __future__ import annotations

import hashlib
import json
from pathlib import Path


def build_space_report(*, f01_manifest: Path, checks: list[dict[str, object]]) -> dict[str, object]:
    manifest = json.loads(f01_manifest.read_text(encoding="utf-8"))
    if manifest.get("overallStatus") != "PASS":
        raise ValueError("F04 verification requires PASS F01 evidence")
    result = {"f01RunId": manifest.get("runId"), "checks": checks}
    result["overallStatus"] = "PASS" if all(check.get("status") == "PASS" for check in checks) else "FAIL"
    result["sha256"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return result
