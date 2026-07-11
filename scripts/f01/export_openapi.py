"""Capture and compare the complete OpenAPI contract without weakening it."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import urlopen

from baseline_contracts import canonical_json


class OpenAPIContractMismatch(AssertionError):
    """The live OpenAPI document changed relative to a checked-in snapshot."""


def canonicalize_openapi(document: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively sort object keys while retaining every OpenAPI field and value."""

    if not isinstance(document, Mapping):
        raise ValueError("OpenAPI document must be a JSON object")
    return json.loads(canonical_json(document))


def ensure_sanitized_contract(document: Mapping[str, Any]) -> None:
    """Reject credentials, machine-local paths, and local server URLs before writing."""

    for location, value in _walk_strings(document):
        normalized = value.casefold()
        if any(marker in normalized for marker in ("bearer ", "token=", "api_key=", "apikey=", "cookie=")):
            raise ValueError(f"unsafe credential-like value at {location}")
        if re.search(r"(?i)(?:^|[^a-z])[a-z]:[\\/]", value):
            raise ValueError(f"unsafe machine-specific path at {location}")
        if normalized.startswith(("/home/", "/users/", "/private/", "/tmp/")):
            raise ValueError(f"unsafe machine-specific path at {location}")
        if re.search(r"https?://(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?(?:/|$)", value, re.IGNORECASE):
            raise ValueError(f"unsafe local server URL at {location}")


def write_openapi_snapshot(document: Mapping[str, Any], snapshot: Path) -> None:
    canonical = canonicalize_openapi(document)
    ensure_sanitized_contract(canonical)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(canonical_json(canonical) + "\n", encoding="utf-8", newline="\n")


def load_openapi_snapshot(snapshot: Path) -> dict[str, Any]:
    try:
        document = json.loads(snapshot.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise OpenAPIContractMismatch(f"OpenAPI snapshot does not exist: {snapshot}") from error
    except json.JSONDecodeError as error:
        raise OpenAPIContractMismatch(f"OpenAPI snapshot is not valid JSON: {snapshot}") from error
    return canonicalize_openapi(document)


def compare_openapi(document: Mapping[str, Any], snapshot: Path) -> None:
    captured = canonicalize_openapi(document)
    expected = load_openapi_snapshot(snapshot)
    if captured != expected:
        raise OpenAPIContractMismatch("OpenAPI contract differs from the checked-in snapshot")


def fetch_openapi(base_url: str, *, timeout_seconds: float = 30.0) -> dict[str, Any]:
    if not base_url or not base_url.strip():
        raise ValueError("An explicit --url is required to capture OpenAPI")
    target = urljoin(base_url.rstrip("/") + "/", "openapi.json")
    try:
        with urlopen(target, timeout=timeout_seconds) as response:  # noqa: S310 - URL is explicit operator input.
            if response.status != 200:
                raise RuntimeError(f"OpenAPI endpoint returned HTTP {response.status}: {target}")
            raw = response.read()
    except URLError as error:
        raise RuntimeError(f"Could not fetch OpenAPI from {target}: {error.reason}") from error
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"OpenAPI endpoint did not return JSON: {target}") from error
    return canonicalize_openapi(document)


def _walk_strings(value: Any, location: str = "$") -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(location, value)]
    if isinstance(value, Mapping):
        return [item for key, child in value.items() for item in _walk_strings(child, f"{location}.{key}")]
    if isinstance(value, list):
        return [item for index, child in enumerate(value) for item in _walk_strings(child, f"{location}[{index}]")]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("capture", "compare"):
        command = subparsers.add_parser(name)
        command.add_argument("--url", required=True, help="Running Inkdesk server base URL")
        command.add_argument("--snapshot", type=Path, required=True, help="Canonical OpenAPI snapshot path")
        command.add_argument("--timeout-seconds", type=float, default=30.0)
    arguments = parser.parse_args(argv)
    document = fetch_openapi(arguments.url, timeout_seconds=arguments.timeout_seconds)
    if arguments.command == "capture":
        write_openapi_snapshot(document, arguments.snapshot)
        return 0
    try:
        compare_openapi(document, arguments.snapshot)
    except OpenAPIContractMismatch as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
