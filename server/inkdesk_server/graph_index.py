from __future__ import annotations

import asyncio
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import yaml
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from inkdesk_server.core.config import Settings
from inkdesk_server.graph_classification import GraphClassification, classify_document


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
    "playwright-report",
    "target",
    "test-results",
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
    classification: GraphClassification = field(default_factory=GraphClassification)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GraphNode":
        raw_classification = payload.get("classification")
        if isinstance(raw_classification, Mapping):
            classification = GraphClassification(
                stage=str(raw_classification.get("stage") or "knowledge"),
                domain=str(raw_classification.get("domain") or "general"),
                category=str(raw_classification.get("category") or "document"),
                importance=str(raw_classification.get("importance") or "normal"),
                visibility=str(raw_classification.get("visibility") or "secondary"),
                origin=str(raw_classification.get("origin") or "fallback"),
            )
        else:
            classification, _ = classify_document(
                {},
                str(payload.get("path") or ""),
                source=str(payload.get("source") or "repo"),
                kind=str(payload.get("kind") or "document"),
            )
        return cls(
            id=str(payload["id"]),
            label=str(payload["label"]),
            kind=str(payload["kind"]),
            path=str(payload["path"]),
            source=str(payload["source"]),
            status=str(payload["status"]),
            summary=str(payload.get("summary") or ""),
            classification=classification,
        )


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
    classification_warnings: tuple[dict[str, str], ...] = ()

    @classmethod
    def empty(cls) -> "GraphSnapshot":
        return cls(version="empty", generated_at=datetime.now(UTC).isoformat(), nodes=(), edges=())

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generatedAt": self.generated_at,
            "nodes": [asdict(node) for node in self.nodes],
            "edges": [asdict(edge) for edge in self.edges],
            "classificationWarnings": list(self.classification_warnings),
            "stats": {
                "nodeCount": len(self.nodes),
                "edgeCount": len(self.edges),
                "missingCount": sum(1 for node in self.nodes if node.kind == "missing"),
                "classificationWarningCount": len(self.classification_warnings),
            },
        }

    def for_source(self, source: str) -> "GraphSnapshot":
        primary_ids = {node.id for node in self.nodes if node.source == source}
        missing_ids = {
            edge.target
            for edge in self.edges
            if edge.source in primary_ids and edge.target.startswith("missing:")
        }
        included_ids = primary_ids | missing_ids
        return GraphSnapshot(
            version=self.version,
            generated_at=self.generated_at,
            nodes=tuple(node for node in self.nodes if node.id in included_ids),
            edges=tuple(
                edge
                for edge in self.edges
                if edge.source in primary_ids and edge.target in included_ids
            ),
            classification_warnings=self.classification_warnings,
        )


@dataclass(frozen=True)
class ParsedDocument:
    node: GraphNode
    body: str
    links: tuple[str, ...]
    classification_warnings: tuple[dict[str, str], ...] = ()


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

    def scan(self) -> GraphSnapshot:
        documents = [self._parse_document(path, source) for path, source in self._iter_markdown_files()]
        documents = [document for document in documents if document is not None]
        classification_warnings = tuple(
            warning
            for document in documents
            for warning in document.classification_warnings
        )
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
                            classification=GraphClassification(
                                stage="knowledge",
                                domain="general",
                                category="missing",
                                importance="supporting",
                                visibility="secondary",
                                origin="rule",
                            ),
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
                "classificationWarnings": classification_warnings,
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
            classification_warnings=classification_warnings,
        )

        self.write_snapshot(snapshot)
        return snapshot

    def load_snapshot(self) -> GraphSnapshot:
        try:
            payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
            return GraphSnapshot(
                version=str(payload["version"]),
                generated_at=str(payload["generatedAt"]),
                nodes=tuple(GraphNode.from_dict(node) for node in payload.get("nodes", [])),
                edges=tuple(GraphEdge(**edge) for edge in payload.get("edges", [])),
                classification_warnings=tuple(payload.get("classificationWarnings", [])),
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

    def read_document(self, node: GraphNode) -> str:
        if node.source == "vault":
            root = self.vault_root
        elif node.source == "repo":
            root = self.repo_root
        else:
            raise FileNotFoundError(node.id)

        candidate = (root / node.path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise FileNotFoundError(node.id) from error
        if candidate.suffix.casefold() != ".md" or not candidate.is_file():
            raise FileNotFoundError(node.id)
        return candidate.read_text(encoding="utf-8")

    def _iter_markdown_files(self):
        seen: set[Path] = set()
        wiki_root = self.vault_root / "wiki"
        if wiki_root.is_dir():
            for path in self._walk_markdown_files(wiki_root):
                resolved = path.resolve()
                seen.add(resolved)
                yield resolved, "vault"

        if not self.repo_root.is_dir():
            return
        for path in self._walk_markdown_files(self.repo_root):
            resolved = path.resolve()
            if resolved in seen or self._is_skipped(resolved):
                continue
            yield resolved, "repo"

    def _walk_markdown_files(self, root: Path):
        for current, directory_names, file_names in os.walk(root):
            directory_names[:] = sorted(
                name
                for name in directory_names
                if name not in SKIPPED_PARTS and name != ".inkdesk"
            )
            current_path = Path(current)
            for file_name in sorted(file_names):
                if file_name.casefold().endswith(".md"):
                    yield current_path / file_name

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
        kind = self._kind(metadata, relative)
        classification, warnings = classify_document(metadata, relative, source=source, kind=kind)
        node = GraphNode(
            id=f"{source}:{relative}",
            label=title,
            kind=kind,
            path=relative,
            source=source,
            status=str(metadata.get("status") or "indexed"),
            summary=summary,
            classification=classification,
        )
        links = tuple(dict.fromkeys(WIKILINK_PATTERN.findall(body) + MARKDOWN_LINK_PATTERN.findall(body)))
        return ParsedDocument(
            node=node,
            body=body,
            links=links,
            classification_warnings=tuple({"path": relative, **asdict(warning)} for warning in warnings),
        )

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

    def publish_runtime(self, event_type: str, data: Mapping[str, Any]) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        loop.call_soon_threadsafe(self._fanout, {"event": event_type, **dict(data)})

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

    def read_document(self, node_id: str) -> dict[str, str]:
        node = next((item for item in self.current().nodes if item.id == node_id), None)
        if node is None:
            raise FileNotFoundError(node_id)
        return {
            "id": node.id,
            "title": node.label,
            "sourcePath": node.path,
            "content": self.scanner.read_document(node),
        }

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
            snapshot = self.scanner.scan()
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
