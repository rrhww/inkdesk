from __future__ import annotations

import re
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

import yaml

from inkdesk_server.graph_index import GraphIndexRuntime, GraphNode, GraphSnapshot
from inkdesk_server.schemas import (
    KnowledgeBriefing,
    KnowledgeDocument,
    KnowledgeRelatedTopic,
    KnowledgeSearchResponse,
    KnowledgeSignal,
    KnowledgeSource,
    KnowledgeSourcesResponse,
    KnowledgeTopicList,
    KnowledgeTopicStats,
    KnowledgeTopicSummary,
)
from inkdesk_server.security import ApiError, ResourceNotFoundError


SECTION_PATTERN = re.compile(r"^#{2,3}\s+(.+?)\s*$", re.MULTILINE)
CODE_PATH_PATTERN = re.compile(
    r"(?<![\w/.-])((?:server|web|scripts|docs|vault|src|tests)/[\w@.+()\-/\\]+(?:\.[A-Za-z0-9_-]+)?)"
)
LIST_PREFIX_PATTERN = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)")
QUESTION_HEADINGS = {"open questions", "open question", "未解问题", "开放问题", "待确认问题"}
UNDERSTANDING_HEADINGS = {"current understanding", "understanding", "当前理解", "现状理解", "摘要"}
DECISION_HEADINGS = {"key decisions", "decisions", "关键决策", "决策"}
CODE_PATH_HEADINGS = {"code paths", "related code", "相关代码", "代码路径"}
SIGNAL_TYPES = {"stale", "unsupported", "conflicting", "open_question", "missing_link"}


