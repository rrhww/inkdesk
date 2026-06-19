from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from inkdesk_server.models import AskTurn, DevRun, ReviewItem, Topic
from inkdesk_server.schemas import DepositResponse
from inkdesk_server.security import ApiError, ResourceNotFoundError
from inkdesk_server.vault import VaultService


VALID_SOURCES = frozenset({"answer", "selection", "stage_output"})


@dataclass
class DepositService:
    db: Session
    vault_service: VaultService

    def deposit(
        self,
        workspace_id: str,
        source: str,
        payload: dict,
        run_id: str | None = None,
        ask_turn_id: str | None = None,
        stage: str | None = None,
    ) -> DepositResponse:
        if source not in VALID_SOURCES:
            raise ApiError(422, "INVALID_SOURCE", f"source must be one of: {','.join(sorted(VALID_SOURCES))}")

        # validate run ownership if provided
        if run_id:
            run = self.db.get(DevRun, run_id)
            if not run or run.workspace_id != workspace_id:
                raise ResourceNotFoundError(f"DevRun not found: {run_id}")

        # validate ask_turn ownership if provided
        ask_turn = None
        if ask_turn_id:
            ask_turn = self.db.scalar(
                select(AskTurn).where(
                    AskTurn.id == ask_turn_id,
                    AskTurn.workspace_id == workspace_id,
                )
            )
            if not ask_turn:
                raise ResourceNotFoundError(f"Ask turn not found: {ask_turn_id}")

        if source == "answer" and not ask_turn_id:
            raise ApiError(422, "MISSING_ASK_TURN", "answer deposit requires askTurnId")

        now = datetime.now(UTC)
        title = payload.get("title", "未命名沉淀")
        understanding = payload.get("understanding", "")
        claim = payload.get("claim") or (payload.get("selectedText") if source == "selection" else None)

        # build content hash for idempotency
        hash_input = f"deposit|{source}|{ask_turn_id or ''}|{run_id or ''}|{understanding}"
        proposal_hash = self.vault_service.content_hash(hash_input)

        existing = self.db.scalar(
            select(ReviewItem).where(
                ReviewItem.content_hash == proposal_hash,
                ReviewItem.status == "PENDING",
                ReviewItem.workspace_id == workspace_id,
            )
        )
        if existing:
            return DepositResponse(reviewId=existing.id, status=existing.status, source=source, isNew=False)

        # derive target topic from payload
        target_topic = None
        target_topic_id = payload.get("targetTopicId")
        if target_topic_id:
            target_topic = self.db.scalar(select(Topic).where(Topic.id == target_topic_id))

        review = ReviewItem(
            id=f"review-{uuid4().hex[:12]}",
            workspace_id=workspace_id,
            source_id=None,
            target_topic=target_topic,
            kind="TOPIC_CREATE" if target_topic is None else "TOPIC_PATCH",
            proposal_kind="TOPIC_CREATE" if target_topic is None else "TOPIC_PATCH",
            status="PENDING",
            title=title,
            summary=payload.get("summary", ""),
            proposed_topic_title=payload.get("proposedTopicTitle"),
            proposed_understanding=understanding,
            proposed_open_questions=payload.get("openQuestions"),
            proposed_claim=claim,
            proposed_vault_path=payload.get("proposedVaultPath"),
            proposal_payload_json=json.dumps({"source": source, "runId": run_id, "askTurnId": ask_turn_id, "stage": stage, **payload}, ensure_ascii=False),
            content_hash=proposal_hash,
            created_at=now,
        )
        self.db.add(review)

        # record a deposit event on the run if provided
        if run_id:
            from inkdesk_server.run_service import RunService
            RunService(self.db).add_event(
                run_id=run_id,
                stage=stage or "deposit",
                event_type="deposited",
                payload={"reviewId": review.id, "source": source, "askTurnId": ask_turn_id},
                workspace_id=workspace_id,
            )

        self.db.commit()
        return DepositResponse(reviewId=review.id, status=review.status, source=source, isNew=True)
