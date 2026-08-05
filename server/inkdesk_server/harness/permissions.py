from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from inkdesk_server.harness.models import PermissionRecord, PermissionStatus, utc_now
from inkdesk_server.harness.redaction import redact_value


class PermissionError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class PermissionBroker:
    def __init__(self, *, timeout_seconds: float = 90.0):
        self.timeout_seconds = timeout_seconds
        self._records: dict[str, PermissionRecord] = {}
        self._waiters: dict[str, asyncio.Future[bool]] = {}
        self._lock = asyncio.Lock()

    async def request(
        self,
        *,
        run_id: str,
        stage_id: str,
        session_id: str,
        tool_use_id: str,
        tool: str,
        tool_input: dict[str, Any],
    ) -> PermissionRecord:
        now = datetime.now(UTC)
        record = PermissionRecord(
            id="perm-" + uuid4().hex[:16],
            runId=run_id,
            stageId=stage_id,
            sessionId=session_id,
            toolUseId=tool_use_id,
            tool=tool,
            inputPreview=redact_value(tool_input),
            expiresAt=(now + timedelta(seconds=self.timeout_seconds)).isoformat(),
        )
        async with self._lock:
            self._records[record.id] = record
            self._waiters[record.id] = asyncio.get_running_loop().create_future()
        return record

    async def wait(self, permission_id: str) -> bool:
        async with self._lock:
            record = self._require(permission_id)
            waiter = self._waiters[permission_id]
        try:
            return await asyncio.wait_for(asyncio.shield(waiter), timeout=self.timeout_seconds)
        except TimeoutError:
            async with self._lock:
                current = self._require(permission_id)
                if current.status == PermissionStatus.PENDING:
                    self._records[permission_id] = current.model_copy(
                        update={"status": PermissionStatus.EXPIRED, "resolvedAt": utc_now(), "reason": "Approval timed out."}
                    )
                    if not waiter.done():
                        waiter.set_result(False)
            return False

    async def decide(self, permission_id: str, *, allow: bool, reason: str | None = None) -> PermissionRecord:
        async with self._lock:
            current = self._require(permission_id)
            if current.status != PermissionStatus.PENDING:
                raise PermissionError("PERMISSION_NOT_PENDING", "Permission request is no longer pending.")
            updated = current.model_copy(
                update={
                    "status": PermissionStatus.ALLOWED if allow else PermissionStatus.DENIED,
                    "resolvedAt": utc_now(),
                    "reason": reason,
                }
            )
            self._records[permission_id] = updated
            waiter = self._waiters[permission_id]
            if not waiter.done():
                waiter.set_result(allow)
            return updated

    def list(self, run_id: str, status: PermissionStatus | None = None) -> list[PermissionRecord]:
        values = [record for record in self._records.values() if record.runId == run_id]
        if status is not None:
            values = [record for record in values if record.status == status]
        return sorted(values, key=lambda item: item.createdAt)

    async def cancel_run(self, run_id: str) -> None:
        async with self._lock:
            for permission_id, current in tuple(self._records.items()):
                if current.runId != run_id or current.status != PermissionStatus.PENDING:
                    continue
                self._records[permission_id] = current.model_copy(
                    update={"status": PermissionStatus.CANCELLED, "resolvedAt": utc_now(), "reason": "Run cancelled."}
                )
                waiter = self._waiters[permission_id]
                if not waiter.done():
                    waiter.set_result(False)

    def _require(self, permission_id: str) -> PermissionRecord:
        try:
            return self._records[permission_id]
        except KeyError as exc:
            raise PermissionError("PERMISSION_NOT_FOUND", "Permission request was not found.") from exc
