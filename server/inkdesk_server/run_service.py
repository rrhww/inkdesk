from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from inkdesk_server.models import DevRun, RunEvent, Workspace
from inkdesk_server.schemas import (
    DevRunResponse,
    DevRunSummaryResponse,
    RunEventResponse,
    StageInfo,
)
from inkdesk_server.security import ResourceNotFoundError, ApiError
from inkdesk_server.time_utils import ensure_utc_datetime


VALID_TYPES = frozenset({"PRD", "BUG", "REFACTOR"})
STAGES = ("context", "solution", "review", "coding", "testing", "deposit")
ACTIVE_STATES = frozenset({"draft", "active", "awaiting_review", "blocked"})


@dataclass
class RunService:
    db: Session

    def create_run(
        self, workspace_id: str, run_type: str, title: str, goal: str, repo_context: str | None
    ) -> DevRunResponse:
        if run_type not in VALID_TYPES:
            raise ApiError(422, "INVALID_RUN_TYPE", f"type must be one of: {','.join(sorted(VALID_TYPES))}")

        now = datetime.now(UTC)
        run = DevRun(
            id=f"run-{uuid4().hex[:12]}",
            workspace_id=workspace_id,
            type=run_type,
            title=title,
            goal=goal,
            repo_context=repo_context or None,
            status="active",
            current_stage="context",
            stage_status="pending",
            created_at=now,
            updated_at=now,
        )
        event = RunEvent(
            id=f"revent-{uuid4().hex[:12]}",
            run=run,
            event_type="created",
            payload_json="{}",
            created_at=now,
        )
        self.db.add(run)
        self.db.add(event)
        self.db.commit()
        return self._to_response(run)

    def get_runs(self, workspace_id: str) -> list[DevRunSummaryResponse]:
        rows = (
            self.db.execute(
                select(DevRun)
                .where(DevRun.workspace_id == workspace_id)
                .order_by(DevRun.created_at.desc())
            )
            .scalars()
            .all()
        )
        return [self._to_summary(r) for r in rows]

    def get_run(self, run_id: str, workspace_id: str) -> DevRunResponse:
        run = self._require_run(run_id, workspace_id)
        return self._to_response(run)

    def add_event(
        self, run_id: str, stage: str | None, event_type: str, payload: dict, workspace_id: str
    ) -> DevRunResponse:
        run = self._require_run(run_id, workspace_id)
        if run.status not in ("draft", "active", "awaiting_review", "blocked"):
            raise ApiError(409, "RUN_NOT_ACTIVE", "Cannot add event to a run that is completed or cancelled.")

        now = datetime.now(UTC)
        event = RunEvent(
            id=f"revent-{uuid4().hex[:12]}",
            run_id=run.id,
            event_type=event_type,
            stage=stage,
            payload_json=json.dumps(payload, ensure_ascii=False),
            created_at=now,
        )
        self.db.add(event)

        if stage and stage in STAGES:
            run.current_stage = stage
            run.stage_status = "awaiting_review"
            run.status = "awaiting_review"

        run.updated_at = now
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return self._to_response(run)

    def cancel_run(self, run_id: str, workspace_id: str) -> DevRunResponse:
        run = self._require_run(run_id, workspace_id)
        if run.status not in ACTIVE_STATES:
            raise ApiError(409, "RUN_NOT_ACTIVE", "Only active runs can be cancelled.")

        now = datetime.now(UTC)
        run.status = "cancelled"
        run.cancelled_at = now
        run.updated_at = now
        event = RunEvent(
            id=f"revent-{uuid4().hex[:12]}",
            run_id=run.id,
            event_type="cancelled",
            payload_json="{}",
            created_at=now,
        )
        self.db.add(run)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(run)
        return self._to_response(run)

    def advance_run(self, run_id: str, action: str, workspace_id: str) -> DevRunResponse:
        run = self._require_run(run_id, workspace_id)
        if run.status not in ACTIVE_STATES:
            raise ApiError(409, "RUN_NOT_ACTIVE", "Cannot advance a run that is completed or cancelled.")

        if action not in ("approve", "complete"):
            raise ApiError(422, "INVALID_ADVANCE_ACTION", "action must be 'approve' or 'complete'.")

        now = datetime.now(UTC)

        if action == "complete":
            if run.current_stage != "deposit":
                raise ApiError(409, "INVALID_STAGE", "Run can only be completed from the deposit stage.")
            if run.stage_status != "awaiting_review":
                raise ApiError(409, "STAGE_NOT_AWAITING_REVIEW", "Deposit stage must be in awaiting_review to complete.")
            run.status = "completed"
            run.stage_status = "completed"
            run.completed_at = now
            run.updated_at = now
            event = RunEvent(
                id=f"revent-{uuid4().hex[:12]}",
                run_id=run.id,
                event_type="completed",
                stage=run.current_stage,
                payload_json=json.dumps({"action": "complete"}, ensure_ascii=False),
                created_at=now,
            )
            self.db.add(run)
            self.db.add(event)
            self.db.commit()
            self.db.refresh(run)
            return self._to_response(run)

        # action == "approve"
        if run.stage_status != "awaiting_review":
            raise ApiError(409, "STAGE_NOT_AWAITING_REVIEW", "Current stage must be in awaiting_review to approve.")
        cur_idx = STAGES.index(run.current_stage)
        run.stage_status = "completed"

        event = RunEvent(
            id=f"revent-{uuid4().hex[:12]}",
            run_id=run.id,
            event_type="stage_approved",
            stage=run.current_stage,
            payload_json=json.dumps({"action": "approve", "fromStage": run.current_stage}, ensure_ascii=False),
            created_at=now,
        )
        self.db.add(event)

        next_idx = cur_idx + 1
        if next_idx >= len(STAGES):
            # 所有阶段完成 = 整个 run 完成
            run.status = "completed"
            run.completed_at = now
            event2 = RunEvent(
                id=f"revent-{uuid4().hex[:12]}",
                run_id=run.id,
                event_type="completed",
                payload_json=json.dumps({"action": "auto-completed"}, ensure_ascii=False),
                created_at=now,
            )
            self.db.add(event2)
        else:
            run.current_stage = STAGES[next_idx]
            run.stage_status = "pending"
            run.status = "active"

        run.updated_at = now
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return self._to_response(run)

    def _require_run(self, run_id: str, workspace_id: str) -> DevRun:
        run = self.db.get(DevRun, run_id)
        if not run or run.workspace_id != workspace_id:
            raise ResourceNotFoundError(f"DevRun not found: {run_id}")
        return run

    def _to_response(self, run: DevRun) -> DevRunResponse:
        events = sorted(run.events, key=lambda e: ensure_utc_datetime(e.created_at))
        return DevRunResponse(
            id=run.id,
            workspaceId=run.workspace_id,
            type=run.type,
            title=run.title,
            goal=run.goal,
            repoContext=run.repo_context,
            status=run.status,
            currentStage=run.current_stage,
            stageStatus=run.stage_status,
            stages=[StageInfo(name=s, status="completed" if _stage_passed(s, run.current_stage, run.stage_status) else
                ("skipped" if _stage_skipped(s, events) else
                 ("active" if s == run.current_stage and run.stage_status not in ("completed", "skipped", "pending") else "pending"))) for s in STAGES],
            events=[RunEventResponse(
                id=e.id,
                eventType=e.event_type,
                stage=e.stage,
                payload=_parse_payload(e.payload_json),
                createdAt=e.created_at,
            ) for e in events],
            createdAt=run.created_at,
            updatedAt=run.updated_at,
            completedAt=run.completed_at,
            cancelledAt=run.cancelled_at,
        )

    def _to_summary(self, run: DevRun) -> DevRunSummaryResponse:
        return DevRunSummaryResponse(
            id=run.id,
            type=run.type,
            title=run.title,
            status=run.status,
            currentStage=run.current_stage,
            stageStatus=run.stage_status,
            createdAt=run.created_at,
        )


def _stage_passed(stage: str, current: str, stage_status: str) -> bool:
    idx = STAGES.index(stage)
    cur_idx = STAGES.index(current)
    return idx < cur_idx or (idx == cur_idx and stage_status in ("completed", "skipped"))


def _stage_skipped(stage: str, events: list[RunEvent]) -> bool:
    for e in events:
        if e.stage == stage and e.event_type == "stage_output":
            try:
                p = json.loads(e.payload_json)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(p, dict) and p.get("skipped"):
                return True
    return False


def _parse_payload(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"raw": raw}
