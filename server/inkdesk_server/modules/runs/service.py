from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy.orm import Session

from inkdesk_server.modules.runs.domain import GoalContractValidationError, parse_goal_contract
from inkdesk_server.modules.runs.repository import RunRepository
from inkdesk_server.modules.spaces.topology import WorkspaceSpaceContext
from inkdesk_server.run_service import VALID_TYPES, RunService
from inkdesk_server.schemas import DevRunResponse
from inkdesk_server.security import ApiError


class RunsApplicationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_run(
        self,
        *,
        context: WorkspaceSpaceContext,
        run_type: str,
        title: str,
        repo_context: str | None,
        goal_contract: Mapping[str, Any] | None,
    ) -> DevRunResponse:
        if run_type not in VALID_TYPES:
            raise ApiError(422, "INVALID_RUN_TYPE", f"type must be one of: {','.join(sorted(VALID_TYPES))}")
        try:
            contract = parse_goal_contract(goal_contract)
        except GoalContractValidationError as error:
            raise ApiError(422, error.code, "Goal Contract is invalid.") from error

        try:
            run = RunRepository(self.db).create_with_goal_contract(
                context=context,
                run_type=run_type,
                title=title,
                repo_context=repo_context,
                contract=contract,
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(run)
        return RunService(self.db)._to_response(run)
