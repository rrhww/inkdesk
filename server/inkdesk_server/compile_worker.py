from __future__ import annotations

import logging
import queue
import threading
from datetime import UTC, datetime

from inkdesk_server.core.config import Settings, get_settings
from inkdesk_server.db import get_session_factory, session_scope

logger = logging.getLogger(__name__)

_worker: CompileWorker | None = None
_worker_lock = threading.Lock()

COMPILE_STEP_NAMES = ["INSIGHT", "EVIDENCE", "ROUTER", "CONFLICT", "PATCH"]


def get_compile_worker(settings: Settings | None = None) -> CompileWorker:
    global _worker
    with _worker_lock:
        if _worker is None:
            _worker = CompileWorker(settings)
        return _worker


def _reset_compile_worker() -> None:
    global _worker
    with _worker_lock:
        if _worker is not None:
            _worker.stop()
            _worker = None


class CompileWorker:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._queue: queue.Queue[str] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="compile-worker"
        )
        self._thread.start()
        self._recover_pending_tasks()
        logger.info("Compile worker started.")

    def stop(self, timeout: float = 10.0) -> None:
        if not self._running:
            return
        self._running = False
        self._queue.put("__SHUTDOWN__")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        logger.info("Compile worker stopped.")

    def enqueue(self, task_id: str) -> None:
        self._queue.put(task_id)

    def _recover_pending_tasks(self) -> None:
        from inkdesk_server.models import CompileTask
        from sqlalchemy import select
        try:
            with session_scope() as db:
                orphaned = db.scalars(
                    select(CompileTask).where(CompileTask.status == "PENDING")
                ).all()
                for task in orphaned:
                    self.enqueue(task.id)
            if orphaned:
                logger.info("Recovered %d pending compile tasks.", len(orphaned))
        except Exception:
            logger.warning("Could not recover pending compile tasks.", exc_info=True)

    def _run_loop(self) -> None:
        while self._running:
            try:
                task_id = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if task_id == "__SHUTDOWN__":
                break
            try:
                self._process_task(task_id)
            except Exception:
                logger.exception("Compile worker crash processing task %s", task_id)
            finally:
                self._queue.task_done()

    def _process_task(self, task_id: str) -> None:
        from inkdesk_server.models import CompileTask, CompileStep
        from inkdesk_server.research import get_research_service

        with session_scope() as db:
            task = db.get(CompileTask, task_id)
            if task is None:
                return
            if task.status != "PENDING":
                return

            task.status = "RUNNING"
            task.started_at = datetime.now(UTC)
            task.error_message = None
            db.add(task)

            service = get_research_service(db, self._settings)
            source = task.source

            step_list = sorted(task.steps, key=lambda s: s.sort_order)
            failed = False
            for step in step_list:
                step.status = "RUNNING"
                step.started_at = datetime.now(UTC)
                db.add(step)
                db.flush()

                try:
                    if step.step_name == "INSIGHT":
                        self._execute_insight(step, source)
                    elif step.step_name == "EVIDENCE":
                        self._execute_evidence(step, service, source)
                    elif step.step_name == "ROUTER":
                        self._execute_router(step, service, source)
                    elif step.step_name == "CONFLICT":
                        self._execute_conflict(step, service, source)
                    elif step.step_name == "PATCH":
                        self._execute_patch(step, service, source)

                    step.status = "COMPLETED"
                    step.completed_at = datetime.now(UTC)
                except Exception as exc:
                    step.status = "FAILED"
                    step.error_message = str(exc)[:2000]
                    step.completed_at = datetime.now(UTC)
                    task.error_message = f"Step {step.step_name} failed: {step.error_message}"
                    task.status = "FAILED"
                    db.add(task)
                    db.add(step)
                    failed = True
                    break

                db.add(step)

            if not failed:
                task.status = "COMPLETED"
                task.completed_at = datetime.now(UTC)
                db.add(task)

    def _execute_insight(self, step, source):
        import json
        if source is None:
            raise ValueError("Source not found")
        step.payload_json = json.dumps({
            "sourceTitle": source.title,
            "sourceExcerpt": source.excerpt,
            "sourceKind": source.kind,
        }, ensure_ascii=False)

    def _execute_evidence(self, step, service, source):
        import json
        if source is None:
            raise ValueError("Source not found")
        available_topics = service._topics()
        matched_topic = service.find_matching_topic(source, available_topics)
        step.payload_json = json.dumps({
            "matchedTopicId": matched_topic.id if matched_topic else None,
            "matchedTopicTitle": matched_topic.title if matched_topic else None,
        }, ensure_ascii=False)

    def _execute_router(self, step, service, source):
        import json
        if source is None:
            raise ValueError("Source not found")
        available_topics = service._topics()
        matched_topic = service.find_matching_topic(source, available_topics)
        decision = "TOPIC_CREATE" if matched_topic is None else "TOPIC_PATCH"
        step.payload_json = json.dumps({
            "decision": decision,
            "matchedTopicId": matched_topic.id if matched_topic else None,
        }, ensure_ascii=False)

    def _execute_conflict(self, step, service, source):
        import json
        if source is None:
            raise ValueError("Source not found")
        available_topics = service._topics()
        matched_topic = service.find_matching_topic(source, available_topics)
        conflicts = []
        if matched_topic:
            conflicts = service.conflicting_claims(matched_topic)
        step.payload_json = json.dumps({
            "conflictCount": len(conflicts),
        }, ensure_ascii=False)

    def _execute_patch(self, step, service, source):
        if source is None:
            raise ValueError("Source not found")
        service._compile_and_create_review(source)
