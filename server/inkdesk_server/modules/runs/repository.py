from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from inkdesk_server.models import DevRun, RunEvent
from inkdesk_server.modules.runs.domain import GoalContract
from inkdesk_server.modules.runs.models import RunGoalContract
from inkdesk_server.modules.spaces.topology import WorkspaceSpaceContext


class RunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_with_goal_contract(
        self,
        *,
        context: WorkspaceSpaceContext,
        run_type: str,
        title: str,
        repo_context: str | None,
        contract: GoalContract,
    ) -> DevRun:
        now = datetime.now(UTC)
        run = DevRun(
            id=f"run-{uuid4().hex[:12]}",
            workspace_id=context.workspace.id,
            organization_id=context.organization.id,
            capability_space_id=context.project_space.id,
            created_by_membership_id=context.membership.id,
            type=run_type,
            title=title,
            goal=contract.purpose,
            repo_context=repo_context or None,
            status="active",
            current_stage="context",
            stage_status="pending",
            created_at=now,
            updated_at=now,
        )
        goal_contract = RunGoalContract(
            id=f"gcontract-{uuid4().hex[:12]}",
            run_id=run.id,
            schema_version=1,
            contract_json=contract.canonical_json,
            contract_hash=contract.hash,
            created_at=now,
        )
        event = RunEvent(
            id=f"revent-{uuid4().hex[:12]}",
            run_id=run.id,
            event_type="created",
            payload_json=json.dumps(
                {
                    "goalContractId": goal_contract.id,
                    "goalContractVersion": goal_contract.schema_version,
                    "goalContractHash": goal_contract.contract_hash,
                },
                separators=(",", ":"),
            ),
            created_at=now,
        )
        self.db.add_all((run, goal_contract, event))
        self.db.flush()
        return run
