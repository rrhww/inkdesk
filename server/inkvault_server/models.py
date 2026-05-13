from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from inkvault_server.db import Base


topic_sources_table = Table(
    "topic_sources",
    Base.metadata,
    Column("topic_id", String(64), ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
    Column("source_id", String(64), ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    workspaces: Mapped[list["Workspace"]] = relationship(back_populates="owner_user")


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    owner_user: Mapped[User] = relationship(back_populates="workspaces")
    content_nodes: Mapped[list["ContentNode"]] = relationship(back_populates="workspace")
    sources: Mapped[list["Source"]] = relationship(back_populates="workspace")
    topics: Mapped[list["Topic"]] = relationship(back_populates="workspace")


class ContentNode(Base):
    __tablename__ = "content_nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.id"), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("content_nodes.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    workspace: Mapped[Workspace] = relationship(back_populates="content_nodes")
    parent: Mapped["ContentNode | None"] = relationship(remote_side=[id])
    note_document: Mapped["NoteDocument | None"] = relationship(back_populates="note", uselist=False, cascade="all, delete-orphan")


class NoteDocument(Base):
    __tablename__ = "note_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    note_id: Mapped[str] = mapped_column(String(64), ForeignKey("content_nodes.id", ondelete="CASCADE"), unique=True, nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    note: Mapped[ContentNode] = relationship(back_populates="note_document")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    legacy_note_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("content_nodes.id", ondelete="SET NULL"), unique=True, nullable=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    locator: Mapped[str | None] = mapped_column(String(500), nullable=True)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    vault_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    workspace: Mapped[Workspace] = relationship(back_populates="sources")
    legacy_note: Mapped[ContentNode | None] = relationship()
    topics: Mapped[list["Topic"]] = relationship(secondary=topic_sources_table, back_populates="sources")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    current_understanding: Mapped[str] = mapped_column(Text, nullable=False)
    open_questions: Mapped[str] = mapped_column(Text, nullable=False)
    vault_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    workspace: Mapped[Workspace] = relationship(back_populates="topics")
    sources: Mapped[list[Source]] = relationship(secondary=topic_sources_table, back_populates="topics")
    claims: Mapped[list["TopicClaim"]] = relationship(back_populates="topic", cascade="all, delete-orphan")
    thread_entries: Mapped[list["TopicThreadEntry"]] = relationship(back_populates="topic", cascade="all, delete-orphan")


class TopicClaim(Base):
    __tablename__ = "topic_claims"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    topic_id: Mapped[str] = mapped_column(String(64), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    citation_label: Mapped[str] = mapped_column(String(240), nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provenance_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unsupported")
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    topic: Mapped[Topic] = relationship(back_populates="claims")
    source: Mapped[Source | None] = relationship()


class TopicThreadEntry(Base):
    __tablename__ = "topic_thread_entries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    topic_id: Mapped[str] = mapped_column(String(64), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    topic: Mapped[Topic] = relationship(back_populates="thread_entries")
    source: Mapped[Source | None] = relationship()


class ReviewItem(Base):
    __tablename__ = "review_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    target_topic_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    proposal_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_topic_title: Mapped[str | None] = mapped_column(String(240), nullable=True)
    proposed_understanding: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_open_questions: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_claim: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_vault_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    proposal_payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workspace: Mapped[Workspace] = relationship()
    source: Mapped[Source | None] = relationship()
    target_topic: Mapped[Topic | None] = relationship()


class RetrievalChunk(Base):
    __tablename__ = "retrieval_chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    workspace: Mapped[Workspace] = relationship()


class AskTurn(Base):
    __tablename__ = "ask_turns"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    topic_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    parent_ask_turn_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("ask_turns.id", ondelete="SET NULL"), nullable=True
    )
    thread_root_ask_turn_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("ask_turns.id", ondelete="SET NULL"), nullable=True
    )
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="vault")
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    retrieval_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="lexical_fallback")
    used_wiki_ids: Mapped[str] = mapped_column(Text, nullable=False, default="")
    used_source_ids: Mapped[str] = mapped_column(Text, nullable=False, default="")
    used_chunk_ids: Mapped[str] = mapped_column(Text, nullable=False, default="")
    used_web_sources_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    knowledge_gaps_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    follow_up_questions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    can_writeback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    writeback_package_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    judgment_payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    citation_source_ids: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    workspace: Mapped[Workspace] = relationship()
    topic: Mapped[Topic | None] = relationship()
