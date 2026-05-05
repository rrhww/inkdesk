from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from inkvault_server.agents import AskContextTurnModel, AskWritebackPackageModel, AgentRuntime, AskRequestModel, CitationModel, CompileRequestModel, SourceModel, TopicModel, WebCitationModel
from inkvault_server.core.config import Settings
from inkvault_server.embeddings import EmbeddingService
from inkvault_server.importers import ImportedRawMaterial, PdfRawImportService, WebRawImportService
from inkvault_server.models import AskTurn, ContentNode, NoteDocument, ReviewItem, RetrievalChunk, Source, Topic, TopicClaim, TopicThreadEntry, User, Workspace
from inkvault_server.retrieval import RetrievalSelection, RetrievalService, RetrievedCitation
from inkvault_server.schemas import (
    AskCitationResponse,
    AskRequest,
    AskResponse,
    AskThreadResponse,
    ProposalClaimResponse,
    ProposalEvidenceResponse,
    ProposalPayloadResponse,
    ProposalTopicDecisionResponse,
    ResearchDashboardResponse,
    ResearchDashboardSummary,
    ReviewDecisionResponse,
    ReviewItemResponse,
    SourceResponse,
    TopicClaimResponse,
    TopicDetailResponse,
    TopicSourceLinkResponse,
    TopicSummaryResponse,
    TopicThreadEntryResponse,
)
from inkvault_server.security import ResourceNotFoundError
from inkvault_server.time_utils import ensure_utc_datetime
from inkvault_server.vault import LIST_DELIMITER, VaultMarkdownService, VaultService


DEFAULT_WORKSPACE_SLUG = "inkvault"


