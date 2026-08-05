from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from inkdesk_server.graph_index import GraphIndexRuntime, GraphNode, GraphSnapshot
from inkdesk_server.security import ApiError, ResourceNotFoundError


SIGNAL_TYPES = {"stale", "unsupported", "conflicting", "open_question", "missing_link"}
SIGNAL_STATUSES = {"open", "acknowledged", "resolved", "dismissed"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _stable(prefix: str, *values: object) -> str:
    payload = "\x1f".join(str(value).strip().casefold() for value in values)
    return f"{prefix}-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


class KnowledgeHealthRuntime:
    """Small, deterministic Claim/Evidence health projection over the file graph."""

    def __init__(self, graph_runtime: GraphIndexRuntime):
        configured = os.environ.get("INKDESK_DATABASE_PATH", "").strip()
        self.database_path = (
            Path(configured).expanduser().resolve()
            if configured
            else Path(__file__).resolve().parents[1] / ".data" / "inkdesk.sqlite"
        )
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.graph_runtime = graph_runtime
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
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS knowledge_claims (
                    id TEXT PRIMARY KEY,
                    topic_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source_path TEXT,
                    locator_json TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS knowledge_claims_topic_idx ON knowledge_claims(topic_id);
                CREATE TABLE IF NOT EXISTS knowledge_evidence (
                    id TEXT PRIMARY KEY,
                    claim_id TEXT NOT NULL REFERENCES knowledge_claims(id) ON DELETE CASCADE,
                    source_id TEXT,
                    source_path TEXT NOT NULL,
                    locator_json TEXT NOT NULL,
                    stance TEXT NOT NULL,
                    excerpt TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS knowledge_evidence_claim_idx ON knowledge_evidence(claim_id);
                CREATE TABLE IF NOT EXISTS knowledge_signals (
                    id TEXT PRIMARY KEY,
                    topic_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    refs_json TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    resolution_note TEXT,
                    version INTEGER NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    resolved_at TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS knowledge_signals_fingerprint_idx
                    ON knowledge_signals(topic_id, type, fingerprint);
                CREATE INDEX IF NOT EXISTS knowledge_signals_status_idx ON knowledge_signals(status);
                CREATE TABLE IF NOT EXISTS knowledge_reviews (
                    id TEXT PRIMARY KEY,
                    signal_id TEXT,
                    topic_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    proposal_json TEXT,
                    note TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    decided_at TEXT
                );
                """
            )
            if version < 2:
                connection.execute("PRAGMA user_version = 2")

    def reconcile(self, snapshot: GraphSnapshot | None = None) -> None:
        snapshot = snapshot or self.graph_runtime.current()
        if snapshot.version == "empty":
            snapshot = self.graph_runtime.refresh("knowledge-health")
        nodes = {node.id: node for node in snapshot.nodes}
        topics = [node for node in snapshot.nodes if self._is_topic(node)]
        with self._lock, self._connect() as connection:
            seen_claims: set[str] = set()
            seen_signals: set[tuple[str, str, str]] = set()
            for topic in topics:
                document = self._document(topic)
                metadata, body = self._split_frontmatter(document)
                claims = self._claims(topic, metadata, body, nodes)
                for claim in claims:
                    seen_claims.add(claim["id"])
                    connection.execute(
                        """INSERT INTO knowledge_claims
                        (id, topic_id, text, status, source_path, locator_json, content_hash, observed_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET text=excluded.text,status=excluded.status,
                          source_path=excluded.source_path,locator_json=excluded.locator_json,
                          content_hash=excluded.content_hash,observed_at=excluded.observed_at,updated_at=excluded.updated_at""",
                        (claim["id"], self._topic_id(topic), claim["text"], claim["status"], topic.path,
                         json.dumps(claim["locator"], ensure_ascii=False), claim["contentHash"], _now(), _now()),
                    )
                    connection.execute("DELETE FROM knowledge_evidence WHERE claim_id = ?", (claim["id"],))
                    for evidence in claim["evidence"]:
                        connection.execute(
                            """INSERT OR REPLACE INTO knowledge_evidence
                            (id, claim_id, source_id, source_path, locator_json, stance, excerpt, content_hash, observed_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (evidence["id"], claim["id"], evidence.get("sourceId"), evidence["sourcePath"],
                             json.dumps(evidence["locator"], ensure_ascii=False), evidence["stance"],
                             evidence.get("excerpt", ""), evidence["contentHash"], _now()),
                        )
                    for signal in self._signals(topic, claim, metadata, body):
                        fingerprint = signal["fingerprint"]
                        seen_signals.add((self._topic_id(topic), signal["type"], fingerprint))
                        existing = connection.execute(
                            "SELECT id,status,version FROM knowledge_signals WHERE topic_id=? AND type=? AND fingerprint=?",
                            (self._topic_id(topic), signal["type"], fingerprint),
                        ).fetchone()
                        if existing:
                            connection.execute(
                                "UPDATE knowledge_signals SET last_seen_at=?,title=?,detail=?,refs_json=? WHERE id=?",
                                (_now(), signal["title"], signal["detail"], json.dumps(signal["refs"], ensure_ascii=False), existing["id"]),
                            )
                        else:
                            connection.execute(
                                """INSERT INTO knowledge_signals
                                (id,topic_id,type,severity,title,detail,refs_json,fingerprint,status,resolution_note,version,first_seen_at,last_seen_at,resolved_at)
                                VALUES (?,?,?,?,?,?,?,?, 'open', NULL, 1,?,?,NULL)""",
                                (signal["id"], self._topic_id(topic), signal["type"], signal["severity"], signal["title"],
                                 signal["detail"], json.dumps(signal["refs"], ensure_ascii=False), fingerprint, _now(), _now()),
                            )
            if seen_claims:
                placeholders = ",".join("?" for _ in seen_claims)
                connection.execute(f"DELETE FROM knowledge_claims WHERE id NOT IN ({placeholders})", tuple(seen_claims))

    @staticmethod
    def _is_topic(node: GraphNode) -> bool:
        path = node.path.replace("\\", "/").casefold()
        if node.kind in {"source", "missing"}:
            return False
        if node.source == "vault":
            return path.startswith("wiki/")
        return path.startswith("docs/") or (
            "/" not in path and path.endswith(".md") and path not in {"agents.md", "claude.md"}
        )

    def _topic_id(self, node: GraphNode) -> str:
        return "topic-" + hashlib.sha256(node.id.encode("utf-8")).hexdigest()[:16]

    def _document(self, node: GraphNode) -> str:
        try:
            return self.graph_runtime.scanner.read_document(node)
        except (FileNotFoundError, OSError, UnicodeDecodeError):
            return ""

    @staticmethod
    def _split_frontmatter(content: str) -> tuple[dict[str, Any], str]:
        normalized = content.replace("\r\n", "\n")
        if not normalized.startswith("---\n"):
            return {}, normalized
        end = normalized.find("\n---\n", 4)
        if end < 0:
            return {}, normalized
        try:
            metadata = yaml.safe_load(normalized[4:end]) or {}
        except yaml.YAMLError:
            metadata = {}
        return (metadata if isinstance(metadata, dict) else {}, normalized[end + 5 :])

    def _claims(self, topic: GraphNode, metadata: dict[str, Any], body: str, nodes: dict[str, GraphNode]) -> list[dict[str, Any]]:
        declared = metadata.get("claims")
        values = declared if isinstance(declared, list) else []
        claims: list[dict[str, Any]] = []
        linked_sources = [node for node in nodes.values() if node.kind == "source" and (node.path in body or node.label in body)]
        for index, item in enumerate(values):
            if isinstance(item, str):
                text, extra = item, {}
            elif isinstance(item, dict):
                text, extra = str(item.get("text") or item.get("statement") or ""), item
            else:
                continue
            text = text.strip()
            if not text:
                continue
            claim_id = _stable("claim", self._topic_id(topic), text)
            evidence: list[dict[str, Any]] = []
            raw_evidence = extra.get("evidence", []) if isinstance(extra, dict) else []
            if isinstance(raw_evidence, list):
                for evidence_item in raw_evidence:
                    if isinstance(evidence_item, str):
                        path, stance, excerpt = evidence_item, "supports", ""
                    elif isinstance(evidence_item, dict):
                        path = str(evidence_item.get("path") or evidence_item.get("sourcePath") or "")
                        stance = str(evidence_item.get("stance") or "supports")
                        excerpt = str(evidence_item.get("excerpt") or "")[:500]
                    else:
                        continue
                    if not path:
                        continue
                    evidence.append({"id": _stable("evidence", claim_id, path, stance, excerpt), "sourcePath": path, "sourceId": None, "locator": {"path": path}, "stance": stance, "excerpt": excerpt, "contentHash": hashlib.sha256(path.encode()).hexdigest()})
            for source in linked_sources:
                evidence.append({"id": _stable("evidence", claim_id, source.id), "sourcePath": source.path, "sourceId": source.id, "locator": {"path": source.path}, "stance": "supports", "excerpt": source.summary[:500], "contentHash": hashlib.sha256(source.path.encode()).hexdigest()})
            claims.append({"id": claim_id, "text": text, "status": str(extra.get("status") or "asserted") if isinstance(extra, dict) else "asserted", "locator": {"index": index}, "contentHash": hashlib.sha256(text.encode()).hexdigest(), "evidence": evidence})
        return claims

    def _signals(self, topic: GraphNode, claim: dict[str, Any], metadata: dict[str, Any], body: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        evidence = claim["evidence"]
        if not evidence:
            result.append(self._signal(topic, "unsupported", "warning", "Evidence is incomplete", f"Claim has no explicit supporting evidence: {claim['text']}", [claim["id"]]))
        if claim["status"] in {"deprecated", "superseded"} or metadata.get("status") == "stale" or (isinstance(metadata.get("healthSignals"), list) and "stale" in metadata["healthSignals"]):
            result.append(self._signal(topic, "stale", "warning", "Knowledge may be stale", "Claim or source is marked for freshness review.", [claim["id"]]))
        if isinstance(metadata.get("healthSignals"), list) and any(str(item) in {"conflicting", "conflict"} for item in metadata["healthSignals"]):
            result.append(self._signal(topic, "conflicting", "critical", "Conflicting knowledge", "The source declares an unresolved conflict.", [claim["id"]]))
        if "?" in body and re.search(r"^#{2,3}\s+(Open Questions|未解问题|开放问题)", body, re.MULTILINE | re.IGNORECASE):
            result.append(self._signal(topic, "open_question", "info", "Open questions remain", "This topic contains an unresolved question.", [claim["id"]]))
        return result

    def _signal(self, topic: GraphNode, signal_type: str, severity: str, title: str, detail: str, refs: list[str]) -> dict[str, Any]:
        fingerprint = _stable("fingerprint", self._topic_id(topic), signal_type, detail, *refs)
        return {"id": _stable("signal", self._topic_id(topic), signal_type, fingerprint), "topicId": self._topic_id(topic), "type": signal_type, "severity": severity, "title": title, "detail": detail, "refs": {"claimIds": refs}, "fingerprint": fingerprint}

    def _ensure(self) -> None:
        self.reconcile()

    @staticmethod
    def _json(value: str | None, default: Any) -> Any:
        if not value:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default

    def list_signals(self, *, status: str | None = None, signal_type: str | None = None, topic_id: str | None = None) -> list[dict[str, Any]]:
        self._ensure()
        conditions, params = [], []
        if status:
            conditions.append("status=?"); params.append(status)
        if signal_type:
            conditions.append("type=?"); params.append(signal_type)
        if topic_id:
            conditions.append("topic_id=?"); params.append(topic_id)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        with self._connect() as connection:
            rows = connection.execute(f"SELECT * FROM knowledge_signals{where} ORDER BY last_seen_at DESC", params).fetchall()
        return [self._signal_row(row) for row in rows]

    def get_signal(self, signal_id: str) -> dict[str, Any]:
        self._ensure()
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM knowledge_signals WHERE id=?", (signal_id,)).fetchone()
        if not row:
            raise ResourceNotFoundError("Knowledge signal was not found.")
        signal = self._signal_row(row)
        signal["claims"] = self.claims(signal["topicId"], signal["refs"].get("claimIds", []))
        return signal

    def claims(self, topic_id: str, claim_ids: list[str] | None = None) -> list[dict[str, Any]]:
        self._ensure()
        params: list[Any] = [topic_id]
        where = "topic_id=?"
        if claim_ids:
            placeholders = ",".join("?" for _ in claim_ids); where += f" AND id IN ({placeholders})"; params.extend(claim_ids)
        with self._connect() as connection:
            rows = connection.execute(f"SELECT * FROM knowledge_claims WHERE {where} ORDER BY id", params).fetchall()
        return [self._claim_row(row) for row in rows]

    def get_claim(self, claim_id: str) -> dict[str, Any]:
        self._ensure()
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM knowledge_claims WHERE id=?", (claim_id,)).fetchone()
        if not row:
            raise ResourceNotFoundError("Knowledge claim was not found.")
        return self._claim_row(row)

    def evidence(self, claim_id: str) -> list[dict[str, Any]]:
        self._ensure()
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM knowledge_evidence WHERE claim_id=? ORDER BY id", (claim_id,)).fetchall()
        return [self._evidence_row(row) for row in rows]

    def summary(self) -> dict[str, Any]:
        signals = self.list_signals()
        active = [signal for signal in signals if signal["status"] in {"open", "acknowledged"}]
        return {"total": len(signals), "active": len(active), "byType": {kind: sum(signal["type"] == kind and signal["status"] in {"open", "acknowledged"} for signal in signals) for kind in sorted(SIGNAL_TYPES)}}

    def action(self, signal_id: str, action: str, if_version: int, note: str | None = None) -> dict[str, Any]:
        if action not in {"acknowledge", "resolve", "dismiss", "reopen"}:
            raise ApiError(400, "INVALID_SIGNAL_ACTION", "Unsupported knowledge signal action.")
        if action in {"resolve", "dismiss"} and not (note or "").strip():
            raise ApiError(400, "SIGNAL_NOTE_REQUIRED", "A note is required to resolve or dismiss a signal.")
        self._ensure()
        target = {"acknowledge": "acknowledged", "resolve": "resolved", "dismiss": "dismissed", "reopen": "open"}[action]
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT * FROM knowledge_signals WHERE id=?", (signal_id,)).fetchone()
            if not row:
                raise ResourceNotFoundError("Knowledge signal was not found.")
            if row["version"] != if_version:
                raise ApiError(409, "VERSION_CONFLICT", "Knowledge signal version is stale.")
            new_version = row["version"] + 1
            connection.execute("UPDATE knowledge_signals SET status=?,resolution_note=?,version=?,resolved_at=? WHERE id=? AND version=?", (target, note, new_version, _now() if target in {"resolved", "dismissed"} else None, signal_id, if_version))
        return self.get_signal(signal_id)

    def list_reviews(self, status: str | None = None) -> list[dict[str, Any]]:
        conditions = " WHERE status=?" if status else ""
        params = (status,) if status else ()
        with self._connect() as connection:
            rows = connection.execute(f"SELECT * FROM knowledge_reviews{conditions} ORDER BY created_at DESC", params).fetchall()
        return [self._review_row(row) for row in rows]

    def create_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        review_id = str(payload.get("id") or _stable("review", payload.get("signalId"), payload.get("topicId"), payload.get("action"), _now()))
        created_at = _now()
        with self._connect() as connection:
            connection.execute("INSERT INTO knowledge_reviews (id,signal_id,topic_id,action,proposal_json,note,status,created_at,decided_at) VALUES (?,?,?,?,?,?, 'pending',?,NULL)", (review_id, payload.get("signalId"), payload["topicId"], payload["action"], json.dumps(payload.get("proposal") or {}, ensure_ascii=False), payload.get("note"), created_at))
        return self._review_by_id(review_id)

    def decide_review(self, review_id: str, decision: str, note: str | None = None) -> dict[str, Any]:
        if decision not in {"accepted", "rejected", "cancelled"}:
            raise ApiError(400, "INVALID_REVIEW_DECISION", "Unsupported review decision.")
        with self._connect() as connection:
            cursor = connection.execute("UPDATE knowledge_reviews SET status=?,note=COALESCE(?,note),decided_at=? WHERE id=? AND status='pending'", (decision, note, _now(), review_id))
            if cursor.rowcount != 1:
                raise ResourceNotFoundError("Pending knowledge review was not found.")
        return self._review_by_id(review_id)

    def _review_by_id(self, review_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM knowledge_reviews WHERE id=?", (review_id,)).fetchone()
        if not row:
            raise ResourceNotFoundError("Knowledge review was not found.")
        return self._review_row(row)

    @staticmethod
    def _review_row(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "signalId": row["signal_id"], "topicId": row["topic_id"], "action": row["action"], "proposal": json.loads(row["proposal_json"] or "{}"), "note": row["note"], "status": row["status"], "createdAt": row["created_at"], "decidedAt": row["decided_at"]}

    def _signal_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "topicId": row["topic_id"], "type": row["type"], "severity": row["severity"], "title": row["title"], "detail": row["detail"], "refs": self._json(row["refs_json"], {}), "fingerprint": row["fingerprint"], "status": row["status"], "resolutionNote": row["resolution_note"], "version": row["version"], "firstSeenAt": row["first_seen_at"], "lastSeenAt": row["last_seen_at"], "resolvedAt": row["resolved_at"]}

    def _claim_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "topicId": row["topic_id"], "text": row["text"], "status": row["status"], "sourcePath": row["source_path"], "locator": self._json(row["locator_json"], {}), "contentHash": row["content_hash"], "observedAt": row["observed_at"], "updatedAt": row["updated_at"], "evidence": self.evidence(row["id"])}

    @staticmethod
    def _evidence_row(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "claimId": row["claim_id"], "sourceId": row["source_id"], "sourcePath": row["source_path"], "locator": json.loads(row["locator_json"]), "stance": row["stance"], "excerpt": row["excerpt"], "contentHash": row["content_hash"], "observedAt": row["observed_at"]}
