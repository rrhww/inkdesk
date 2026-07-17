from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = ET.parse(args.junit).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    failures = sum(int(suite.attrib.get("failures", "0")) + int(suite.attrib.get("errors", "0")) for suite in suites)
    tests = sum(int(suite.attrib.get("tests", "0")) for suite in suites)
    payload = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "checks": {"tests": tests, "failures": failures},
        "overallStatus": "PASS" if failures == 0 and tests > 0 else "FAIL",
    }
    payload["sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return 0 if payload["overallStatus"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
