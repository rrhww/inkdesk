"""Turn captured command output into an F01 test manifest record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from baseline_contracts import classify_test_result


def _known_issues(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(document, dict) and isinstance(document.get("issues"), list):
        return document["issues"]
    if isinstance(document, list):
        return document
    raise ValueError("known issues document must contain an issues list")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--stdout-file", type=Path, required=True)
    parser.add_argument("--stderr-file", type=Path, required=True)
    parser.add_argument("--stdout-path", required=True)
    parser.add_argument("--stderr-path", required=True)
    parser.add_argument("--known-issues", type=Path, required=True)
    parser.add_argument("--environment-error")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    result = classify_test_result(
        suite=arguments.suite,
        command=arguments.command,
        exit_code=arguments.exit_code,
        duration=arguments.duration,
        stdout=arguments.stdout_file.read_text(encoding="utf-8", errors="replace"),
        stderr=arguments.stderr_file.read_text(encoding="utf-8", errors="replace"),
        known_issues=_known_issues(arguments.known_issues),
        environment_error=arguments.environment_error,
    )
    result["stdout"] = arguments.stdout_path
    result["stderr"] = arguments.stderr_path
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
