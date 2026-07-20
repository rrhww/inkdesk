from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from inkdesk_server.embeddings import EmbeddingService
from inkdesk_server.models import RetrievalChunk


class RetrievalService:
    """Rebuildable vector-cache storage for file-backed documents."""

    def __init__(self, db: Session, embedding_service: EmbeddingService):
        self.db = db
        self.embedding_service = embedding_service

    def sync_vault_document(
        self, workspace_id: str, document_id: str, text_content: str
    ) -> list[RetrievalChunk]:
        texts = self._split_text(text_content)
        existing = self.db.scalars(
            select(RetrievalChunk)
            .where(
                RetrievalChunk.workspace_id == workspace_id,
                RetrievalChunk.entity_type == "VAULT_PAGE",
                RetrievalChunk.entity_id == document_id,
            )
            .order_by(RetrievalChunk.chunk_ordinal)
        ).all()
        hashes = [self._hash(document_id, ordinal, text) for ordinal, text in enumerate(texts, start=1)]
        changed = [
            text
            for ordinal, text in enumerate(texts, start=1)
            if ordinal > len(existing) or existing[ordinal - 1].content_hash != hashes[ordinal - 1]
        ]
        embeddings = iter(self.embedding_service.embed_texts(changed))
        now = datetime.now(UTC)
        synchronized: list[RetrievalChunk] = []
        for ordinal, text in enumerate(texts, start=1):
            content_hash = hashes[ordinal - 1]
            if ordinal <= len(existing):
                chunk = existing[ordinal - 1]
                if chunk.content_hash != content_hash:
                    chunk.text = text
                    chunk.content_hash = content_hash
                    chunk.embedding_json = json.dumps(next(embeddings), ensure_ascii=False)
                    chunk.updated_at = now
                synchronized.append(chunk)
                continue
            chunk = RetrievalChunk(
                id=f"chunk-{uuid4().hex}",
                workspace_id=workspace_id,
                entity_type="VAULT_PAGE",
                entity_id=document_id,
                chunk_ordinal=ordinal,
                text=text,
                content_hash=content_hash,
                embedding_json=json.dumps(next(embeddings), ensure_ascii=False),
                updated_at=now,
            )
            self.db.add(chunk)
            synchronized.append(chunk)
        if len(existing) > len(texts):
            self.db.execute(delete(RetrievalChunk).where(RetrievalChunk.id.in_([item.id for item in existing[len(texts) :]])))
        self.db.flush()
        return synchronized

    def remove_missing_vault_documents(self, workspace_id: str, document_ids: set[str]) -> None:
        statement = delete(RetrievalChunk).where(
            RetrievalChunk.workspace_id == workspace_id,
            RetrievalChunk.entity_type == "VAULT_PAGE",
        )
        if document_ids:
            statement = statement.where(~RetrievalChunk.entity_id.in_(document_ids))
        self.db.execute(statement)

    @staticmethod
    def _split_text(text: str, chunk_size: int = 480) -> list[str]:
        normalized = " ".join(text.split()).strip()
        if not normalized:
            return [""]
        return [normalized[index : index + chunk_size] for index in range(0, len(normalized), chunk_size)]

    @staticmethod
    def _hash(document_id: str, ordinal: int, text: str) -> str:
        return hashlib.sha256(f"VAULT_PAGE|{document_id}|{ordinal}|{text}".encode("utf-8")).hexdigest()
