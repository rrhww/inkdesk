"""CompileTask compatibility adapter for the durable job worker."""

from __future__ import annotations

from datetime import UTC, datetime
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from inkdesk_server.models import CompileStep, CompileTask, Source
from inkdesk_server.modules.spaces.workspace_adapter import require_workspace_context_by_id

from ..models import Job
from ..policies import JobCommand
from ..repository import ClaimedJob, DurableJobRepository, JobRequest


COMPILE_STEP_NAMES = ["INSIGHT", "EVIDENCE", "ROUTER", "CONFLICT", "PATCH"]


class CompileJobAdapter:
    kind = "compile_source"

    def enqueue_for_source(self, service, source: Source) -> CompileTask:
        db: Session = service.db
        proposed_vault_path = service.vault_service.wiki_path_for_slug(service.slugify(source.title))
        content_hash = service.vault_service.content_hash(f"compile|{source.id}|{proposed_vault_path}|{source.content_hash}")
        context = require_workspace_context_by_id(db, workspace_id=source.workspace_id)
        deduplication_key = f"compile:{source.workspace_id}:{source.id}:{content_hash}"
        existing_job = db.scalar(select(Job).where(Job.kind == self.kind, Job.organization_id == context.organization.id, Job.capability_space_id == context.project_space.id, Job.deduplication_key == deduplication_key, Job.status.in_(["pending", "running"])))
        if existing_job is not None:
            existing_task = db.get(CompileTask, existing_job.subject_id)
            if existing_task is not None:
                return existing_task
        now = datetime.now(UTC)
        task = CompileTask(id=service.new_id("ct"), workspace_id=source.workspace_id, source_id=source.id, status="PENDING", content_hash=content_hash, created_at=now)
        db.add(task)
        db.flush()
        for index, step_name in enumerate(COMPILE_STEP_NAMES):
            db.add(CompileStep(id=service.new_id("cs"), compile_task_id=task.id, step_name=step_name, sort_order=index, status="PENDING"))
        DurableJobRepository(db).enqueue(JobRequest(command=JobCommand(self.kind, context.organization.id, context.project_space.id, {"compile_task_id": task.id}), idempotency_key=f"compile-task:{task.id}", deduplication_key=deduplication_key, subject_type="compile_task", subject_id=task.id, max_attempts=service.settings.job_default_max_attempts), now=now)
        db.flush()
        return task

    def handle(self, db: Session, claim: ClaimedJob) -> dict[str, object]:
        task = db.get(CompileTask, claim.subject_id)
        if task is None or task.status in {"COMPLETED", "FAILED"}:
            return {"reconciled": True}
        if task.source is None:
            raise ValueError("Compile source is unavailable")
        from inkdesk_server.core.config import get_settings
        from inkdesk_server.research import get_research_service

        service = get_research_service(db, get_settings())
        task.status, task.started_at, task.error_message = "RUNNING", datetime.now(UTC), None
        for step in sorted(task.steps, key=lambda item: item.sort_order):
            step.status, step.started_at = "RUNNING", datetime.now(UTC)
            if step.step_name == "INSIGHT":
                step.payload_json = json.dumps({"sourceTitle": task.source.title, "sourceExcerpt": task.source.excerpt, "sourceKind": task.source.kind}, ensure_ascii=False)
            elif step.step_name == "EVIDENCE":
                match = service.find_matching_topic(task.source, service._topics())
                step.payload_json = json.dumps({"matchedTopicId": match.id if match else None, "matchedTopicTitle": match.title if match else None}, ensure_ascii=False)
            elif step.step_name == "ROUTER":
                match = service.find_matching_topic(task.source, service._topics())
                step.payload_json = json.dumps({"decision": "TOPIC_CREATE" if match is None else "TOPIC_PATCH", "matchedTopicId": match.id if match else None}, ensure_ascii=False)
            elif step.step_name == "CONFLICT":
                match = service.find_matching_topic(task.source, service._topics())
                step.payload_json = json.dumps({"conflictCount": len(service.conflicting_claims(match)) if match else 0}, ensure_ascii=False)
            elif step.step_name == "PATCH":
                service._compile_and_create_review(task.source)
            step.status, step.completed_at = "COMPLETED", datetime.now(UTC)
        task.status, task.completed_at = "COMPLETED", datetime.now(UTC)
        db.add(task)
        return {"compile_task_id": task.id}

    def on_failure(self, db: Session, claim: ClaimedJob, message: str) -> None:
        task = db.get(CompileTask, claim.subject_id)
        if task is None or task.status in {"COMPLETED", "FAILED"}:
            return
        task.status = "FAILED"
        task.error_message = message
        task.completed_at = datetime.now(UTC)
        for step in task.steps:
            if step.status == "RUNNING":
                step.status = "FAILED"
                step.error_message = message
                step.completed_at = task.completed_at
        db.add(task)
