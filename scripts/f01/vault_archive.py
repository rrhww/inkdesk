"""Create, fingerprint, and securely restore local Vault archives for F01."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from baseline_contracts import create_vault_zip, fingerprint_vault, safe_extract_vault_zip


def _write_json(value: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    fingerprint = subparsers.add_parser("fingerprint")
    fingerprint.add_argument("--source", type=Path, required=True)
    fingerprint.add_argument("--output", type=Path, required=True)
    archive = subparsers.add_parser("archive")
    archive.add_argument("--source", type=Path, required=True)
    archive.add_argument("--archive", type=Path, required=True)
    archive.add_argument("--output", type=Path, required=True)
    extract = subparsers.add_parser("extract")
    extract.add_argument("--archive", type=Path, required=True)
    extract.add_argument("--destination", type=Path, required=True)
    extract.add_argument("--evidence-root", type=Path, required=True)
    extract.add_argument("--active-vault", type=Path, required=True)
    extract.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    if arguments.command == "fingerprint":
        _write_json(fingerprint_vault(arguments.source), arguments.output)
    elif arguments.command == "archive":
        _write_json(create_vault_zip(arguments.source, arguments.archive), arguments.output)
    else:
        safe_extract_vault_zip(
            arguments.archive,
            arguments.destination,
            evidence_root=arguments.evidence_root,
            active_vault=arguments.active_vault,
        )
        _write_json(fingerprint_vault(arguments.destination), arguments.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
