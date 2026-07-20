from __future__ import annotations

import asyncio
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from inkdesk_server.core.config import Settings
from inkdesk_server.db import session_scope
from inkdesk_server.embeddings import EmbeddingService
from inkdesk_server.models import User, Workspace
from inkdesk_server.retrieval import RetrievalService


WIKILINK_PATTERN = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)#]+\.md)(?:#[^)]+)?\)")
HEADING_PATTERN = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
SKIPPED_PARTS = {
    ".git",
    ".next",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "target",
}


@dataclass(frozen=True)
class GraphNode:
    id: str
    label: str
    kind: str
    path: str
    source: str
    status: str
    summary: str


@dataclass(frozen=True)
class GraphEdge:
    id: str
    source: str
    target: str
    kind: str = "wikilink"


@dataclass(frozen=True)
class GraphSnapshot:
    version: str
    generated_at: str
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]

    @classmethod
    def empty(cls) -> "GraphSnapshot":
        return cls(version="empty", generated_at=datetime.now(UTC).isoformat(), nodes=(), edges=())

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generatedAt": self.generated_at,
            "nodes": [asdict(node) for node in self.nodes],
            "edges": [asdict(edge) for edge in self.edges],
            "stats": {
                "nodeCount": len(self.nodes),
                "edgeCount": len(self.edges),
                "missingCount": sum(1 for node in self.nodes if node.kind == "missing"),
            },
        }


@dataclass(frozen=True)
class ParsedDocument:
    node: GraphNode
    body: str
    links: tuple[str, ...]


