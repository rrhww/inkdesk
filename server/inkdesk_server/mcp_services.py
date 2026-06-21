from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from inkdesk_server.models import AskTurn, ReviewItem
from inkdesk_server.run_service import RunService
from inkdesk_server.time_utils import ensure_utc_datetime
from inkdesk_server.vault import VaultService


CONTEXT_PACK_LIMIT = 20


@dataclass
class ContextPackService:
    db: Session

    def build(self, workspace_id: str, run_id: str) -> dict:
        run = RunService(self.db).get_run(run_id, workspace_id)
        result = {
            "id": run.id,
            "type": run.type,
            "title": run.title,
            "goal": run.goal,
            "repoContext": run.repoContext,
            "status": run.status,
            "currentStage": run.currentStage,
            "stages": [{"name": stage.name, "status": stage.status} for stage in run.stages],
            "events": [
                {
                    "id": event.id,
                    "type": event.eventType,
                    "stage": event.stage,
                    "payload": event.payload,
                }
                for event in run.events
            ],
            "createdAt": ensure_utc_datetime(run.createdAt).isoformat(),
            "updatedAt": ensure_utc_datetime(run.updatedAt).isoformat(),
            "askHistory": self._ask_history(workspace_id, run_id),
            "relatedReviews": self._related_reviews(workspace_id, run_id),
        }
        if run.completedAt:
            result["completedAt"] = ensure_utc_datetime(run.completedAt).isoformat()
        if run.cancelledAt:
            result["cancelledAt"] = ensure_utc_datetime(run.cancelledAt).isoformat()
        return result

    def _ask_history(self, workspace_id: str, run_id: str) -> list[dict]:
        turns = self.db.scalars(
            select(AskTurn)
            .where(AskTurn.run_id == run_id, AskTurn.workspace_id == workspace_id)
            .order_by(desc(AskTurn.created_at))
            .limit(CONTEXT_PACK_LIMIT)
        ).all()
        history = []
        for turn in reversed(turns):
            try:
                gaps = json.loads(turn.knowledge_gaps_json)
            except (json.JSONDecodeError, TypeError):
                gaps = []
            history.append({
                "id": turn.id,
                "question": turn.question,
                "answer": turn.answer[:800],
                "confidence": turn.confidence,
                "knowledgeGaps": gaps[:10],
                "canWriteback": turn.can_writeback,
                "createdAt": ensure_utc_datetime(turn.created_at).isoformat(),
            })
        return history

    def _related_reviews(self, workspace_id: str, run_id: str) -> list[dict]:
        reviews = self.db.scalars(
            select(ReviewItem).where(
                ReviewItem.workspace_id == workspace_id,
                ReviewItem.status == "PENDING",
            )
        ).all()
        related = []
        for review in reviews:
            try:
                payload = json.loads(review.proposal_payload_json)
            except (json.JSONDecodeError, TypeError):
                continue
            if payload.get("runId") == run_id:
                related.append({
                    "id": review.id,
                    "kind": review.kind,
                    "title": review.title,
                    "summary": review.summary[:300],
                    "status": review.status,
                })
        return related


@dataclass
class VaultSearchService:
    vault: VaultService

    def search(self, query: str, directories: tuple[str, ...] = ("wiki", "raw")) -> list[dict]:
        results = []
        normalized_query = query.casefold()
        for directory in directories:
            for relative_path in self.vault.list_markdown_files(directory):
                try:
                    content = self.vault.read_vault_file(relative_path)
                except (OSError, ValueError):
                    continue
                if normalized_query in content.casefold():
                    results.append({"path": relative_path, "snippet": content[:200]})
        return results