class KnowledgeService:
    """Builds a read-only knowledge view from the file-backed graph snapshot."""

    def __init__(self, graph_runtime: GraphIndexRuntime):
        self.graph_runtime = graph_runtime

    def list_topics(self) -> KnowledgeTopicList:
        snapshot = self._snapshot()
        topics = [self._topic_summary(snapshot, node) for node in self._topic_nodes(snapshot)]
        topics.sort(key=lambda item: (-item.signalCount, item.title.casefold(), item.id))
        return KnowledgeTopicList(
            topics=topics,
            stats=KnowledgeTopicStats(
                topicCount=len(topics),
                sourceCount=sum(1 for node in snapshot.nodes if node.kind == "source"),
                signalCount=sum(topic.signalCount for topic in topics),
                attentionCount=sum(1 for topic in topics if topic.signalCount),
            ),
        )

    def search(self, query: str, scope: str = "all") -> KnowledgeSearchResponse:
        normalized_scope = (scope or "all").strip().casefold()
        if normalized_scope not in {"all", "vault", "repo"}:
            raise ApiError(
                400,
                "INVALID_KNOWLEDGE_SCOPE",
                "Knowledge scope must be 'all', 'vault', or 'repo'.",
            )

        normalized_query = " ".join(query.split()).casefold()
        if not normalized_query:
            return KnowledgeSearchResponse(query="", results=[])
        terms = tuple(dict.fromkeys(normalized_query.split()))
        snapshot = self._snapshot()
        matches: list[tuple[int, KnowledgeTopicSummary]] = []
        for node in self._topic_nodes(snapshot):
            if normalized_scope != "all" and node.source != normalized_scope:
                continue
            document = self._document(node)
            haystack = "\n".join((node.label, node.summary, node.path, document)).casefold()
            if not all(term in haystack for term in terms):
                continue
            score = sum(haystack.count(term) for term in terms)
            if normalized_query in haystack:
                score += 10
            if normalized_query in node.label.casefold():
                score += 20
            matches.append((score, self._topic_summary(snapshot, node, document=document)))
        matches.sort(key=lambda item: (-item[0], item[1].title.casefold(), item[1].id))
        return KnowledgeSearchResponse(query=" ".join(query.split()), results=[item for _, item in matches])

    def briefing(self, topic_id: str) -> KnowledgeBriefing:
        snapshot = self._snapshot()
        node = self._require_topic(snapshot, topic_id)
        document = self._document(node)
        metadata, body = self._split_frontmatter(document)
        sections = self._sections(body)
        questions = self._open_questions(metadata, sections)
        signals = self._signals(snapshot, node, metadata, sections, questions)
        sources = self._sources(snapshot, node)
        related = self._related_topics(snapshot, node)
        understanding = self._section_items(sections, UNDERSTANDING_HEADINGS)
        decisions = self._section_items(sections, DECISION_HEADINGS)
        if not understanding and node.summary:
            understanding = [node.summary]
        code_paths = self._code_paths(sections, body)
        confidence = self._confidence(signals, source_count=len(sources))
        source_coverage, provenance_status = self._provenance(sources)
        return KnowledgeBriefing(
            topicId=self.topic_id(node.id),
            title=node.label,
            summary=node.summary,
            kind=node.kind,
            path=node.path,
            source=node.source,
            status=node.status,
            sourceCount=len(sources),
            openQuestionCount=len(questions),
            signalCount=len(signals),
            currentUnderstanding=understanding,
            keyDecisions=decisions,
            openQuestions=questions,
            sources=sources,
            codePaths=code_paths,
            relatedTopics=related,
            signals=signals,
            healthSignals=signals,
            documentId=node.id,
            updatedAt=self._updated_at(node),
            confidence=confidence,
            sourceCoverage=source_coverage,
            provenanceStatus=provenance_status,
        )

    def sources(self, topic_id: str) -> KnowledgeSourcesResponse:
        snapshot = self._snapshot()
        node = self._require_topic(snapshot, topic_id)
        return KnowledgeSourcesResponse(topicId=topic_id, sources=self._sources(snapshot, node))

    def document(self, topic_id: str) -> KnowledgeDocument:
        """Return a topic's Markdown through the graph's validated document reader.

        Callers identify documents by the public, stable topic id. The scanner still
        performs the root/extension/path checks, so arbitrary filesystem paths never
        enter this service boundary.
        """
        snapshot = self._snapshot()
        node = self._require_topic(snapshot, topic_id)
        content = self._document(node)
        if not content:
            raise ResourceNotFoundError("Knowledge document was not found.")
        return KnowledgeDocument(
            documentId=node.id,
            title=node.label,
            source=node.source,
            path=node.path,
            content=content,
            contentHash=self._content_hash(content),
        )

    def document_by_id(self, document_id: str) -> KnowledgeDocument:
        """Resolve a graph document id without accepting a path from the client."""
        snapshot = self._snapshot()
        node = next(
            (item for item in snapshot.nodes if item.id == document_id and item.kind != "missing"),
            None,
        )
        if node is None:
            raise ResourceNotFoundError("Knowledge document was not found.")
        content = self._document(node)
        if not content:
            raise ResourceNotFoundError("Knowledge document was not found.")
        return KnowledgeDocument(
            documentId=node.id,
            title=node.label,
            source=node.source,
            path=node.path,
            content=content,
            contentHash=self._content_hash(content),
        )

    @staticmethod
    def topic_id(node_id: str) -> str:
        return "topic-" + sha256(node_id.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def source_id(node_id: str) -> str:
        return "source-" + sha256(node_id.encode("utf-8")).hexdigest()[:16]

    def _snapshot(self) -> GraphSnapshot:
        snapshot = self.graph_runtime.current()
        if snapshot.version == "empty":
            snapshot = self.graph_runtime.refresh("knowledge-api")
        return snapshot

    def _topic_nodes(self, snapshot: GraphSnapshot) -> list[GraphNode]:
        return [node for node in snapshot.nodes if self._is_knowledge_node(node)]

    @staticmethod
    def _is_knowledge_node(node: GraphNode) -> bool:
        if node.kind in {"missing", "source"}:
            return False
        normalized = node.path.replace("\\", "/").casefold()
        if node.source == "vault":
            return normalized.startswith("wiki/")
        return normalized.startswith("docs/") or (
            "/" not in normalized and normalized.endswith(".md") and normalized not in {"agents.md", "claude.md"}
        )

    def _require_topic(self, snapshot: GraphSnapshot, topic_id: str) -> GraphNode:
        node = next(
            (node for node in self._topic_nodes(snapshot) if self.topic_id(node.id) == topic_id),
            None,
        )
        if node is None:
            raise ResourceNotFoundError("Knowledge topic was not found.")
        return node

    def _topic_summary(
        self,
        snapshot: GraphSnapshot,
        node: GraphNode,
        *,
        document: str | None = None,
    ) -> KnowledgeTopicSummary:
        content = document if document is not None else self._document(node)
        metadata, body = self._split_frontmatter(content)
        sections = self._sections(body)
        questions = self._open_questions(metadata, sections)
        signals = self._signals(snapshot, node, metadata, sections, questions)
        sources = self._sources(snapshot, node)
        source_coverage, provenance_status = self._provenance(sources)
        return KnowledgeTopicSummary(
            id=self.topic_id(node.id),
            title=node.label,
            summary=node.summary,
            kind=node.kind,
            path=node.path,
            source=node.source,
            status=node.status,
            updatedAt=self._updated_at(node),
            sourceCount=len(sources),
            openQuestionCount=len(questions),
            signalCount=len(signals),
            signals=signals,
            healthSignals=signals,
            vaultPath=node.path if node.source == "vault" else None,
            sourceCoverage=source_coverage,
            provenanceStatus=provenance_status,
        )

    def _document(self, node: GraphNode) -> str:
        try:
            return self.graph_runtime.scanner.read_document(node)
        except (FileNotFoundError, OSError, UnicodeDecodeError):
            return ""

    def _updated_at(self, node: GraphNode) -> str:
        root = (
            self.graph_runtime.scanner.vault_root
            if node.source == "vault"
            else self.graph_runtime.scanner.repo_root
        )
        path = (root / node.path).resolve()
        try:
            timestamp = path.stat().st_mtime
        except OSError:
            return self._snapshot().generated_at
        return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()

    def _sources(self, snapshot: GraphSnapshot, node: GraphNode) -> list[KnowledgeSource]:
        nodes = {item.id: item for item in snapshot.nodes}
        linked_ids: set[str] = set()
        for edge in snapshot.edges:
            if edge.source == node.id:
                linked_ids.add(edge.target)
            elif edge.target == node.id:
                linked_ids.add(edge.source)
        source_nodes = [nodes[node_id] for node_id in linked_ids if node_id in nodes and nodes[node_id].kind == "source"]
        source_nodes.sort(key=lambda item: (item.label.casefold(), item.id))
        return [
            self._source_record(source)
            for source in source_nodes
        ]

    def _source_record(self, source: GraphNode) -> KnowledgeSource:
        content = self._document(source)
        return KnowledgeSource(
            id=self.source_id(source.id),
            documentId=source.id,
            title=source.label,
            path=source.path,
            source=source.source,
            kind=source.kind,
            summary=source.summary,
            updatedAt=self._updated_at(source),
            href=f"/api/knowledge/documents/{quote(source.id, safe='')}",
            locator=self._locator(content),
            excerpt=self._excerpt(content, source.summary),
            contentHash=self._content_hash(content) if content else None,
            sourceCoverage="supported" if content else "unknown",
            provenanceStatus="supported" if content else "unknown",
        )

    @staticmethod
    def _content_hash(content: str) -> str:
        return sha256(content.replace("\r\n", "\n").encode("utf-8")).hexdigest()

    @staticmethod
    def _excerpt(content: str, fallback: str = "") -> str:
        normalized_content = content.replace("\r\n", "\n")
        if normalized_content.startswith("---\n"):
            frontmatter_end = normalized_content.find("\n---\n", 4)
            if frontmatter_end >= 0:
                normalized_content = normalized_content[frontmatter_end + 5 :]
        lines = [
            line.strip()
            for line in normalized_content.splitlines()
            if line.strip() and not line.lstrip().startswith(("#", "---"))
        ]
        excerpt = " ".join(lines) if lines else fallback
        return " ".join(excerpt.split())[:320]

    @staticmethod
    def _locator(content: str) -> dict[str, str | int] | None:
        normalized = content.replace("\r\n", "\n")
        lines = normalized.splitlines()
        heading = next((line.lstrip()[1:].strip() for line in lines if line.lstrip().startswith("#")), None)
        if not lines:
            return None
        locator: dict[str, str | int] = {"startLine": 1, "endLine": len(lines)}
        if heading:
            locator["heading"] = heading
            locator["anchor"] = re.sub(r"[^a-z0-9 -]", "", heading.casefold()).strip().replace(" ", "-")
        return locator

    @staticmethod
    def _provenance(sources: list[KnowledgeSource]) -> tuple[str, str]:
        if not sources:
            return "none", "unsupported"
        if all(source.contentHash for source in sources):
            return "supported", "supported"
        return "partial", "partial"

    def _related_topics(self, snapshot: GraphSnapshot, node: GraphNode) -> list[KnowledgeRelatedTopic]:
        nodes = {item.id: item for item in self._topic_nodes(snapshot)}
        related_ids: set[str] = set()
        for edge in snapshot.edges:
            if edge.source == node.id:
                related_ids.add(edge.target)
            elif edge.target == node.id:
                related_ids.add(edge.source)
        related = [nodes[node_id] for node_id in related_ids if node_id in nodes]
        related.sort(key=lambda item: (item.label.casefold(), item.id))
        return [
            KnowledgeRelatedTopic(id=self.topic_id(item.id), title=item.label, kind=item.kind)
            for item in related
        ]

    def _signals(
        self,
        snapshot: GraphSnapshot,
        node: GraphNode,
        metadata: dict[str, Any],
        sections: dict[str, list[str]],
        questions: list[str],
    ) -> list[KnowledgeSignal]:
        signals: dict[str, KnowledgeSignal] = {}

        def add(signal_type: str, title: str, detail: str, severity: str = "warning") -> None:
            signals.setdefault(
                signal_type,
                KnowledgeSignal(
                    id="signal-" + sha256(f"{node.id}:{signal_type}".encode("utf-8")).hexdigest()[:16],
                    type=signal_type,
                    severity=severity,
                    title=title,
                    detail=detail,
                    sourcePath=node.path,
                ),
            )

        declared: list[str] = []
        for value in (metadata.get("healthSignals"), metadata.get("health")):
            if isinstance(value, str):
                declared.append(value)
            elif isinstance(value, list):
                declared.extend(str(item) for item in value)
        normalized_declared = {self._normalize_signal_type(item) for item in declared}
        normalized_status = self._normalize_signal_type(node.status)
        if "stale" in normalized_declared or normalized_status == "stale":
            add("stale", "Knowledge may be stale", "This topic is explicitly marked for freshness review.")
        if "unsupported" in normalized_declared or normalized_status == "unsupported":
            add("unsupported", "Evidence is incomplete", "This topic includes a claim without sufficient evidence.")
        if "conflicting" in normalized_declared or normalized_status == "conflicting":
            add("conflicting", "Conflicting knowledge", "This topic contains an unresolved conflicting judgment.", "critical")
        if "missing_link" in normalized_declared or normalized_status == "missing_link":
            add("missing_link", "Evidence link is unresolved", "This topic contains a link that could not be resolved.")

        claims = metadata.get("claims")
        if isinstance(claims, list):
            for claim in claims:
                if not isinstance(claim, dict):
                    continue
                provenance = str(claim.get("provenanceStatus") or claim.get("provenance_status") or "").casefold()
                if provenance == "unsupported":
                    add("unsupported", "Evidence is incomplete", "At least one claim has no supporting evidence.")
                if claim.get("stale") or claim.get("needsReview"):
                    add("stale", "Knowledge may be stale", "At least one claim requires freshness review.")
                if claim.get("hasConflict") or claim.get("conflicting"):
                    add("conflicting", "Conflicting knowledge", "At least one claim has conflicting evidence.", "critical")

        missing_labels = []
        node_by_id = {item.id: item for item in snapshot.nodes}
        for edge in snapshot.edges:
            if edge.source != node.id:
                continue
            target = node_by_id.get(edge.target)
            if target is not None and target.kind == "missing":
                missing_labels.append(target.label)
        if missing_labels:
            add(
                "missing_link",
                "Evidence link is unresolved",
                "Unresolved references: " + ", ".join(sorted(set(missing_labels), key=str.casefold)),
            )
            add(
                "unsupported",
                "Evidence link is unresolved",
                "Unresolved references: " + ", ".join(sorted(set(missing_labels), key=str.casefold)),
            )

        conflict_items = self._section_items(sections, {"conflicts", "conflict", "冲突", "冲突判断"})
        if conflict_items:
            add("conflicting", "Conflicting knowledge", "This topic records unresolved conflicting judgments.", "critical")
        if questions:
            add("open_question", "Open questions remain", f"{len(questions)} question(s) still require an answer.", "info")
        return [
            signals[key]
            for key in ("stale", "unsupported", "conflicting", "open_question", "missing_link")
            if key in signals
        ]

    @staticmethod
    def _normalize_signal_type(value: str) -> str:
        normalized = str(value).strip().casefold().replace("-", "_").replace(" ", "_")
        aliases = {
            "conflict": "conflicting",
            "unsupported_claim": "unsupported",
            "stale_claim": "stale",
            "open_questions": "open_question",
            "missing": "missing_link",
            "unresolved_link": "missing_link",
        }
        normalized = aliases.get(normalized, normalized)
        return normalized if normalized in SIGNAL_TYPES else normalized

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
        return (metadata if isinstance(metadata, dict) else {}), normalized[end + 5 :]

    @staticmethod
    def _sections(body: str) -> dict[str, list[str]]:
        matches = list(SECTION_PATTERN.finditer(body))
        sections: dict[str, list[str]] = {}
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
            key = match.group(1).strip().casefold()
            sections.setdefault(key, []).extend(body[start:end].strip().splitlines())
        return sections

    def _open_questions(self, metadata: dict[str, Any], sections: dict[str, list[str]]) -> list[str]:
        questions: list[str] = []
        declared = metadata.get("openQuestions") or metadata.get("open_questions")
        if isinstance(declared, str):
            questions.append(declared)
        elif isinstance(declared, list):
            questions.extend(str(item) for item in declared)
        for heading, lines in sections.items():
            if heading not in QUESTION_HEADINGS:
                continue
            for line in lines:
                stripped = line.strip()
                if not stripped or not (LIST_PREFIX_PATTERN.match(stripped) or stripped.endswith(("?", "？"))):
                    continue
                questions.append(LIST_PREFIX_PATTERN.sub("", stripped).strip())
        return self._deduplicate(questions)

    def _section_items(self, sections: dict[str, list[str]], accepted: set[str]) -> list[str]:
        items: list[str] = []
        for heading, lines in sections.items():
            if heading not in accepted:
                continue
            for line in lines:
                cleaned = LIST_PREFIX_PATTERN.sub("", line.strip()).strip()
                cleaned = cleaned.strip("`")
                if cleaned:
                    items.append(cleaned)
        return self._deduplicate(items)

    def _code_paths(self, sections: dict[str, list[str]], body: str) -> list[str]:
        paths = self._section_items(sections, CODE_PATH_HEADINGS)
        paths.extend(match.replace("\\", "/") for match in CODE_PATH_PATTERN.findall(body))
        return self._deduplicate(paths)

    @staticmethod
    def _deduplicate(values: Iterable[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = " ".join(str(value).split()).strip()
            key = cleaned.casefold()
            if cleaned and key not in seen:
                seen.add(key)
                result.append(cleaned)
        return result

    @staticmethod
    def _confidence(signals: list[KnowledgeSignal], source_count: int = 1) -> float:
        penalties = {
            "stale": 0.2,
            "unsupported": 0.25,
            "conflicting": 0.25,
            "open_question": 0.1,
        }
        confidence = max(0.1, 1.0 - sum(penalties.get(signal.type, 0.0) for signal in signals))
        # A topic with no linked source is not a high-confidence fact, even if it
        # has no explicit health signal yet.
        if source_count == 0:
            confidence = min(confidence, 0.25)
        return round(confidence, 2)