@dataclass
class ResearchWorkspaceService:
    db: Session
    settings: Settings
    agent_runtime: AgentRuntime
    embedding_service: EmbeddingService
    retrieval_service: RetrievalService
    vault_service: VaultService
    vault_markdown_service: VaultMarkdownService
    web_import_service: WebRawImportService
    pdf_import_service: PdfRawImportService

    def bootstrap_seed_data(self) -> None:
        if self.db.scalar(select(func.count(User.id))) > 0:
            return
        now = datetime.fromisoformat("2026-04-12T08:00:00+00:00")
        owner = User(
            id="user-owner",
            username="owner",
            email="owner@inkvault.local",
            password_hash="$2a$10$LPDn2kRc8QEv/eTF8R30Hu9.NxWX600YSCWveNEp.5fKhYaylubji",
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
        workspace = Workspace(
            id="workspace-inkvault",
            owner_user=owner,
            name="Inkvault",
            slug=DEFAULT_WORKSPACE_SLUG,
            created_at=now,
            updated_at=now,
        )
        folder_product = self._build_folder("folder-product-reframe", workspace, "产品重定位", 100, now)
        folder_system = self._build_folder("folder-system-structure", workspace, "raw 与 wiki 结构", 200, now)
        folder_review = self._build_folder("folder-public-design", workspace, "ingest 与迁移", 300, now)
        note1 = self._build_note(
            "note-001",
            workspace,
            folder_product,
            "将 Inkvault 重定位为私有研究型 LLM Wiki",
            110,
            datetime.fromisoformat("2026-04-12T08:10:00+00:00"),
            "把产品中心收回到 raw / ingest / wiki，让来源导入、AI 编译和人工审阅形成闭环。",
            "# 将 Inkvault 重定位为私有研究型 LLM Wiki\n\n新的 Inkvault 不再强调个人操作系统或公开发布站，而是一个单人、私有、研究优先的知识编译空间。\n\n系统的核心工作是导入网页、PDF 与旧笔记，把这些材料先保存为 raw，再通过 ingest 转成可审阅的 wiki 记忆，而不是继续扩张旧的计划与发布流。",
            980,
        )
        note2 = self._build_note(
            "note-002",
            workspace,
            folder_system,
            "为什么 Today Vault Panel 应成为登录后的第一屏",
            210,
            datetime.fromisoformat("2026-04-12T07:42:00+00:00"),
            "登录后的首页应首先呈现 raw、ingest 提案和活跃 wiki，而不是旧式导航汇总。",
            "# 为什么 Today Vault Panel 应成为登录后的第一屏\n\n如果首页先看到的只是旧笔记列表，系统会再次退化成存储工具。\n\nToday Vault Panel 的作用，是先把 raw、ingest、wiki 与 Ask 组合成一块研究驾驶舱，让主人一进来就知道该读什么、审什么、追问什么。",
            820,
        )
        note3 = self._build_note(
            "note-003",
            workspace,
            folder_review,
            "审阅队列如何保证 AI 编译可控",
            310,
            datetime.fromisoformat("2026-04-12T06:58:00+00:00"),
            "AI 可以提出 wiki 创建或补丁建议，但所有编译后的知识都必须先经过人工确认。",
            "# 审阅队列如何保证 AI 编译可控\n\nVault-first 版本里，AI 不应该静默改写 wiki 内容。\n\n更合理的做法是把每次 raw 导入后的理解整理成 ingest 提案，让人决定是创建新 wiki、补充现有 wiki，还是直接驳回。",
            700,
        )
        self.db.add_all([owner, workspace, folder_product, folder_system, folder_review, note1, note2, note3])
        self.db.commit()

    def get_dashboard(self) -> ResearchDashboardResponse:
        self.ensure_research_seed_state()
        topics = self._topics()
        pending_reviews = self._pending_reviews()
        sources = self._sources()
        raw_sources = sum(1 for source in sources if self.is_raw_waiting_for_ingest(source))
        focus_topic = self.to_topic_summary(topics[0]) if topics else None
        return ResearchDashboardResponse(
            summary=ResearchDashboardSummary(
                activeTopics=len(topics),
                pendingReviews=len(pending_reviews),
                inboxSources=raw_sources,
                totalSources=len(sources),
            ),
            focusTopic=focus_topic,
            recentSources=[self.to_source_response(source) for source in sources[:3]],
            pendingReviews=[self.to_review_response(review) for review in pending_reviews[:3]],
            suggestedQuestions=self.build_suggested_questions(topics, pending_reviews, sources),
        )

    def get_retrieval_health(self) -> dict[str, object]:
        return self.retrieval_service.health()

    def get_topics(self) -> list[TopicSummaryResponse]:
        self.ensure_research_seed_state()
        return [self.to_topic_summary(topic) for topic in self._topics()]

    def get_topic(self, topic_id: str) -> TopicDetailResponse:
        self.ensure_research_seed_state()
        topic = self.db.scalar(
            select(Topic)
            .where(Topic.id == topic_id, Topic.workspace.has(slug=DEFAULT_WORKSPACE_SLUG))
            .options(selectinload(Topic.sources), selectinload(Topic.claims), selectinload(Topic.thread_entries))
        )
        if not topic:
            raise ResourceNotFoundError(f"Topic not found: {topic_id}")
        return self.to_topic_detail(topic)

    def get_sources(self) -> list[SourceResponse]:
        self.ensure_research_seed_state()
        return [self.to_source_response(source) for source in self._sources()]

    def create_source(self, kind: str, title: str | None, locator: str | None, excerpt: str | None, body: str | None) -> SourceResponse:
        self.ensure_research_seed_state()
        material = ImportedRawMaterial(
            kind=kind or "TEXT",
            title=self.blank_to_fallback(title, "未命名来源"),
            locator=self.blank_to_none(locator),
            excerpt=self.blank_to_fallback(excerpt, self.first_sentence(body or "")),
            body=self.blank_to_fallback(body, excerpt or ""),
        )
        return self.create_imported_source(material)

    def import_web_source(self, url: str, title: str | None) -> SourceResponse:
        self.ensure_research_seed_state()
        return self.create_imported_source(self.web_import_service.import_from_url(url, title))

    def import_pdf_source(self, file, title: str | None, locator: str | None) -> SourceResponse:
        self.ensure_research_seed_state()
        return self.create_imported_source(self.pdf_import_service.import_pdf(file, title, locator))

    def get_review_items(self) -> list[ReviewItemResponse]:
        self.ensure_research_seed_state()
        return [self.to_review_response(review) for review in self._pending_reviews()]

    def get_review_item(self, review_id: str) -> ReviewItemResponse:
        self.ensure_research_seed_state()
        review = self.db.scalar(
            select(ReviewItem)
            .where(ReviewItem.id == review_id)
            .options(
                selectinload(ReviewItem.source),
                selectinload(ReviewItem.target_topic),
            )
        )
        if not review:
            raise ResourceNotFoundError(f"Review item not found: {review_id}")
        return self.to_review_response(review)

    def accept_review(self, review_id: str) -> ReviewDecisionResponse:
        self.ensure_research_seed_state()
        review = self.require_pending_review(review_id)
        now = datetime.now(UTC)
        topic = self.create_topic_from_review(review, now) if review.kind == "TOPIC_CREATE" else self.apply_patch_review(review, now)
        review.status = "ACCEPTED"
        review.decided_at = now
        if review.source:
            review.source.status = "WIKI_LINKED"
            review.source.updated_at = now
        self.db.add(review)
        self.db.commit()
        return ReviewDecisionResponse(reviewId=review.id, status=review.status, topicId=topic.id)

    def reject_review(self, review_id: str) -> ReviewDecisionResponse:
        self.ensure_research_seed_state()
        review = self.require_pending_review(review_id)
        review.status = "REJECTED"
        review.decided_at = datetime.now(UTC)
        self.db.add(review)
        self.db.commit()
        return ReviewDecisionResponse(reviewId=review.id, status=review.status, topicId=review.target_topic.id if review.target_topic else None)

    def ask(self, request: AskRequest) -> AskResponse:
        self.ensure_research_seed_state()
        now = datetime.now(UTC)
        workspace = self.require_workspace()
        question = self.blank_to_fallback(request.question, "现在有什么值得继续追问的内容？")
        mode = self.blank_to_fallback(request.mode, "vault").lower()
        continued_from = None
        continued_lineage: list[AskTurn] = []
        if self.blank_to_none(request.continueFromAskTurnId):
            continued_from = self.db.scalar(
                select(AskTurn).where(
                    AskTurn.id == request.continueFromAskTurnId,
                    AskTurn.workspace_id == workspace.id,
                )
            )
            if not continued_from:
                raise ResourceNotFoundError(f"Ask turn not found: {request.continueFromAskTurnId}")
            continued_lineage = self.build_ask_lineage(continued_from)
        topic = None
        if self.blank_to_none(request.topicId):
            topic = self.db.scalar(
                select(Topic)
                .where(Topic.id == request.topicId, Topic.workspace_id == workspace.id)
                .options(selectinload(Topic.sources), selectinload(Topic.claims), selectinload(Topic.thread_entries))
            )
            if not topic:
                raise ResourceNotFoundError(f"Topic not found: {request.topicId}")
        self.ensure_compatible_ask_scope(continued_from, topic)
        topics = self._topics()
        sources = self._sources()
        pending_review_count = len(self._pending_reviews())
        context_turns = self.build_ask_context_turns(continued_from, continued_lineage)
        retrieval = self.retrieval_service.select_for_ask(
            workspace_id=workspace.id,
            question=question,
            topic=topic,
            context_turns=context_turns,
            topics=topics,
            sources=sources,
        )
        candidate_citations = retrieval.citations
        draft = self.agent_runtime.answer(
            AskRequestModel(
                question=question,
                mode=mode,
                pendingReviewCount=pending_review_count,
                topic=self.to_agent_topic(topic) if topic else None,
                citations=[self.to_agent_citation(citation) for citation in candidate_citations],
                contextTurns=context_turns,
                continueFromAskTurnId=continued_from.id if continued_from else None,
            )
        )
        citations = self.map_citations_by_id(candidate_citations, draft.citationSourceIds) or candidate_citations
        used_wiki_ids = self.dedupe_ids(([topic.id] if topic else []) + [citation.topic_id for citation in citations if citation.topic_id])
        used_source_ids = self.dedupe_ids([citation.source_id for citation in citations if citation.source_id])
        used_chunk_ids = [citation.chunk_id for citation in citations]
        used_web_sources = draft.usedWebSources
        used_web_source_payloads = [item.model_dump() if hasattr(item, "model_dump") else item for item in used_web_sources]
        context_ask_turn_ids = self.normalize_context_ask_turn_ids(context_turns, draft.contextAskTurnIds)
        can_writeback = draft.canWriteback
        if topic:
            self.append_thread_entry(topic, None, "USER", question, now)
            self.append_thread_entry(topic, self.resolve_thread_source(citations), "ASSISTANT", draft.answer, now)
            topic.updated_at = now
            self.db.add(topic)
        ask_turn_id = self.new_id("ask")
        thread_root_ask_turn_id = continued_lineage[0].id if continued_lineage else ask_turn_id
        ask_turn = AskTurn(
            id=ask_turn_id,
            workspace=workspace,
            topic=topic,
            parent_ask_turn_id=continued_from.id if continued_from else None,
            thread_root_ask_turn_id=thread_root_ask_turn_id,
            mode=mode,
            question=question,
            answer=draft.answer,
            confidence=draft.confidence,
            retrieval_mode=retrieval.retrieval_mode,
            used_wiki_ids=self.join_csv(used_wiki_ids),
            used_source_ids=self.join_csv(used_source_ids),
            used_chunk_ids=self.join_csv(used_chunk_ids),
            used_web_sources_json=self.encode_json_payload(used_web_source_payloads),
            knowledge_gaps_json=self.encode_json_payload(draft.knowledgeGaps),
            follow_up_questions_json=self.encode_json_payload(draft.followUpQuestions),
            can_writeback=can_writeback,
            writeback_package_json=self.encode_json_payload(draft.writebackPackage.model_dump() if draft.writebackPackage else {}),
            citation_source_ids=self.join_csv(used_source_ids),
            created_at=now,
        )
        self.db.add(ask_turn)
        self.db.commit()
        lineage_ask_turn_ids = [turn.id for turn in continued_lineage] + [ask_turn.id]
        return self.to_ask_response(
            ask_turn,
            citations=citations,
            context_ask_turn_ids=context_ask_turn_ids,
            lineage_ask_turn_ids=lineage_ask_turn_ids,
        )

    def get_ask_turn(self, ask_turn_id: str) -> AskResponse:
        self.ensure_research_seed_state()
        ask_turn = self.require_ask_turn(ask_turn_id)
        return self.to_ask_response(ask_turn)

    def get_ask_thread(self, ask_turn_id: str) -> AskThreadResponse:
        self.ensure_research_seed_state()
        ask_turn = self.require_ask_turn(ask_turn_id)
        lineage = self.build_ask_lineage(ask_turn)
        return AskThreadResponse(
            rootAskTurnId=lineage[0].id if lineage else ask_turn.id,
            currentAskTurnId=ask_turn.id,
            topicId=ask_turn.topic_id,
            turns=[self.to_ask_response(turn, lineage_ask_turn_ids=[item.id for item in lineage[: index + 1]]) for index, turn in enumerate(lineage)],
        )

    def create_ask_writeback_proposal(self, ask_turn_id: str) -> ReviewItemResponse:
        self.ensure_research_seed_state()
        now = datetime.now(UTC)
        ask_turn = self.db.scalar(select(AskTurn).where(AskTurn.id == ask_turn_id).options(selectinload(AskTurn.topic)))
        if not ask_turn:
            raise ResourceNotFoundError(f"Ask turn not found: {ask_turn_id}")
        package = self.decode_writeback_package(ask_turn.writeback_package_json)
        materialized_sources = self.materialize_writeback_sources(ask_turn, now)
        available_sources = self._sources()
        citations = self.resolve_citation_sources(ask_turn.citation_source_ids, available_sources)
        materialized_source_ids = {source.id for source in materialized_sources}
        supporting_sources = materialized_sources + [source for source in citations if source.id not in materialized_source_ids]
        primary_source = supporting_sources[0] if supporting_sources else None
        target_topic = ask_turn.topic
        if package and package.targetTopicId:
            requested_topic = self.db.scalar(select(Topic).where(Topic.id == package.targetTopicId))
            target_topic = requested_topic or target_topic
        if package and package.topicDecision == "CREATE":
            target_topic = None
        if package is None and target_topic is None and primary_source is not None:
            target_topic = self.find_matching_topic(primary_source, self._topics())
        proposed_topic_title = (
            package.proposedTopicTitle
            if package and package.proposedTopicTitle
            else (None if target_topic else self.derive_ask_writeback_topic_title(ask_turn, primary_source))
        )
        proposed_vault_path = target_topic.vault_path if target_topic and target_topic.vault_path else self.vault_service.wiki_path_for_slug(self.slugify(proposed_topic_title or "topic"))
        proposal_understanding = package.proposedUnderstanding if package else ask_turn.answer
        proposal_claim = package.proposedClaim if package else self.first_sentence(ask_turn.answer)
        proposal_open_question = package.proposedOpenQuestion if package else self.derive_ask_writeback_open_question(ask_turn)
        proposal_hash = self.vault_service.content_hash(
            f"ask-writeback|{ask_turn.id}|{proposed_vault_path}|{proposal_understanding}|{','.join(source.id for source in materialized_sources)}"
        )
        existing = self.db.scalar(select(ReviewItem).where(ReviewItem.content_hash == proposal_hash, ReviewItem.status == "PENDING"))
        if existing:
            return self.to_review_response(existing)
        review = ReviewItem(
            id=self.new_id("review"),
            workspace=ask_turn.workspace,
            source=primary_source,
            target_topic=target_topic,
            kind="TOPIC_CREATE" if target_topic is None else "TOPIC_PATCH",
            proposal_kind="TOPIC_CREATE" if target_topic is None else "TOPIC_PATCH",
            status="PENDING",
            title="从 Ask 回答建立 wiki 页面" if target_topic is None else "把 Ask 结论补充进现有 wiki",
            summary=self.build_ask_writeback_summary(ask_turn, target_topic, proposed_topic_title),
            proposed_topic_title=proposed_topic_title,
            proposed_understanding=proposal_understanding,
            proposed_open_questions=proposal_open_question,
            proposed_claim=proposal_claim,
            proposed_vault_path=proposed_vault_path,
            content_hash=proposal_hash,
            created_at=now,
        )
        self.db.add(review)
        self.db.commit()
        return self.to_review_response(review)

    def ensure_research_seed_state(self) -> None:
        self.bootstrap_seed_data()
        self.vault_service.ensure_initialized()
        self.import_legacy_notes_as_sources()
        topics = self._topics()
        for source in self._sources():
            if not source.vault_path or not source.content_hash:
                self.persist_raw_file(source, source.created_at)
                self.db.add(source)
            if self.is_raw_waiting_for_ingest(source):
                self.ensure_review_for_source(source, topics)
        self.db.commit()

    def import_legacy_notes_as_sources(self) -> None:
        workspace = self.require_workspace()
        notes = self.db.scalars(
            select(ContentNode)
            .where(ContentNode.workspace_id == workspace.id, ContentNode.type == "NOTE")
            .options(selectinload(ContentNode.note_document))
            .order_by(ContentNode.updated_at.desc())
        ).all()
        existing_legacy_ids = {value for value in self.db.scalars(select(Source.legacy_note_id)).all() if value}
        for note in notes:
            if note.id in existing_legacy_ids:
                continue
            source = Source(
                id=self.new_id("source"),
                workspace=workspace,
                legacy_note=note,
                kind="LEGACY_NOTE",
                status="INGEST_PENDING",
                title=note.title,
                locator=f"legacy-note://{note.id}",
                excerpt=self.blank_to_fallback(note.note_document.excerpt if note.note_document else None, self.first_sentence(note.note_document.markdown_content if note.note_document else "")),
                body=self.blank_to_fallback(note.note_document.markdown_content if note.note_document else None, note.title),
                created_at=note.updated_at,
                updated_at=note.updated_at,
            )
            self.persist_raw_file(source, source.created_at)
            self.db.add(source)
        self.db.flush()

    def create_imported_source(self, material: ImportedRawMaterial) -> SourceResponse:
        now = datetime.now(UTC)
        source = self._create_source_from_material(material, now)
        self.ensure_review_for_source(source)
        self.db.commit()
        return self.to_source_response(source)

    def _create_source_from_material(self, material: ImportedRawMaterial, now: datetime) -> Source:
        workspace = self.require_workspace()
        source = Source(
            id=self.new_id("source"),
            workspace=workspace,
            legacy_note=None,
            kind=material.kind,
            status="INGEST_PENDING",
            title=self.blank_to_fallback(material.title, "未命名来源"),
            locator=self.blank_to_none(material.locator),
            excerpt=self.blank_to_fallback(material.excerpt, self.first_sentence(material.body)),
            body=self.blank_to_fallback(material.body, material.excerpt),
            created_at=now,
            updated_at=now,
        )
        self.persist_raw_file(source, now)
        self.db.add(source)
        self.db.flush()
        self.retrieval_service.sync_source(source)
        return source

    def ensure_review_for_source(self, source: Source, topics: list[Topic] | None = None) -> None:
        available_topics = topics or self._topics()
        available_sources = self._sources()
        matched_topic = self.find_matching_topic(source, available_topics)
        compile_context = self.retrieval_service.select_for_compile(
            workspace_id=source.workspace_id,
            source=source,
            matched_topic=matched_topic,
            topics=available_topics,
            sources=available_sources,
        )
        proposed_vault_path = matched_topic.vault_path if matched_topic and matched_topic.vault_path else self.vault_service.wiki_path_for_slug(self.slugify(matched_topic.title if matched_topic else source.title))
        content_hash = self.vault_service.content_hash(f"{source.id}|{proposed_vault_path}|{source.content_hash}")
        existing = self.db.scalar(select(ReviewItem).where(ReviewItem.content_hash == content_hash, ReviewItem.status == "PENDING"))
        if existing:
            return
        draft = self.agent_runtime.compile(
            CompileRequestModel(
                source=self.to_agent_source(source),
                matchedTopic=self.to_agent_topic(matched_topic) if matched_topic else None,
                citations=[self.to_agent_citation(citation) for citation in compile_context.citations],
            )
        )
        proposal_payload = self.build_compile_proposal_payload(
            draft=draft,
            matched_topic=matched_topic,
            source=source,
            compile_context=compile_context.citations,
        )
        review = ReviewItem(
            id=self.new_id("review"),
            workspace=source.workspace,
            source=source,
            target_topic=matched_topic,
            kind="TOPIC_CREATE" if draft.kind == "TOPIC_CREATE" else "TOPIC_PATCH",
            proposal_kind=draft.kind,
            status="PENDING",
            title=self.blank_to_fallback(draft.title, "从 raw 建立 wiki 页面"),
            summary=self.blank_to_fallback(draft.summary, source.excerpt),
            proposed_topic_title=draft.proposedTopicTitle,
            proposed_understanding=draft.proposedUnderstanding,
            proposed_open_questions=draft.proposedOpenQuestions,
            proposed_claim=draft.proposedClaim,
            proposed_vault_path=proposed_vault_path,
            proposal_payload_json=self.encode_json_payload(proposal_payload.model_dump()),
            content_hash=content_hash,
            created_at=source.updated_at,
        )
        self.db.add(review)

    def create_topic_from_review(self, review: ReviewItem, now: datetime) -> Topic:
        proposal_payload = self.to_proposal_payload(review)
        topic_title = self.blank_to_fallback(
            proposal_payload.topicDecision.proposedTopicTitle or review.proposed_topic_title,
            review.source.title if review.source else "未命名主题",
        )
        topic = Topic(
            id=self.new_id("topic"),
            workspace=review.workspace,
            title=topic_title,
            slug=self.unique_slugify(topic_title),
            summary=self.review_summary_value(review, proposal_payload, review.summary),
            current_understanding=self.join_segments(
                self.proposal_segments(
                    proposal_payload.summaryChanges,
                    self.blank_to_fallback(review.proposed_understanding, review.summary),
                )
            ),
            open_questions=self.join_segments(
                self.proposal_segments(
                    proposal_payload.openQuestions,
                    self.blank_to_fallback(review.proposed_open_questions, "接下来应该继续验证什么？"),
                )
            ),
            vault_path=self.blank_to_fallback(review.proposed_vault_path, self.vault_service.wiki_path_for_slug("topic")),
            created_at=now,
            updated_at=now,
        )
        self.attach_review_sources(topic, review, proposal_payload)
        self.db.add(topic)
        self.db.flush()
        self.apply_review_claims(topic, review, proposal_payload, now)
        self.append_thread_entry(topic, review.source, "SYSTEM", "已从来源建立研究主题。", now)
        self.persist_wiki_page(topic)
        self.retrieval_service.sync_topic(topic)
        return topic

    def apply_patch_review(self, review: ReviewItem, now: datetime) -> Topic:
        topic = review.target_topic
        if not topic:
            raise ResourceNotFoundError(f"Target topic not found for review {review.id}")
        proposal_payload = self.to_proposal_payload(review)
        self.attach_review_sources(topic, review, proposal_payload)
        topic.current_understanding = self.append_unique_segments(topic.current_understanding, proposal_payload.summaryChanges)
        if topic.current_understanding == "":
            topic.current_understanding = self.append_unique_segment(topic.current_understanding, review.proposed_understanding)
        topic.open_questions = self.append_unique_segments(topic.open_questions, proposal_payload.openQuestions)
        if topic.open_questions == "":
            topic.open_questions = self.append_unique_segment(topic.open_questions, review.proposed_open_questions)
        topic.summary = self.review_summary_value(review, proposal_payload, topic.summary)
        topic.updated_at = now
        if not topic.vault_path:
            topic.vault_path = self.blank_to_fallback(review.proposed_vault_path, self.vault_service.wiki_path_for_slug(topic.slug))
        self.db.add(topic)
        self.db.flush()
        self.apply_review_claims(topic, review, proposal_payload, now)
        self.append_thread_entry(topic, review.source, "ASSISTANT", "已把新来源编译进当前主题。", now)
        self.persist_wiki_page(topic)
        self.retrieval_service.sync_topic(topic)
        return topic

    def attach_review_sources(self, topic: Topic, review: ReviewItem, proposal_payload: ProposalPayloadResponse) -> None:
        for source in self.review_supporting_sources(review, proposal_payload):
            if source not in topic.sources:
                topic.sources.append(source)

    def review_supporting_sources(self, review: ReviewItem, proposal_payload: ProposalPayloadResponse) -> list[Source]:
        preferred_sources = [review.source] if review.source else []
        candidate_source_ids = self.dedupe_ids(
            [claim.sourceId for claim in proposal_payload.claims]
        )
        source_by_id = {source.id: source for source in self._sources()}
        supporting_sources: list[Source] = [source for source in preferred_sources if source is not None]
        for source_id in candidate_source_ids:
            source = source_by_id.get(source_id)
            if source is not None and source not in supporting_sources:
                supporting_sources.append(source)
        return supporting_sources

    def apply_review_claims(self, topic: Topic, review: ReviewItem, proposal_payload: ProposalPayloadResponse, now: datetime) -> None:
        claim_candidates = proposal_payload.claims or [
            ProposalClaimResponse(
                statement=self.blank_to_fallback(review.proposed_claim, self.first_sentence(topic.summary)),
                citationLabel=review.source.title if review.source else review.title,
                sourceId=review.source.id if review.source else None,
                citationChunkIds=[],
            )
        ]
        existing_statements = {
            claim.statement.strip()
            for claim in topic.claims
            if claim.statement and claim.statement.strip()
        }
        evidence_by_chunk_id = {
            evidence.chunkId: evidence
            for evidence in proposal_payload.evidence
            if evidence.chunkId
        }
        supporting_sources = self.review_supporting_sources(review, proposal_payload)
        source_by_id = {source.id: source for source in supporting_sources}
        fallback_source = review.source or (supporting_sources[0] if supporting_sources else None)
        for claim in claim_candidates:
            statement = self.blank_to_none(claim.statement)
            if not statement or statement in existing_statements:
                continue
            source = self.resolve_review_claim_source(claim, evidence_by_chunk_id, source_by_id, fallback_source)
            citation_label = self.blank_to_fallback(claim.citationLabel, source.title if source else "主题摘要")
            self.append_claim(topic, source, statement, now, citation_label=citation_label)
            existing_statements.add(statement)

    def resolve_review_claim_source(
        self,
        claim: ProposalClaimResponse,
        evidence_by_chunk_id: dict[str, ProposalEvidenceResponse],
        source_by_id: dict[str, Source],
        fallback_source: Source | None,
    ) -> Source | None:
        if claim.sourceId and claim.sourceId in source_by_id:
            return source_by_id[claim.sourceId]
        for chunk_id in claim.citationChunkIds:
            evidence = evidence_by_chunk_id.get(chunk_id)
            if evidence and evidence.sourceId in source_by_id:
                return source_by_id[evidence.sourceId]
        return fallback_source

    def append_claim(self, topic: Topic, source: Source | None, statement: str, now: datetime, citation_label: str | None = None) -> None:
        claim = TopicClaim(
            id=self.new_id("claim"),
            topic=topic,
            source=source,
            statement=self.blank_to_fallback(statement, topic.summary),
            citation_label=self.blank_to_fallback(citation_label, source.title if source else "主题摘要"),
            sort_order=len(topic.claims) + 1,
            created_at=now,
        )
        self.db.add(claim)

    def append_thread_entry(self, topic: Topic, source: Source | None, role: str, content: str, now: datetime) -> None:
        entry = TopicThreadEntry(
            id=self.new_id("thread"),
            topic=topic,
            source=source,
            role=role,
            content=content,
            sort_order=len(topic.thread_entries) + 1,
            created_at=now,
        )
        self.db.add(entry)

    def persist_raw_file(self, source: Source, imported_at: datetime) -> None:
        result = self.vault_service.write_raw_source(imported_at, source.title, source.id, self.vault_markdown_service.render_raw_source(source, imported_at))
        source.vault_path = result.relative_path
        source.content_hash = result.content_hash

    def persist_wiki_page(self, topic: Topic) -> None:
        claims = list(sorted(topic.claims, key=lambda item: item.sort_order))
        result = self.vault_service.write_vault_file(topic.vault_path or self.vault_service.wiki_path_for_slug(topic.slug), self.vault_markdown_service.render_wiki_topic(topic, claims))
        topic.vault_path = result.relative_path
        topic.content_hash = result.content_hash
        self.db.add(topic)

    def to_topic_summary(self, topic: Topic) -> TopicSummaryResponse:
        return TopicSummaryResponse(
            id=topic.id,
            title=topic.title,
            summary=topic.summary,
            sourceCount=len(topic.sources),
            openQuestionCount=len(self.split_segments(topic.open_questions)),
            vaultPath=topic.vault_path,
            updatedAt=topic.updated_at,
        )

    def to_topic_detail(self, topic: Topic) -> TopicDetailResponse:
        claims = sorted(topic.claims, key=lambda item: item.sort_order)
        thread = sorted(topic.thread_entries, key=lambda item: item.sort_order)
        sources = sorted(topic.sources, key=lambda item: ensure_utc_datetime(item.updated_at), reverse=True)
        return TopicDetailResponse(
            id=topic.id,
            title=topic.title,
            summary=topic.summary,
            vaultPath=topic.vault_path,
            contentHash=topic.content_hash,
            currentUnderstanding=self.split_segments(topic.current_understanding),
            openQuestions=self.split_segments(topic.open_questions),
            sources=[
                TopicSourceLinkResponse(
                    sourceId=source.id,
                    title=source.title,
                    kind=source.kind,
                    locator=source.locator,
                    vaultPath=source.vault_path,
                    legacyNoteId=source.legacy_note_id,
                )
                for source in sources
            ],
            keyClaims=[
                TopicClaimResponse(
                    id=claim.id,
                    statement=claim.statement,
                    sourceId=claim.source_id,
                    citationLabel=claim.citation_label,
                )
                for claim in claims
            ],
            thread=[
                TopicThreadEntryResponse(
                    id=entry.id,
                    role=entry.role,
                    content=entry.content,
                    sourceId=entry.source_id,
                    createdAt=entry.created_at,
                )
                for entry in thread
            ],
            updatedAt=topic.updated_at,
        )

    def to_source_response(self, source: Source) -> SourceResponse:
        return SourceResponse(
            id=source.id,
            kind=source.kind,
            status=source.status,
            title=source.title,
            locator=source.locator,
            excerpt=source.excerpt,
            legacyNoteId=source.legacy_note_id,
            vaultPath=source.vault_path,
            contentHash=source.content_hash,
            updatedAt=source.updated_at,
        )

    def to_review_response(self, review: ReviewItem) -> ReviewItemResponse:
        return ReviewItemResponse(
            id=review.id,
            kind=review.kind,
            proposalKind=review.proposal_kind,
            title=review.title,
            summary=review.summary,
            sourceId=review.source.id if review.source else None,
            sourceTitle=review.source.title if review.source else None,
            targetTopicId=review.target_topic.id if review.target_topic else None,
            targetTopicTitle=review.target_topic.title if review.target_topic else None,
            proposedTopicTitle=review.proposed_topic_title,
            proposedUnderstanding=review.proposed_understanding,
            proposedOpenQuestions=review.proposed_open_questions,
            proposedClaim=review.proposed_claim,
            proposedVaultPath=review.proposed_vault_path,
            sourceVaultPath=review.source.vault_path if review.source else None,
            proposalPayload=self.to_proposal_payload(review),
            createdAt=review.created_at,
        )

    def to_proposal_payload(self, review: ReviewItem) -> ProposalPayloadResponse:
        stored_payload = self.decode_proposal_payload(review.proposal_payload_json)
        if stored_payload is not None:
            return stored_payload
        decision = "PATCH" if review.kind == "TOPIC_PATCH" else "CREATE"
        summary_changes = [review.proposed_understanding.strip()] if self.blank_to_none(review.proposed_understanding) else []
        claims = (
            [ProposalClaimResponse(statement=review.proposed_claim.strip(), citationLabel=review.source.title if review.source else review.title, sourceId=review.source.id if review.source else None, citationChunkIds=[])]
            if self.blank_to_none(review.proposed_claim)
            else []
        )
        open_questions = [review.proposed_open_questions.strip()] if self.blank_to_none(review.proposed_open_questions) else []
        evidence = (
            [
                ProposalEvidenceResponse(
                    sourceId=review.source.id,
                    sourceTitle=review.source.title,
                    sourceVaultPath=review.source.vault_path,
                    locator=review.source.locator,
                    excerpt=review.source.excerpt,
                    chunkId=None,
                    entityType="SOURCE",
                    entityId=review.source.id,
                    topicId=None,
                )
            ]
            if review.source
            else []
        )
        return ProposalPayloadResponse(
            topicDecision=ProposalTopicDecisionResponse(
                decision=decision,
                targetTopicId=review.target_topic.id if review.target_topic else None,
                targetTopicTitle=review.target_topic.title if review.target_topic else None,
                proposedTopicTitle=review.proposed_topic_title,
            ),
            summaryChanges=summary_changes,
            claims=claims,
            conflicts=[],
            openQuestions=open_questions,
            explanation=self.review_explanation(review),
            evidence=evidence,
        )

    def build_compile_proposal_payload(
        self,
        *,
        draft,
        matched_topic: Topic | None,
        source: Source,
        compile_context: list[RetrievedCitation],
    ) -> ProposalPayloadResponse:
        decision = "PATCH" if draft.kind == "TOPIC_PATCH" else "CREATE"
        topic_title = matched_topic.title if matched_topic else None
        citations_by_id = {citation.chunk_id: citation for citation in compile_context}
        claims = [
            ProposalClaimResponse(
                statement=claim.statement,
                citationLabel=self.proposal_claim_label(claim.citationIds, citations_by_id, source, matched_topic),
                sourceId=self.proposal_claim_source_id(claim.citationIds, citations_by_id, source),
                citationChunkIds=claim.citationIds,
            )
            for claim in draft.claims
        ]
        evidence = [
            self.to_proposal_evidence(citations_by_id[citation_id], source)
            for citation_id in draft.evidenceCitationIds
            if citation_id in citations_by_id
        ]
        if not evidence:
            evidence = [self.to_proposal_evidence(citation, source) for citation in compile_context[:2]]
        return ProposalPayloadResponse(
            topicDecision=ProposalTopicDecisionResponse(
                decision=decision,
                targetTopicId=matched_topic.id if matched_topic else None,
                targetTopicTitle=topic_title,
                proposedTopicTitle=draft.proposedTopicTitle,
            ),
            summaryChanges=draft.summaryChanges or [draft.proposedUnderstanding],
            claims=claims,
            conflicts=draft.conflicts,
            openQuestions=draft.openQuestions or [draft.proposedOpenQuestions],
            explanation=self.blank_to_fallback(draft.explanation, self.review_explanation_from_decision(decision, matched_topic)),
            evidence=evidence,
        )

    def to_proposal_evidence(self, citation: RetrievedCitation, source: Source) -> ProposalEvidenceResponse:
        return ProposalEvidenceResponse(
            sourceId=citation.source_id or source.id,
            sourceTitle=citation.title if citation.source_id else source.title,
            sourceVaultPath=citation.vault_path if citation.source_id else source.vault_path,
            locator=citation.locator if citation.source_id else source.locator,
            excerpt=citation.snippet if citation.snippet else source.excerpt,
            chunkId=citation.chunk_id,
            entityType=citation.entity_type,
            entityId=citation.entity_id,
            topicId=citation.topic_id,
        )

    def proposal_claim_label(
        self,
        citation_ids: list[str],
        citations_by_id: dict[str, RetrievedCitation],
        source: Source,
        matched_topic: Topic | None,
    ) -> str:
        if citation_ids:
            citation = citations_by_id.get(citation_ids[0])
            if citation is not None:
                return citation.title
        if matched_topic is not None:
            return matched_topic.title
        return source.title

    def proposal_claim_source_id(
        self,
        citation_ids: list[str],
        citations_by_id: dict[str, RetrievedCitation],
        source: Source,
    ) -> str | None:
        for citation_id in citation_ids:
            citation = citations_by_id.get(citation_id)
            if citation is not None and citation.source_id:
                return citation.source_id
        return source.id if source else None

    def review_explanation_from_decision(self, decision: str, matched_topic: Topic | None) -> str:
        if decision == "PATCH" and matched_topic is not None:
            return f"系统建议把这次 Ask / raw 结论补充进现有主题「{matched_topic.title}」，因为证据与当前主题最相关。"
        return "系统建议基于这份来源建立新主题，因为当前没有更合适的已有 wiki 页面承接这次结论。"

    def review_explanation(self, review: ReviewItem) -> str:
        if review.title and "Ask" in review.title:
            if review.kind == "TOPIC_PATCH" and review.target_topic:
                return f"系统建议把这次 Ask 当前回答补充进现有主题「{review.target_topic.title}」，因为当前答案已经命中了这个 wiki 页面。"
            return "系统建议基于这次 Ask 当前回答建立新主题，因为现有 wiki 里没有更合适的承接页面。"
        if review.kind == "TOPIC_PATCH" and review.target_topic:
            return f"系统建议把这次 Ask / raw 结论补充进现有主题「{review.target_topic.title}」，因为证据与当前主题最相关。"
        return "系统建议基于这份来源建立新主题，因为当前没有更合适的已有 wiki 页面承接这次结论。"

    def to_ask_response(
        self,
        ask_turn: AskTurn,
        *,
        citations: list[RetrievedCitation] | None = None,
        context_ask_turn_ids: list[str] | None = None,
        lineage_ask_turn_ids: list[str] | None = None,
    ) -> AskResponse:
        resolved_citations = citations if citations is not None else self.resolve_retrieved_citations(ask_turn.used_chunk_ids)
        lineage_ids = lineage_ask_turn_ids or [turn.id for turn in self.build_ask_lineage(ask_turn)]
        thread_root_ask_turn_id = ask_turn.thread_root_ask_turn_id or (lineage_ids[0] if lineage_ids else ask_turn.id)
        return AskResponse(
            id=ask_turn.id,
            topicId=ask_turn.topic_id,
            parentAskTurnId=ask_turn.parent_ask_turn_id,
            threadRootAskTurnId=thread_root_ask_turn_id,
            lineageAskTurnIds=lineage_ids or [ask_turn.id],
            question=ask_turn.question,
            answer=ask_turn.answer,
            confidence=ask_turn.confidence,
            retrievalMode=ask_turn.retrieval_mode,
            usedChunkIds=self.split_csv(ask_turn.used_chunk_ids),
            followUpQuestions=self.decode_json_list(ask_turn.follow_up_questions_json),
            knowledgeGaps=self.decode_json_list(ask_turn.knowledge_gaps_json),
            usedWikiIds=self.split_csv(ask_turn.used_wiki_ids),
            usedSourceIds=self.split_csv(ask_turn.used_source_ids),
            usedWebSources=[item.model_dump() for item in self.decode_web_citations(ask_turn.used_web_sources_json)],
            contextAskTurnIds=context_ask_turn_ids if context_ask_turn_ids is not None else self.context_ask_turn_ids_for_turn(ask_turn, lineage_ids),
            canWriteback=ask_turn.can_writeback,
            citations=[self.to_ask_citation(source) for source in resolved_citations],
            createdAt=ask_turn.created_at,
        )

    def to_ask_citation(self, citation: RetrievedCitation) -> AskCitationResponse:
        return AskCitationResponse(
            id=citation.chunk_id,
            entityType=citation.entity_type,
            entityId=citation.entity_id,
            sourceId=citation.source_id,
            topicId=citation.topic_id,
            title=citation.title,
            locator=citation.locator,
            vaultPath=citation.vault_path,
            snippet=citation.snippet,
            chunkId=citation.chunk_id,
        )

    def to_agent_topic(self, topic: Topic | None) -> TopicModel | None:
        if topic is None:
            return None
        return TopicModel(
            id=topic.id,
            title=topic.title,
            currentUnderstanding=self.split_segments(topic.current_understanding),
            openQuestions=self.split_segments(topic.open_questions),
            summary=topic.summary,
            vaultPath=topic.vault_path,
        )

    def to_agent_source(self, source: Source) -> SourceModel:
        return SourceModel(id=source.id, title=source.title, kind=source.kind, excerpt=source.excerpt, body=source.body, locator=source.locator, vaultPath=source.vault_path)

    def to_agent_citation(self, citation: RetrievedCitation) -> CitationModel:
        return CitationModel(
            id=citation.chunk_id,
            title=citation.title,
            kind=citation.kind,
            excerpt=citation.snippet,
            locator=citation.locator,
            vaultPath=citation.vault_path,
        )

    def map_citations_by_id(self, available_citations: list[RetrievedCitation], citation_ids: list[str]) -> list[RetrievedCitation]:
        by_id = {citation.chunk_id: citation for citation in available_citations}
        return [by_id[citation_id] for citation_id in citation_ids if citation_id in by_id]

    def resolve_retrieved_citations(self, used_chunk_ids: str) -> list[RetrievedCitation]:
        chunk_ids = self.split_csv(used_chunk_ids)
        if not chunk_ids:
            return []
        chunks = self.db.scalars(select(RetrievalChunk).where(RetrievalChunk.id.in_(chunk_ids))).all()
        chunk_by_id = {chunk.id: chunk for chunk in chunks}
        sources = {source.id: source for source in self._sources()}
        topics = {topic.id: topic for topic in self._topics()}
        resolved: list[RetrievedCitation] = []
        for chunk_id in chunk_ids:
            chunk = chunk_by_id.get(chunk_id)
            if chunk is None:
                continue
            if chunk.entity_type == "TOPIC":
                topic = topics.get(chunk.entity_id)
                if topic is None:
                    continue
                resolved.append(
                    RetrievedCitation(
                        chunk_id=chunk.id,
                        entity_type="TOPIC",
                        entity_id=topic.id,
                        source_id=None,
                        topic_id=topic.id,
                        title=topic.title,
                        kind="TOPIC",
                        locator=None,
                        vault_path=topic.vault_path,
                        snippet=chunk.text[:240],
                        score=0.0,
                    )
                )
                continue
            source = sources.get(chunk.entity_id)
            if source is None:
                continue
            resolved.append(
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
                    score=0.0,
                )
            )
        return resolved

    def resolve_citation_sources(self, citation_source_ids: str, available_sources: list[Source]) -> list[Source]:
        ids = [value.strip() for value in citation_source_ids.split(",") if value.strip()]
        by_id = {source.id: source for source in available_sources}
        return [by_id[source_id] for source_id in ids if source_id in by_id]

    def resolve_thread_source(self, citations: list[RetrievedCitation]) -> Source | None:
        source_ids = [citation.source_id for citation in citations if citation.source_id]
        if not source_ids:
            return None
        return {source.id: source for source in self._sources()}.get(source_ids[0])

    def build_ask_lineage(self, ask_turn: AskTurn | None) -> list[AskTurn]:
        if ask_turn is None:
            return []
        lineage: list[AskTurn] = []
        seen: set[str] = set()
        current: AskTurn | None = ask_turn
        while current is not None and current.id not in seen:
            lineage.append(current)
            seen.add(current.id)
            if not current.parent_ask_turn_id:
                break
            current = self.find_ask_turn(current.parent_ask_turn_id)
        lineage.reverse()
        return lineage

    def build_ask_context_turns(self, continued_from: AskTurn | None, continued_lineage: list[AskTurn] | None = None) -> list[AskContextTurnModel]:
        if continued_from is None:
            return []
        lineage = continued_lineage or self.build_ask_lineage(continued_from)
        selected_turns = lineage[-2:]
        return [
            AskContextTurnModel(
                askTurnId=turn.id,
                question=turn.question,
                answer=turn.answer,
            )
            for turn in selected_turns
        ]

    def build_topic_citations(self, topic: Topic | None) -> list[Source]:
        if topic is None:
            return []
        return sorted(topic.sources, key=lambda item: ensure_utc_datetime(item.updated_at), reverse=True)[:4]

    def build_global_citations(self, question: str) -> list[Source]:
        sources = self._sources()
        scored_sources = [
            (self.global_match_score(source, question), source)
            for source in sources
        ]
        matched_sources = [
            source
            for score, source in sorted(
                scored_sources,
                key=lambda item: (item[0], ensure_utc_datetime(item[1].updated_at)),
                reverse=True,
            )
            if score > 0
        ]
        matched_ids = {source.id for source in matched_sources}
        fallback_sources = [source for source in sources if source.id not in matched_ids]
        return (matched_sources + fallback_sources)[:4]

    def ensure_compatible_ask_scope(self, continued_from: AskTurn | None, topic: Topic | None) -> None:
        if continued_from is None:
            return
        expected_topic_id = topic.id if topic else None
        if continued_from.topic_id != expected_topic_id:
            raise ResourceNotFoundError(f"Ask turn not found for this topic scope: {continued_from.id}")

    def normalize_context_ask_turn_ids(self, context_turns: list[AskContextTurnModel], runtime_ids: list[str]) -> list[str]:
        expected_ids = [turn.askTurnId for turn in context_turns if turn.askTurnId]
        if not expected_ids:
            return []
        allowed_ids = set(expected_ids)
        normalized: list[str] = []
        seen: set[str] = set()
        for runtime_id in runtime_ids:
            if runtime_id in allowed_ids and runtime_id not in seen:
                normalized.append(runtime_id)
                seen.add(runtime_id)
        return normalized or expected_ids

    def context_ask_turn_ids_for_turn(self, ask_turn: AskTurn, lineage_ids: list[str] | None = None) -> list[str]:
        resolved_lineage_ids = lineage_ids or [turn.id for turn in self.build_ask_lineage(ask_turn)]
        if not resolved_lineage_ids or resolved_lineage_ids[-1] != ask_turn.id:
            return []
        return resolved_lineage_ids[:-1][-2:]

    def materialize_writeback_sources(self, ask_turn: AskTurn, now: datetime) -> list[Source]:
        package = self.decode_writeback_package(ask_turn.writeback_package_json)
        if package is None:
            return []
        materialized_sources: list[Source] = []
        for web_source in package.usedWebSources:
            source_hash = self.vault_service.content_hash(web_source.excerpt)
            existing = self.find_source_by_locator_and_hash(web_source.url, source_hash)
            if existing is not None:
                materialized_sources.append(existing)
                continue
            materialized_sources.append(
                self._create_source_from_material(
                    ImportedRawMaterial(
                        kind="WEB",
                        title=web_source.title,
                        locator=web_source.url,
                        excerpt=web_source.excerpt,
                        body=web_source.excerpt,
                    ),
                    now,
                )
            )
        return materialized_sources

    def find_source_by_locator_and_hash(self, locator: str | None, content_hash: str) -> Source | None:
        normalized_locator = self.blank_to_none(locator)
        if normalized_locator is None:
            return None
        for source in self._sources():
            if source.locator != normalized_locator:
                continue
            if self.vault_service.content_hash(source.excerpt) == content_hash:
                return source
        return None

    def global_match_score(self, source: Source, question: str) -> int:
        source_text = self.normalize(" ".join(filter(None, [source.title, source.excerpt, source.body])))
        if not source_text:
            return 0
        best_score = 0
        for term in self.extract_query_terms(question):
            if term in source_text:
                best_score = max(best_score, len(term))
        return best_score

    def extract_query_terms(self, question: str) -> list[str]:
        normalized_question = self.normalize(question)
        if not normalized_question:
            return []
        terms: list[str] = [normalized_question]
        seen = {normalized_question}
        minimum_length = 2 if any("\u4e00" <= char <= "\u9fff" for char in question) else 3
        maximum_length = min(6, len(normalized_question))
        for length in range(maximum_length, minimum_length - 1, -1):
            for start in range(0, len(normalized_question) - length + 1):
                term = normalized_question[start : start + length]
                if term not in seen:
                    seen.add(term)
                    terms.append(term)
        return terms

    def build_suggested_questions(self, topics: list[Topic], pending_reviews: list[ReviewItem], sources: list[Source]) -> list[str]:
        if topics:
            topic = topics[0]
            return [
                "这个主题现在最稳定的理解是什么？",
                f"围绕「{topic.title}」还缺哪条证据？",
                "下一轮最值得追问的问题是什么？",
            ]
        if pending_reviews:
            return [f"如何处理「{review.source.title if review.source else review.title}」？" for review in pending_reviews[:3]]
        return [f"围绕「{source.title}」还能推导出什么主题？" for source in sources[:3]]

    def find_matching_topic(self, source: Source, topics: list[Topic]) -> Topic | None:
        normalized_source_title = self.normalize(source.title)
        for topic in topics:
            normalized_topic_title = self.normalize(topic.title)
            if normalized_source_title in normalized_topic_title or normalized_topic_title in normalized_source_title:
                return topic
        return self.retrieval_service.match_topic_for_source(source, topics)

    def derive_ask_writeback_topic_title(self, ask_turn: AskTurn, primary_source: Source | None) -> str:
        if primary_source:
            return primary_source.title
        question = self.blank_to_fallback(ask_turn.question, "ask-topic")
        return question[:60]

    def build_ask_writeback_summary(self, ask_turn: AskTurn, target_topic: Topic | None, proposed_topic_title: str | None) -> str:
        if target_topic:
            return f"把 Ask 问题“{ask_turn.question}”的当前结论补充进主题「{target_topic.title}」。"
        return f"基于 Ask 问题“{ask_turn.question}”建立新主题「{proposed_topic_title or '新主题'}」。"

    def derive_ask_writeback_open_question(self, ask_turn: AskTurn) -> str:
        return f"围绕 Ask 问题“{ask_turn.question}”还需要补哪些来源？"

    def is_raw_waiting_for_ingest(self, source: Source) -> bool:
        return source.status in {"RAW", "INGEST_PENDING"}

    def find_ask_turn(self, ask_turn_id: str) -> AskTurn | None:
        return self.db.scalar(
            select(AskTurn)
            .where(AskTurn.id == ask_turn_id, AskTurn.workspace_id == self.require_workspace().id)
            .options(selectinload(AskTurn.topic))
        )

    def require_ask_turn(self, ask_turn_id: str) -> AskTurn:
        ask_turn = self.find_ask_turn(ask_turn_id)
        if ask_turn is None:
            raise ResourceNotFoundError(f"Ask turn not found: {ask_turn_id}")
        return ask_turn

    def require_pending_review(self, review_id: str) -> ReviewItem:
        review = self.db.scalar(select(ReviewItem).where(ReviewItem.id == review_id).options(selectinload(ReviewItem.source), selectinload(ReviewItem.target_topic)))
        if not review:
            raise ResourceNotFoundError(f"Review item not found: {review_id}")
        if review.status != "PENDING":
            raise ResourceNotFoundError(f"Review item is no longer pending: {review_id}")
        return review

    def require_workspace(self) -> Workspace:
        workspace = self.db.scalar(select(Workspace).where(Workspace.slug == DEFAULT_WORKSPACE_SLUG))
        if not workspace:
            raise ResourceNotFoundError(f"Workspace not found for slug: {DEFAULT_WORKSPACE_SLUG}")
        return workspace

    def _sources(self) -> list[Source]:
        workspace = self.require_workspace()
        return self.db.scalars(
            select(Source)
            .where(Source.workspace_id == workspace.id)
            .order_by(Source.updated_at.desc())
            .options(selectinload(Source.legacy_note))
        ).all()

    def _topics(self) -> list[Topic]:
        workspace = self.require_workspace()
        return self.db.scalars(
            select(Topic)
            .where(Topic.workspace_id == workspace.id)
            .order_by(Topic.updated_at.desc())
            .options(selectinload(Topic.sources), selectinload(Topic.claims), selectinload(Topic.thread_entries))
        ).all()

    def _pending_reviews(self) -> list[ReviewItem]:
        workspace = self.require_workspace()
        return self.db.scalars(
            select(ReviewItem)
            .where(ReviewItem.workspace_id == workspace.id, ReviewItem.status == "PENDING")
            .order_by(ReviewItem.created_at.desc())
            .options(selectinload(ReviewItem.source), selectinload(ReviewItem.target_topic))
        ).all()

    def _build_folder(self, node_id: str, workspace: Workspace, title: str, sort_order: int, updated_at: datetime) -> ContentNode:
        return ContentNode(
            id=node_id,
            workspace=workspace,
            type="FOLDER",
            title=title,
            sort_order=sort_order,
            status="ACTIVE",
            created_at=updated_at,
            updated_at=updated_at,
        )

    def _build_note(self, node_id: str, workspace: Workspace, parent: ContentNode, title: str, sort_order: int, updated_at: datetime, excerpt: str, markdown: str, word_count: int) -> ContentNode:
        note = ContentNode(
            id=node_id,
            workspace=workspace,
            parent=parent,
            type="NOTE",
            title=title,
            sort_order=sort_order,
            status="ACTIVE",
            created_at=updated_at,
            updated_at=updated_at,
        )
        note.note_document = NoteDocument(
            id=node_id.replace("note", "doc"),
            note=note,
            excerpt=excerpt,
            markdown_content=markdown,
            word_count=word_count,
            updated_at=updated_at,
        )
        return note

    def first_sentence(self, value: str) -> str:
        normalized = self.blank_to_fallback(value, "等待补充更多来源。").strip()
        indexes = [index for index in (normalized.find("。"), normalized.find(".")) if index >= 0]
        return normalized[: min(indexes) + 1] if indexes else normalized

    def blank_to_fallback(self, value: str | None, fallback: str) -> str:
        return value.strip() if value and value.strip() else fallback

    def blank_to_none(self, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return value.strip()

    def join_segments(self, segments: Iterable[str]) -> str:
        return LIST_DELIMITER.join(segment.strip() for segment in segments if segment and segment.strip())

    def join_csv(self, values: Iterable[str]) -> str:
        return ",".join(value.strip() for value in values if value and value.strip())

    def split_csv(self, value: str | None) -> list[str]:
        if not value or not value.strip():
            return []
        return [item.strip() for item in value.split(",") if item and item.strip()]

    def dedupe_ids(self, values: Iterable[str | None]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = value.strip() if value and value.strip() else None
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

    def dump_json(self, value) -> str:
        return self.encode_json_payload(value)

    def encode_json_payload(self, value: object) -> str:
        return json.dumps(value, ensure_ascii=False)

    def decode_json_list(self, raw: str | None) -> list[str]:
        if not raw or not raw.strip():
            return []
        decoded = json.loads(raw)
        if not isinstance(decoded, list):
            return []
        return [str(item) for item in decoded]

    def decode_web_citations(self, raw: str | None) -> list[WebCitationModel]:
        if not raw or not raw.strip():
            return []
        decoded = json.loads(raw)
        if not isinstance(decoded, list):
            return []
        return [WebCitationModel.model_validate(item) for item in decoded]

    def decode_writeback_package(self, raw: str | None) -> AskWritebackPackageModel | None:
        if not raw or not raw.strip():
            return None
        decoded = json.loads(raw)
        if not isinstance(decoded, dict) or not decoded:
            return None
        return AskWritebackPackageModel.model_validate(decoded)

    def decode_proposal_payload(self, raw: str | None) -> ProposalPayloadResponse | None:
        if not raw or not raw.strip():
            return None
        decoded = json.loads(raw)
        if not isinstance(decoded, dict) or not decoded:
            return None
        return ProposalPayloadResponse.model_validate(decoded)

    def split_segments(self, value: str | None) -> list[str]:
        if not value or not value.strip():
            return []
        return [segment.strip() for segment in value.split(LIST_DELIMITER) if segment.strip()]

    def append_unique_segment(self, existing: str, candidate: str | None) -> str:
        segments = self.split_segments(existing)
        normalized_candidate = self.blank_to_none(candidate)
        if normalized_candidate and normalized_candidate not in segments:
            segments.append(normalized_candidate)
        return self.join_segments(segments)

    def append_unique_segments(self, existing: str, candidates: Iterable[str]) -> str:
        updated = existing
        for candidate in candidates:
            updated = self.append_unique_segment(updated, candidate)
        return updated

    def proposal_segments(self, values: Iterable[str], fallback: str | None = None) -> list[str]:
        segments: list[str] = []
        for value in values:
            normalized = self.blank_to_none(value)
            if normalized and normalized not in segments:
                segments.append(normalized)
        fallback_value = self.blank_to_none(fallback)
        if not segments and fallback_value:
            segments.append(fallback_value)
        return segments

    def review_summary_value(self, review: ReviewItem, proposal_payload: ProposalPayloadResponse, fallback: str) -> str:
        if self.blank_to_none(review.proposed_understanding):
            return review.proposed_understanding.strip()
        proposal_segments = self.proposal_segments(proposal_payload.summaryChanges)
        if proposal_segments:
            return proposal_segments[-1]
        return self.blank_to_fallback(fallback, review.summary)

    def normalize(self, value: str | None) -> str:
        return re.sub(r"[^\w\u4e00-\u9fff]+", "", (value or "").lower())

    def slugify(self, value: str) -> str:
        return self.vault_service.slugify(value)

    def unique_slugify(self, value: str) -> str:
        base = self.slugify(value)
        existing = {topic.slug for topic in self._topics()}
        if base not in existing:
            return base
        suffix = 2
        while f"{base}-{suffix}" in existing:
            suffix += 1
        return f"{base}-{suffix}"

    def new_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid4().hex}"


def get_research_service(db: Session, settings: Settings) -> ResearchWorkspaceService:
    web_import_service = WebRawImportService()
    embedding_service = EmbeddingService(settings)
    retrieval_service = RetrievalService(db, embedding_service)
    return ResearchWorkspaceService(
        db=db,
        settings=settings,
        agent_runtime=AgentRuntime(
            settings,
            web_assist_provider=web_import_service.assist_from_query if settings.enable_web_assist else None,
        ),
        embedding_service=embedding_service,
        retrieval_service=retrieval_service,
        vault_service=VaultService(settings),
        vault_markdown_service=VaultMarkdownService(),
        web_import_service=web_import_service,
        pdf_import_service=PdfRawImportService(),
    )
