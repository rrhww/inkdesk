from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4
from hashlib import sha256

from inkdesk_server.schemas import TaskCreateRequest
from inkdesk_server.security import ApiError, ResourceNotFoundError


ALLOWED_TRANSITIONS = {
    "backlog": {"ready", "blocked"},
    "ready": {"backlog", "doing", "blocked"},
    "doing": {"review", "blocked"},
    "review": {"doing", "blocked", "done"},
    "blocked": {"backlog", "ready", "doing"},
    "done": set(),
}
EXECUTION_GATE_STATUSES = {"ready", "doing"}
VALID_CONTEXT_STATUSES = {"ready", "gap"}
SEARCH_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_\-\u4e00-\u9fff]+")
STOP_WORDS = {"the", "and", "for", "with", "from", "that", "this", "add", "change", "implement", "undocumented", "subsystem", "behavior", "confirm", "upgrade", "repository", "knowledge", "source", "which", "no"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


class TaskEventBus:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = threading.RLock()

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        with self._lock:
            self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._subscribers.discard(queue)

    def publish(self, event: dict[str, Any]) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        with self._lock:
            subscribers = tuple(self._subscribers)
        for subscriber in subscribers:
            loop.call_soon_threadsafe(self._put, subscriber, event)

    @staticmethod
    def _put(queue: asyncio.Queue[dict[str, Any]], event: dict[str, Any]) -> None:
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        queue.put_nowait(event)


class TaskRuntime:
    def __init__(self, graph_provider: Callable[[], Any], on_change: Callable[[dict[str, Any]], None] | None = None):
        configured_path = os.environ.get("INKDESK_DATABASE_PATH", "").strip()
        self.database_path = (
            Path(configured_path).expanduser().resolve()
            if configured_path
            else Path(__file__).resolve().parents[1] / ".data" / "inkdesk.sqlite"
        )
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.graph_provider = graph_provider
        self.on_change = on_change
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS development_tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    origin_type TEXT NOT NULL,
                    origin_ref TEXT,
                    priority TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    status TEXT NOT NULL,
                    context_status TEXT NOT NULL,
                    knowledge_topic_ids TEXT NOT NULL,
                    context_pack TEXT,
                    knowledge_gap TEXT,
                    version INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS development_tasks_status_idx "
                "ON development_tasks(status)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS development_tasks_origin_idx "
                "ON development_tasks(origin_type)"
            )
            connection.execute(
                "UPDATE development_tasks SET context_status='failed', knowledge_gap=? "
                "WHERE context_status IN ('searching', 'pending')",
                (json.dumps({"reason": "service_restart", "recordedAt": _now()}),),
            )

    def _publish(self, task_id: str) -> None:
        if self.on_change is None:
            return
        try:
            task = self.get(task_id)
            self.on_change({"type": "tasks.updated", "taskId": task_id, "version": task["version"]})
        except ResourceNotFoundError:
            return

    def create(self, request: TaskCreateRequest) -> dict[str, Any]:
        task_id = str(uuid4())
        timestamp = _now()
        topic_ids = list(dict.fromkeys(request.knowledgeTopicIds))
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO development_tasks (
                    id, title, goal, origin_type, origin_ref, priority, risk,
                    status, context_status, knowledge_topic_ids, context_pack,
                    knowledge_gap, version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'backlog', 'pending', ?, NULL, NULL, 1, ?, ?)
                """,
                (
                    task_id,
                    request.title.strip(),
                    request.goal.strip(),
                    request.originType,
                    request.originRef.strip() if request.originRef else None,
                    request.priority.strip().lower(),
                    request.risk.strip().lower(),
                    json.dumps(topic_ids, ensure_ascii=False),
                    timestamp,
                    timestamp,
                ),
            )
        result = self.get(task_id)
        self._publish(task_id)
        return result

    def list(self, status: str | None = None, origin_type: str | None = None, context_status: str | None = None) -> list[dict[str, Any]]:
        conditions: list[str] = []
        parameters: list[str] = []
        if status:
            conditions.append("status = ?")
            parameters.append(status)
        if origin_type:
            conditions.append("origin_type = ?")
            parameters.append(origin_type)
        if context_status:
            conditions.append("context_status = ?")
            parameters.append(context_status)
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM development_tasks{where} ORDER BY created_at DESC, id DESC",
                parameters,
            ).fetchall()
        return [self._row_to_task(row, detail=False) for row in rows]

    def get(self, task_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM development_tasks WHERE id = ?", (task_id,)
            ).fetchone()
        if row is None:
            raise ResourceNotFoundError("Development task was not found.")
        return self._row_to_task(row, detail=True)

    def assemble_context(self, task_id: str, *, force: bool = False) -> dict[str, Any]:
        with self._lock:
            task = self.get(task_id)
            if task["contextStatus"] in VALID_CONTEXT_STATUSES and not force:
                return task
            self._set_context_result(
                task_id,
                context_status="searching",
                context_pack=None,
                knowledge_gap=None,
            )
            self._publish(task_id)
            try:
                result = self._build_context(task)
            except Exception as error:
                self._set_context_result(
                    task_id,
                    context_status="failed",
                    context_pack=None,
                    knowledge_gap={
                        "reason": "context_assembly_failed",
                        "message": str(error)[:500],
                        "recordedAt": _now(),
                    },
                )
                self._publish(task_id)
                return self.get(task_id)

            self._set_context_result(
                task_id,
                context_status=result["contextStatus"],
                context_pack=result["contextPack"],
                knowledge_gap=result["knowledgeGap"],
                knowledge_topic_ids=result["knowledgeTopicIds"],
            )
            result = self.get(task_id)
            self._publish(task_id)
            return result

    def transition(self, task_id: str, target_status: str, if_version: int) -> dict[str, Any]:
        with self._lock:
            task = self.get(task_id)
            if task["version"] != if_version:
                raise ApiError(
                    409,
                    "VERSION_CONFLICT",
                    f"Task version is {task['version']}; received ifVersion {if_version}.",
                )
            if target_status not in ALLOWED_TRANSITIONS[task["status"]]:
                raise ApiError(
                    409,
                    "INVALID_TASK_TRANSITION",
                    f"Cannot transition task from {task['status']} to {target_status}.",
                )
            if (
                target_status in EXECUTION_GATE_STATUSES
                and task["contextStatus"] not in VALID_CONTEXT_STATUSES
            ):
                raise ApiError(
                    409,
                    "TASK_CONTEXT_NOT_READY",
                    "Task context must be assembled as ready or gap before execution.",
                )

            timestamp = _now()
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    UPDATE development_tasks
                    SET status = ?, version = version + 1, updated_at = ?
                    WHERE id = ? AND version = ?
                    """,
                    (target_status, timestamp, task_id, if_version),
                )
                if cursor.rowcount != 1:
                    raise ApiError(409, "VERSION_CONFLICT", "Task was updated concurrently.")
            result = self.get(task_id)
            self._publish(task_id)
            return result

    def _set_context_result(
        self,
        task_id: str,
        *,
        context_status: str,
        context_pack: dict[str, Any] | None,
        knowledge_gap: dict[str, Any] | None,
        knowledge_topic_ids: list[str] | None = None,
    ) -> None:
        timestamp = _now()
        assignments = [
            "context_status = ?",
            "context_pack = ?",
            "knowledge_gap = ?",
            "version = version + 1",
            "updated_at = ?",
        ]
        parameters: list[Any] = [
            context_status,
            json.dumps(context_pack, ensure_ascii=False) if context_pack is not None else None,
            json.dumps(knowledge_gap, ensure_ascii=False) if knowledge_gap is not None else None,
            timestamp,
        ]
        if knowledge_topic_ids is not None:
            assignments.append("knowledge_topic_ids = ?")
            parameters.append(json.dumps(knowledge_topic_ids, ensure_ascii=False))
        parameters.append(task_id)
        with self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE development_tasks SET {', '.join(assignments)} WHERE id = ?",
                parameters,
            )
            if cursor.rowcount != 1:
                raise ResourceNotFoundError("Development task was not found.")

    def _build_context(self, task: dict[str, Any]) -> dict[str, Any]:
        snapshot = self.graph_provider()
        requested_ids = set(task["knowledgeTopicIds"])
        query = f"{task['title']} {task['goal']} {task.get('originRef') or ''}".strip()
        tokens = {
            token.casefold()
            for token in SEARCH_TOKEN_PATTERN.findall(query)
            if len(token) >= 3 and token.casefold() not in STOP_WORDS
        }
        matches: list[dict[str, str]] = []
        for node in snapshot.nodes:
            if node.kind == "missing":
                continue
            normalized_path = node.path.replace("\\", "/").casefold()
            if node.source == "vault":
                if not normalized_path.startswith("wiki/"):
                    continue
            elif not (
                normalized_path.startswith("docs/")
                or ("/" not in normalized_path and normalized_path.endswith(".md") and normalized_path not in {"agents.md", "claude.md"})
            ):
                continue
            haystack = f"{node.label} {node.path} {node.summary}".casefold()
            topic_id = "topic-" + sha256(node.id.encode("utf-8")).hexdigest()[:16]
            explicitly_selected = node.id in requested_ids or topic_id in requested_ids
            keyword_match = any(token in haystack for token in tokens)
            if not explicitly_selected and not keyword_match:
                continue
            matches.append(
                {
                    "id": node.id,
                    "title": node.label,
                    "kind": node.kind,
                    "path": node.path,
                    "source": node.source,
                    "status": node.status,
                    "summary": node.summary,
                    "_explicit": explicitly_selected,
                }
            )

        matches.sort(
            key=lambda item: (
                not item["_explicit"],
                item["source"],
                item["path"].casefold(),
            )
        )
        for item in matches:
            item.pop("_explicit", None)
        assembled_at = _now()
        if matches:
            topic_ids = ["topic-" + sha256(item["id"].encode("utf-8")).hexdigest()[:16] for item in matches]
            for item, topic_id in zip(matches, topic_ids):
                item["topicId"] = topic_id
                item["documentId"] = item["id"]
            return {
                "contextStatus": "ready",
                "contextPack": {
                    "query": query,
                    "topics": matches,
                    "sourcePaths": sorted({item["path"] for item in matches if item["kind"] == "source"}),
                    "codePaths": [],
                    "assembledAt": assembled_at,
                    "graphVersion": snapshot.version,
                },
                "knowledgeGap": None,
                "knowledgeTopicIds": topic_ids,
            }

        return {
            "contextStatus": "gap",
            "contextPack": None,
            "knowledgeGap": {
                "reason": "no_relevant_knowledge",
                "query": query,
                "requestedTopicIds": sorted(requested_ids),
                "recordedAt": assembled_at,
                "followUpTaskId": None,
            },
            # Keep explicit references even when they could not be resolved so the
            # resulting gap remains traceable and can be repaired later.
            "knowledgeTopicIds": sorted(requested_ids),
        }

    @staticmethod
    def _row_to_task(row: sqlite3.Row, *, detail: bool) -> dict[str, Any]:
        task = {
            "id": row["id"],
            "title": row["title"],
            "goal": row["goal"],
            "status": row["status"],
            "originType": row["origin_type"],
            "originRef": row["origin_ref"],
            "priority": row["priority"],
            "risk": row["risk"],
            "contextStatus": row["context_status"],
            "knowledgeTopicIds": json.loads(row["knowledge_topic_ids"]),
            "version": row["version"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
        if detail:
            task["contextPack"] = json.loads(row["context_pack"]) if row["context_pack"] else None
            task["knowledgeGap"] = (
                json.loads(row["knowledge_gap"]) if row["knowledge_gap"] else None
            )
        return task
