from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any
from uuid import uuid4

from inkdesk_server.harness.models import RunEvent, RunRecord, RunStatus, utc_now
from inkdesk_server.harness.redaction import redact_value


class RunNotFoundError(FileNotFoundError):
    pass


class RunStore:
    def __init__(self, vault_root: Path):
        self.root = Path(vault_root).resolve() / ".inkdesk" / "runs"
        self.root.mkdir(parents=True, exist_ok=True)
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._subscribers: defaultdict[str, set[asyncio.Queue[RunEvent]]] = defaultdict(set)
        self._recover_interrupted()

    def create_run(
        self,
        capability_id: str,
        executor: str,
        inputs: dict[str, Any],
        source_head: str,
        source_dirty: bool = False,
    ) -> RunRecord:
        run_id = "run-" + uuid4().hex[:16]
        record = RunRecord(
            id=run_id,
            capabilityId=capability_id,
            executor=executor,
            inputs=inputs,
            sourceHead=source_head,
            sourceDirty=source_dirty,
        )
        self._run_dir(run_id).mkdir(parents=True, exist_ok=False)
        self._write_run(record)
        return record

    def get_run(self, run_id: str) -> RunRecord:
        path = self._run_file(run_id)
        try:
            return RunRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RunNotFoundError(run_id) from exc

    def update_run(self, run_id: str, **changes: Any) -> RunRecord:
        current = self.get_run(run_id)
        updated = current.model_copy(update={**changes, "updatedAt": utc_now()})
        self._write_run(updated)
        return updated

    async def append_event(self, run_id: str, event_type: str, data: dict[str, Any]) -> RunEvent:
        async with self._locks[run_id]:
            existing = self.read_events(run_id)
            event = RunEvent(
                sequence=(existing[-1].sequence + 1) if existing else 1,
                type=event_type,
                data=redact_value(data),
            )
            path = self._run_dir(run_id) / "events.jsonl"
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(event.model_dump_json() + "\n")
            for queue in tuple(self._subscribers[run_id]):
                if queue.full():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                queue.put_nowait(event)
            return event

    def read_events(self, run_id: str, after: int = 0) -> list[RunEvent]:
        path = self._run_dir(run_id) / "events.jsonl"
        if not path.is_file():
            if not self._run_dir(run_id).is_dir():
                raise RunNotFoundError(run_id)
            return []
        events: list[RunEvent] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = RunEvent.model_validate_json(line)
            if event.sequence > after:
                events.append(event)
        return events

    def subscribe(self, run_id: str) -> asyncio.Queue[RunEvent]:
        self.get_run(run_id)
        queue: asyncio.Queue[RunEvent] = asyncio.Queue(maxsize=256)
        self._subscribers[run_id].add(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue[RunEvent]) -> None:
        self._subscribers[run_id].discard(queue)

    def write_json(self, run_id: str, name: str, value: Any) -> Path:
        path = self._safe_artifact_path(run_id, name)
        payload = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
        self._atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return path

    def write_text(self, run_id: str, name: str, value: str) -> Path:
        path = self._safe_artifact_path(run_id, name)
        self._atomic_write(path, value)
        return path

    def read_json(self, run_id: str, name: str) -> Any | None:
        path = self._safe_artifact_path(run_id, name)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def read_text(self, run_id: str, name: str) -> str | None:
        path = self._safe_artifact_path(run_id, name)
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    def _recover_interrupted(self) -> None:
        for path in self.root.glob("run-*/run.json"):
            try:
                record = RunRecord.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if record.status in {RunStatus.QUEUED, RunStatus.RUNNING}:
                self._write_run(
                    record.model_copy(update={"status": RunStatus.INTERRUPTED, "updatedAt": utc_now()})
                )

    def _run_dir(self, run_id: str) -> Path:
        if not run_id.startswith("run-") or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in run_id):
            raise ValueError("Invalid run id")
        return self.root / run_id

    def _run_file(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "run.json"

    def _write_run(self, record: RunRecord) -> None:
        self._atomic_write(self._run_file(record.id), record.model_dump_json(indent=2) + "\n")

    def _safe_artifact_path(self, run_id: str, name: str) -> Path:
        if Path(name).name != name or name in {"", ".", ".."}:
            raise ValueError("Artifact name must be a file name")
        return self._run_dir(run_id) / name

    @staticmethod
    def _atomic_write(path: Path, value: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        try:
            temporary.write_text(value, encoding="utf-8", newline="\n")
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
