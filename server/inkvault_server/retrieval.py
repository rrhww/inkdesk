from __future__ import annotations

import json
import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from inkvault_server.agents import AskContextTurnModel
from inkvault_server.embeddings import EmbeddingService
from inkvault_server.models import RetrievalChunk, Source, Topic
from inkvault_server.time_utils import ensure_utc_datetime


@dataclass(frozen=True)
class RetrievedCitation:
    chunk_id: str
    entity_type: str
    entity_id: str
    source_id: str | None
    topic_id: str | None
    title: str
    kind: str
    locator: str | None
    vault_path: str | None
    snippet: str
    score: float


@dataclass(frozen=True)
class RetrievalSelection:
    retrieval_mode: str
    citations: list[RetrievedCitation]

    @property
    def used_chunk_ids(self) -> list[str]:
        return [citation.chunk_id for citation in self.citations]


class RetrievalService:
    def __init__(self, db: Session, embedding_service: EmbeddingService):
        self.db = db
        self.embedding_service = embedding_service

    def health(self) -> dict[str, object]:
        pgvector_ready = False
        if self.db.bind is not None and self.db.bind.dialect.name == "postgresql":
            try:
                pgvector_ready = bool(
                    self.db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).first()
                )
            except Exception:
                pgvector_ready = False
        return {
            "pgvectorReady": pgvector_ready,
            "embeddingConfigured": self.embedding_service.embedding_configured,
            "retrievalMode": self.embedding_service.retrieval_mode,
        }

    def sync_source(self, source: Source) -> list[RetrievalChunk]:
        return self._sync_chunks(
            workspace_id=source.workspace_id,
            entity_type="SOURCE",
            entity_id=source.id,
            texts=self._split_text(
                "\n".join(
                    part
                    for part in [
                        source.title,
                        source.excerpt,
                        source.body,
                    ]
                    if part and part.strip()
                )
            ),
        )

    def sync_topic(self, topic: Topic) -> list[RetrievalChunk]:
        claims = [claim.statement for claim in sorted(topic.claims, key=lambda item: item.sort_order)]
        source_labels = [source.title for source in sorted(topic.sources, key=lambda item: ensure_utc_datetime(item.updated_at), reverse=True)]
        text = "\n".join(
            part
            for part in [
                topic.title,
                topic.summary,
                "Current Understanding: " + topic.current_understanding,
                "Open Questions: " + topic.open_questions,
                "Key Claims: " + "；".join(claims),
                "Sources: " + "；".join(source_labels),
            ]
            if part and part.strip()
        )
        return self._sync_chunks(
            workspace_id=topic.workspace_id,
            entity_type="TOPIC",
            entity_id=topic.id,
            texts=self._split_text(text),
        )

    def sync_workspace_entities(self, topics: list[Topic], sources: list[Source]) -> None:
        for topic in topics:
            self.sync_topic(topic)
        for source in sources:
            self.sync_source(source)

    def select_for_ask(
        self,
        *,
        workspace_id: str,
        question: str,
        topic: Topic | None,
        context_turns: list[AskContextTurnModel],
        topics: list[Topic],
        sources: list[Source],
        limit: int = 4,
    ) -> RetrievalSelection:
        if topic is not None:
            self.sync_topic(topic)
            for linked_source in topic.sources:
                self.sync_source(linked_source)
        else:
            self.sync_workspace_entities(topics, sources)

        query = self._build_query(question, context_turns)
        query_embedding = self.embedding_service.embed_texts([query])[0]
        if topic is not None:
            topic_source_ids = {source.id for source in topic.sources}
            chunks = self.db.scalars(
                select(RetrievalChunk).where(
                    RetrievalChunk.workspace_id == workspace_id,
                    (
                        ((RetrievalChunk.entity_type == "TOPIC") & (RetrievalChunk.entity_id == topic.id))
                        | ((RetrievalChunk.entity_type == "SOURCE") & (RetrievalChunk.entity_id.in_(topic_source_ids or {"__empty__"})))
                    ),
                )
            ).all()
        else:
            chunks = self.db.scalars(select(RetrievalChunk).where(RetrievalChunk.workspace_id == workspace_id)).all()
        ranked = self._rank_chunks(query, query_embedding, chunks, topic, topics, sources)
        if topic is not None:
            topic_ranked = [
                citation
                for citation in ranked
                if citation.entity_type == "TOPIC" and citation.entity_id == topic.id
            ]
            if topic_ranked:
                ranked = topic_ranked
        return RetrievalSelection(
            retrieval_mode=self.embedding_service.retrieval_mode,
            citations=ranked[:limit],
        )

    def select_for_compile(
        self,
        *,
        workspace_id: str,
        source: Source,
        matched_topic: Topic | None,
        topics: list[Topic],
        sources: list[Source],
        limit: int = 4,
    ) -> RetrievalSelection:
        self.sync_source(source)
        query = "\n".join(part for part in [source.title, source.excerpt, source.body] if part and part.strip())
        query_embedding = self.embedding_service.embed_texts([query])[0]
        if matched_topic is not None:
            self.sync_topic(matched_topic)
            related_sources = [item for item in matched_topic.sources if item.id != source.id]
            for related_source in related_sources:
                self.sync_source(related_source)
            candidate_chunks = self.db.scalars(
                select(RetrievalChunk).where(
                    RetrievalChunk.workspace_id == workspace_id,
                    (
                        ((RetrievalChunk.entity_type == "TOPIC") & (RetrievalChunk.entity_id == matched_topic.id))
                        | (
                            (RetrievalChunk.entity_type == "SOURCE")
                            & (RetrievalChunk.entity_id.in_({item.id for item in related_sources} or {"__empty__"}))
                        )
                    ),
                )
            ).all()
            ranked = self._rank_chunks(query, query_embedding, candidate_chunks, matched_topic, topics, sources)
            return RetrievalSelection(
                retrieval_mode=self.embedding_service.retrieval_mode,
                citations=ranked[:limit],
            )

        self.sync_workspace_entities(topics, [item for item in sources if item.id != source.id])
        candidate_chunks = self.db.scalars(
            select(RetrievalChunk).where(
                RetrievalChunk.workspace_id == workspace_id,
                ~(
                    (RetrievalChunk.entity_type == "SOURCE")
                    & (RetrievalChunk.entity_id == source.id)
                ),
            )
        ).all()
        ranked = self._rank_chunks(query, query_embedding, candidate_chunks, None, topics, sources)
        return RetrievalSelection(
            retrieval_mode=self.embedding_service.retrieval_mode,
            citations=ranked[:limit],
        )

    def match_topic_for_source(self, source: Source, topics: list[Topic]) -> Topic | None:
        if not topics:
            return None
        self.sync_source(source)
        for topic in topics:
            self.sync_topic(topic)
        topic_ids = [topic.id for topic in topics]
        chunks = self.db.scalars(
            select(RetrievalChunk).where(
                RetrievalChunk.workspace_id == source.workspace_id,
                RetrievalChunk.entity_type == "TOPIC",
                RetrievalChunk.entity_id.in_(topic_ids),
            )
        ).all()
        if not chunks:
            return None
        query = "\n".join(part for part in [source.title, source.excerpt, source.body] if part and part.strip())
        query_embedding = self.embedding_service.embed_texts([query])[0]
        scores_by_topic: dict[str, tuple[float, float, float]] = {}
        for chunk in chunks:
            lexical_score = self._lexical_score(chunk.text, query)
            vector_score = self.embedding_service.cosine_similarity(query_embedding, self._decode_embedding(chunk.embedding_json))
            combined_score = lexical_score + (vector_score * 2.0)
            previous = scores_by_topic.get(chunk.entity_id, (0.0, 0.0, 0.0))
            if combined_score > previous[0]:
                scores_by_topic[chunk.entity_id] = (combined_score, lexical_score, vector_score)
        if not scores_by_topic:
            return None
        ranked = sorted(
            ((topic, *scores_by_topic.get(topic.id, (0.0, 0.0, 0.0))) for topic in topics if topic.id in scores_by_topic),
            key=lambda item: (item[1], item[2], item[3], ensure_utc_datetime(item[0].updated_at)),
            reverse=True,
        )
        best_topic, best_score, best_lexical, best_vector = ranked[0]
        if self.embedding_service.retrieval_mode == "lexical_fallback":
            return best_topic if best_lexical >= 4.0 else None
        return best_topic if best_lexical >= 3.0 or best_vector >= 0.45 or best_score >= 3.4 else None

    def _sync_chunks(self, *, workspace_id: str, entity_type: str, entity_id: str, texts: list[str]) -> list[RetrievalChunk]:
        existing = self.db.scalars(
            select(RetrievalChunk)
            .where(
                RetrievalChunk.workspace_id == workspace_id,
                RetrievalChunk.entity_type == entity_type,
                RetrievalChunk.entity_id == entity_id,
            )
            .order_by(RetrievalChunk.chunk_ordinal.asc())
        ).all()
        normalized_texts = texts or [""]
        desired_hashes = [self._content_hash(entity_type, entity_id, ordinal, text) for ordinal, text in enumerate(normalized_texts, start=1)]
        changed_texts = [
            text
            for ordinal, text in enumerate(normalized_texts, start=1)
            if ordinal > len(existing) or existing[ordinal - 1].content_hash != desired_hashes[ordinal - 1]
        ]
        embeddings = self.embedding_service.embed_texts(changed_texts)
        embedding_index = 0
        now = datetime.now(UTC)
        synchronized: list[RetrievalChunk] = []
        for ordinal, text in enumerate(normalized_texts, start=1):
            content_hash = desired_hashes[ordinal - 1]
            if ordinal <= len(existing):
                chunk = existing[ordinal - 1]
                if chunk.content_hash != content_hash:
                    chunk.text = text
                    chunk.content_hash = content_hash
                    chunk.embedding_json = json.dumps(embeddings[embedding_index], ensure_ascii=False)
                    chunk.updated_at = now
                    embedding_index += 1
                    self.db.add(chunk)
                synchronized.append(chunk)
                continue
            chunk = RetrievalChunk(
                id=f"chunk-{uuid4().hex}",
                workspace_id=workspace_id,
                entity_type=entity_type,
                entity_id=entity_id,
                chunk_ordinal=ordinal,
                text=text,
                content_hash=content_hash,
                embedding_json=json.dumps(embeddings[embedding_index], ensure_ascii=False) if embeddings else "[]",
                updated_at=now,
            )
            embedding_index += 1
            self.db.add(chunk)
            synchronized.append(chunk)
        if len(existing) > len(normalized_texts):
            stale_ids = [chunk.id for chunk in existing[len(normalized_texts) :]]
            self.db.execute(delete(RetrievalChunk).where(RetrievalChunk.id.in_(stale_ids)))
        self.db.flush()
        return synchronized

    def _rank_chunks(
        self,
        query: str,
        query_embedding: list[float],
        chunks: list[RetrievalChunk],
        topic: Topic | None,
        topics: list[Topic],
        sources: list[Source],
    ) -> list[RetrievedCitation]:
        source_by_id = {source.id: source for source in sources}
        topic_by_id = {item.id: item for item in topics}
        ranked: list[RetrievedCitation] = []
        for chunk in chunks:
            lexical_score = self._lexical_score(chunk.text, query)
            vector_score = self.embedding_service.cosine_similarity(query_embedding, self._decode_embedding(chunk.embedding_json))
            boost = 0.0
            if topic is not None and chunk.entity_type == "TOPIC" and chunk.entity_id == topic.id:
                boost += 1000.0
            elif topic is None and chunk.entity_type == "TOPIC":
                boost += 50.0
            source = source_by_id.get(chunk.entity_id) if chunk.entity_type == "SOURCE" else None
            resolved_topic = topic_by_id.get(chunk.entity_id) if chunk.entity_type == "TOPIC" else None
            if lexical_score <= 0 and vector_score <= 0 and boost <= 0:
                continue
            if chunk.entity_type == "TOPIC" and resolved_topic is not None:
                ranked.append(
                    RetrievedCitation(
                        chunk_id=chunk.id,
                        entity_type="TOPIC",
                        entity_id=resolved_topic.id,
                        source_id=None,
                        topic_id=resolved_topic.id,
                        title=resolved_topic.title,
                        kind="TOPIC",
                        locator=None,
                        vault_path=resolved_topic.vault_path,
                        snippet=chunk.text[:240],
                        score=boost + lexical_score + vector_score,
                    )
                )
            elif chunk.entity_type == "SOURCE" and source is not None:
                ranked.append(
                    RetrievedCitation(
                        chunk_id=chunk.id,
                        entity_type="SOURCE",
                        entity_id=source.id,
                        source_id=source.id,
                        topic_id=None,
                        title=source.title,
                        kind=source.kind,
                        locator=source.locator,
                        vault_path=source.vault_path,
                        snippet=chunk.text[:240],
                        score=boost + lexical_score + vector_score,
                    )
                )
        ranked.sort(key=lambda item: item.score, reverse=True)
        seen_chunk_ids: set[str] = set()
        deduped: list[RetrievedCitation] = []
        for citation in ranked:
            if citation.chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(citation.chunk_id)
            deduped.append(citation)
        return deduped

    def _build_query(self, question: str, context_turns: list[AskContextTurnModel]) -> str:
        if not context_turns:
            return question
        lineage_context = "\n".join(f"Q: {turn.question}\nA: {turn.answer}" for turn in context_turns[-2:])
        return f"{question}\n{lineage_context}"

    def _split_text(self, text: str, chunk_size: int = 480) -> list[str]:
        normalized = " ".join((text or "").split()).strip()
        if not normalized:
            return [""]
        segments: list[str] = []
        start = 0
        while start < len(normalized):
            segments.append(normalized[start : start + chunk_size].strip())
            start += chunk_size
        return [segment for segment in segments if segment]

    def _lexical_score(self, text: str, query: str) -> float:
        normalized_text = self._normalize(text)
        if not normalized_text:
            return 0.0
        best = 0.0
        for term in self._extract_query_terms(query):
            if term in normalized_text:
                best = max(best, float(len(term)))
        return best

    def _extract_query_terms(self, query: str) -> list[str]:
        normalized_query = self._normalize(query)
        if not normalized_query:
            return []
        terms: list[str] = [normalized_query]
        seen = {normalized_query}
        minimum_length = 2 if any("\u4e00" <= char <= "\u9fff" for char in query) else 3
        maximum_length = min(6, len(normalized_query))
        for length in range(maximum_length, minimum_length - 1, -1):
            for start in range(0, len(normalized_query) - length + 1):
                term = normalized_query[start : start + length]
                if term not in seen:
                    seen.add(term)
                    terms.append(term)
        return terms

    def _normalize(self, value: str | None) -> str:
        return re.sub(r"[^\w\u4e00-\u9fff]+", "", (value or "").lower())

    def _decode_embedding(self, raw: str | None) -> list[float]:
        if not raw or not raw.strip():
            return []
        decoded = json.loads(raw)
        if not isinstance(decoded, list):
            return []
        return [float(item) for item in decoded]

    def _content_hash(self, entity_type: str, entity_id: str, ordinal: int, text: str) -> str:
        normalized = f"{entity_type}|{entity_id}|{ordinal}|{text}"
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
