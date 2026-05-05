from __future__ import annotations

from datetime import UTC, datetime


def ensure_utc_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.fromtimestamp(0, tz=UTC)
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
