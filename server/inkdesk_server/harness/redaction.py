from __future__ import annotations

import re
from pathlib import Path
from typing import Any


REDACTED = "[REDACTED]"
_KNOWN_TOKEN = re.compile(
    r"(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9]{12,}|github_pat_[A-Za-z0-9_]{12,})"
)
_PRIVATE_KEY = re.compile(
    r"-----BEGIN(?: [A-Z0-9]+)* PRIVATE KEY-----.*?-----END(?: [A-Z0-9]+)* PRIVATE KEY-----",
    re.DOTALL,
)
_ASSIGNMENT = re.compile(
    r"(?im)"
    r"(?P<prefix>(?P<key_quote>[\"']?)(?P<key>[A-Za-z_][A-Za-z0-9_-]*)(?P=key_quote)\s*[:=]\s*)"
    r"(?P<value_quote>[\"']?)(?P<value>[^\r\n]*?)(?P=value_quote)(?=$|[\r\n,;}])"
)
_URI_USERINFO = re.compile(
    r"(?P<scheme>\b[A-Za-z][A-Za-z0-9+.-]*://)(?P<userinfo>[^/\s:@]+:[^/\s@]+)@"
)
_SENSITIVE_KEYS = {
    "authorization",
    "password",
    "passwd",
    "pwd",
    "database_url",
    "db_url",
}
_SENSITIVE_SUFFIXES = (
    "token",
    "secret",
    "api_key",
    "access_key",
    "private_key",
    "client_secret",
)


def redact_text(value: str) -> str:
    redacted = _PRIVATE_KEY.sub(REDACTED, value)
    redacted = _ASSIGNMENT.sub(_redact_assignment, redacted)
    redacted = _URI_USERINFO.sub(r"\g<scheme>[REDACTED]@", redacted)
    redacted = _KNOWN_TOKEN.sub(REDACTED, redacted)
    home = str(Path.home())
    if home:
        redacted = redacted.replace(home, "[USER_HOME]")
        redacted = redacted.replace(home.replace("\\", "/"), "[USER_HOME]")
    return redacted


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): REDACTED if _is_sensitive_key(_normalize_key(str(key))) else redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def _redact_assignment(match: re.Match[str]) -> str:
    key = _normalize_key(match.group("key"))
    if not _is_sensitive_key(key):
        return match.group(0)
    quote = match.group("value_quote")
    return f"{match.group('prefix')}{quote}{REDACTED}{quote}"


def _is_sensitive_key(key: str) -> bool:
    if key in _SENSITIVE_KEYS:
        return True
    return any(key == suffix or key.endswith(f"_{suffix}") for suffix in _SENSITIVE_SUFFIXES)


def _normalize_key(key: str) -> str:
    snake_case = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    return snake_case.casefold().replace("-", "_")
