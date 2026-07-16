"""Explicit, closed handler registry for durable job kinds."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from .repository import ClaimedJob


JobHandler = Callable[[Session, ClaimedJob], dict[str, Any] | None]


class JobHandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, JobHandler] = {}

    def register(self, kind: str, handler: JobHandler) -> None:
        if not kind or kind in self._handlers:
            raise ValueError("job kind must be non-empty and registered once")
        self._handlers[kind] = handler

    def get(self, kind: str) -> JobHandler | None:
        return self._handlers.get(kind)