class DirectoryScanner:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.vault_root = Path(settings.vault_root).expanduser().resolve()
        self.repo_root = (
            Path(settings.repo_root).expanduser().resolve()
            if settings.repo_root
            else Path(__file__).resolve().parents[2]
        )
        self.snapshot_path = self.vault_root / ".inkdesk" / "graph" / "snapshot.json"

    def scan(self, db: Session | None = None) -> GraphSnapshot:
        documents = [self._parse_document(path, source) for path, source in self._iter_markdown_files()]
        documents = [document for document in documents if document is not None]
        nodes = {document.node.id: document.node for document in documents}
        aliases = self._build_aliases(documents)
        edges: dict[str, GraphEdge] = {}

        for document in documents:
            for link in document.links:
                target_id = self._resolve_target(document, link, aliases)
                if target_id is None:
                    target_id = "missing:" + sha256(link.casefold().encode("utf-8")).hexdigest()[:20]
                    nodes.setdefault(
                        target_id,
                        GraphNode(
                            id=target_id,
                            label=link,
                            kind="missing",
                            path=link,
                            source="unresolved",
                            status="missing",
                            summary="Unresolved knowledge link",
                        ),
                    )
                edge_id = sha256(f"{document.node.id}|{target_id}".encode("utf-8")).hexdigest()[:24]
                edges[edge_id] = GraphEdge(id=edge_id, source=document.node.id, target=target_id)

        ordered_nodes = tuple(sorted(nodes.values(), key=lambda node: (node.kind, node.path.casefold())))
        ordered_edges = tuple(sorted(edges.values(), key=lambda edge: edge.id))
        version_input = json.dumps(
            {
                "nodes": [asdict(node) for node in ordered_nodes],
                "edges": [asdict(edge) for edge in ordered_edges],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        snapshot = GraphSnapshot(
            version=sha256(version_input.encode("utf-8")).hexdigest()[:24],
            generated_at=datetime.now(UTC).isoformat(),
            nodes=ordered_nodes,
            edges=ordered_edges,
        )

        if db is not None:
            self._sync_retrieval_index(db, documents)
        self.write_snapshot(snapshot)
        return snapshot

    def load_snapshot(self) -> GraphSnapshot:
        try:
            payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
            return GraphSnapshot(
                version=str(payload["version"]),
                generated_at=str(payload["generatedAt"]),
                nodes=tuple(GraphNode(**node) for node in payload.get("nodes", [])),
                edges=tuple(GraphEdge(**edge) for edge in payload.get("edges", [])),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return GraphSnapshot.empty()

    def write_snapshot(self, snapshot: GraphSnapshot) -> None:
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.snapshot_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(snapshot.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.snapshot_path)

    def _iter_markdown_files(self):
        seen: set[Path] = set()
        wiki_root = self.vault_root / "wiki"
        if wiki_root.is_dir():
            for path in sorted(wiki_root.rglob("*.md")):
                resolved = path.resolve()
                seen.add(resolved)
                yield resolved, "vault"

        if not self.repo_root.is_dir():
            return
        for path in sorted(self.repo_root.rglob("*.md")):
            resolved = path.resolve()
            if resolved in seen or self._is_skipped(resolved):
                continue
            yield resolved, "repo"

    def _is_skipped(self, path: Path) -> bool:
        try:
            relative = path.relative_to(self.repo_root)
        except ValueError:
            return True
        if any(part in SKIPPED_PARTS for part in relative.parts):
            return True
        try:
            path.relative_to(self.vault_root / ".inkdesk")
            return True
        except ValueError:
            return False

    def _parse_document(self, path: Path, source: str) -> ParsedDocument | None:
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        metadata, body = self._split_frontmatter(content)
        relative = self._relative_path(path, source)
        title_match = HEADING_PATTERN.search(body)
        title = str(metadata.get("title") or (title_match.group(1).strip() if title_match else path.stem))
        summary = self._summary(metadata, body)
        node = GraphNode(
            id=f"{source}:{relative}",
            label=title,
            kind=self._kind(metadata, relative),
            path=relative,
            source=source,
            status=str(metadata.get("status") or "indexed"),
            summary=summary,
        )
        links = tuple(dict.fromkeys(WIKILINK_PATTERN.findall(body) + MARKDOWN_LINK_PATTERN.findall(body)))
        return ParsedDocument(node=node, body=body, links=links)

    def _split_frontmatter(self, content: str) -> tuple[dict[str, Any], str]:
        if not content.startswith("---\n") and not content.startswith("---\r\n"):
            return {}, content
        normalized = content.replace("\r\n", "\n")
        end = normalized.find("\n---\n", 4)
        if end < 0:
            return {}, content
        try:
            metadata = yaml.safe_load(normalized[4:end]) or {}
        except yaml.YAMLError:
            metadata = {}
        return (metadata if isinstance(metadata, dict) else {}), normalized[end + 5 :]

    def _relative_path(self, path: Path, source: str) -> str:
        root = self.vault_root if source == "vault" else self.repo_root
        return path.relative_to(root).as_posix()

    def _summary(self, metadata: dict[str, Any], body: str) -> str:
        declared = metadata.get("summary") or metadata.get("description")
        if declared:
            return str(declared).strip()[:240]
        lines = [line.strip() for line in body.splitlines() if line.strip() and not line.lstrip().startswith("#")]
        return (lines[0] if lines else "")[:240]

    def _kind(self, metadata: dict[str, Any], relative_path: str) -> str:
        raw = " ".join(
            str(value).casefold()
            for value in (metadata.get("type"), metadata.get("kind"), metadata.get("inkdeskType"), relative_path)
            if value
        )
        if "interface" in raw or "class" in raw:
            return "class"
        if "tech-solution" in raw or "solution" in raw or "design" in raw:
            return "solution"
        if "source" in raw or "raw" in raw:
            return "source"
        if "concept" in raw or "topic" in raw or relative_path.startswith("wiki/"):
            return "concept"
        return "document"

    def _build_aliases(self, documents: list[ParsedDocument]) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for document in documents:
            path = document.node.path.replace("\\", "/")
            without_suffix = path[:-3] if path.casefold().endswith(".md") else path
            for alias in {
                path.casefold(),
                without_suffix.casefold(),
                Path(path).stem.casefold(),
                document.node.label.casefold(),
            }:
                aliases.setdefault(alias, document.node.id)
        return aliases

    def _resolve_target(self, document: ParsedDocument, raw_target: str, aliases: dict[str, str]) -> str | None:
        target = raw_target.strip().replace("\\", "/")
        without_suffix = target[:-3] if target.casefold().endswith(".md") else target
        parent = Path(document.node.path).parent.as_posix()
        candidates = [target, without_suffix, Path(target).stem]
        if parent not in {"", "."}:
            candidates.extend([f"{parent}/{target}", f"{parent}/{without_suffix}"])
        for candidate in candidates:
            resolved = aliases.get(candidate.casefold())
            if resolved:
                return resolved
        return None

    def _sync_retrieval_index(self, db: Session, documents: list[ParsedDocument]) -> None:
        workspace = db.scalar(select(Workspace).where(Workspace.slug == "inkdesk"))
        if workspace is None:
            now = datetime.now(UTC)
            owner = User(
                id="system-graph-owner",
                username="system-graph-owner",
                email="system-graph-owner@inkdesk.local",
                password_hash="disabled",
                status="SYSTEM",
                created_at=now,
                updated_at=now,
            )
            workspace = Workspace(
                id="system-graph-workspace",
                owner_user=owner,
                name="Inkdesk graph cache",
                slug="inkdesk",
                created_at=now,
                updated_at=now,
            )
            db.add(workspace)
            db.flush()
        retrieval = RetrievalService(db, EmbeddingService(self.settings))
        document_ids: set[str] = set()
        for document in documents:
            document_ids.add(document.node.id)
            retrieval.sync_vault_document(
                workspace_id=workspace.id,
                document_id=document.node.id,
                text_content="\n".join(part for part in (document.node.label, document.node.summary, document.body) if part),
            )
        retrieval.remove_missing_vault_documents(workspace.id, document_ids)


class GraphEventBus:
    def __init__(self):
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = threading.Lock()

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=8)
        with self._lock:
            self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._subscribers.discard(queue)

    def publish(self, snapshot: GraphSnapshot, reason: str) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        event = {"event": "graph.updated", "reason": reason, "snapshot": snapshot.to_dict()}
        loop.call_soon_threadsafe(self._fanout, event)

    def _fanout(self, event: dict[str, Any]) -> None:
        with self._lock:
            subscribers = tuple(self._subscribers)
        for queue in subscribers:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(event)


class GraphIndexRuntime:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.scanner = DirectoryScanner(settings)
        self.events = GraphEventBus()
        self._snapshot = self.scanner.load_snapshot()
        self._snapshot_lock = threading.Lock()
        self._refresh_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="inkdesk-graph-index")
        self._observer: Observer | None = None
        self._debounce_timer: threading.Timer | None = None
        self._stopped = False

    def current(self) -> GraphSnapshot:
        with self._snapshot_lock:
            return self._snapshot

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self.events.attach_loop(loop)
        self._start_observer()
        self.schedule_refresh("startup", debounce_seconds=0.0)

    def stop(self) -> None:
        self._stopped = True
        if self._debounce_timer is not None:
            self._debounce_timer.cancel()
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=3)
        self._executor.shutdown(wait=True, cancel_futures=True)

    def refresh(self, reason: str = "manual") -> GraphSnapshot:
        with self._refresh_lock:
            with session_scope() as db:
                snapshot = self.scanner.scan(db)
            with self._snapshot_lock:
                changed = snapshot.version != self._snapshot.version
                self._snapshot = snapshot
            if changed or reason == "startup":
                self.events.publish(snapshot, reason)
            return snapshot

    def schedule_refresh(self, reason: str, debounce_seconds: float = 0.08) -> None:
        if self._stopped:
            return
        with self._snapshot_lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(
                debounce_seconds,
                lambda: self._executor.submit(self.refresh, reason),
            )
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def _start_observer(self) -> None:
        roots = {self.scanner.vault_root, self.scanner.repo_root}
        handler = MarkdownChangeHandler(self)
        observer = Observer()
        scheduled = False
        for root in roots:
            root.mkdir(parents=True, exist_ok=True)
            observer.schedule(handler, str(root), recursive=True)
            scheduled = True
        if scheduled:
            observer.start()
            self._observer = observer


class MarkdownChangeHandler(FileSystemEventHandler):
    def __init__(self, runtime: GraphIndexRuntime):
        super().__init__()
        self.runtime = runtime

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.casefold() != ".md" or any(part in SKIPPED_PARTS or part == ".inkdesk" for part in path.parts):
            return
        self.runtime.schedule_refresh(f"{event.event_type}:{path.name}")
