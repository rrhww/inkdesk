"""Polling worker for durable Job / Attempt execution."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import logging
import threading
from typing import Callable
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from .domain import AttemptStatus, ReasonCode
from .registry import JobHandlerRegistry
from .repository import ClaimedJob, DurableJobRepository


logger = logging.getLogger(__name__)


class DurableWorker:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        registry: JobHandlerRegistry,
        *,
        worker_id: str | None = None,
        lease_duration: timedelta = timedelta(seconds=60),
        poll_interval: float = 1.0,
        heartbeat_interval: float | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._registry = registry
        self._worker_id = worker_id or f"worker-{uuid4().hex}"
        self._lease_duration = lease_duration
        self._poll_interval = poll_interval
        self._heartbeat_interval = heartbeat_interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="durable-job-worker")
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def run_once(self, *, now: datetime | None = None) -> bool:
        # A standalone worker process must load every FK target before flushing attempts.
        from inkdesk_server.model_registry import load_orm_models

        load_orm_models()
        timestamp = now or datetime.now(UTC)
        with self._session_factory() as claim_db:
            repository = DurableJobRepository(claim_db)
            repository.recover_expired(now=timestamp)
            claim = repository.claim(worker_id=self._worker_id, now=timestamp, lease_duration=self._lease_duration)
            claim_db.commit()
        if claim is None:
            return False
        self._execute_claim(claim, timestamp)
        return True

    def _execute_claim(self, claim: ClaimedJob, now: datetime) -> None:
        handler = self._registry.get(claim.kind)
        if handler is None:
            self._finish_failure(claim, now, ReasonCode.JOB_HANDLER_NOT_REGISTERED, "No handler is registered for this job kind.")
            return

        heartbeat_stop = threading.Event()
        lease_lost = threading.Event()
        heartbeat_thread = self._start_heartbeat(claim, heartbeat_stop, lease_lost)
        try:
            with self._session_factory() as db:
                result = handler(db, claim) or {}
                if lease_lost.is_set():
                    db.rollback()
                    logger.warning("Durable job completion rejected because its lease heartbeat was lost: %s", claim.job_id)
                    return
                completed = DurableJobRepository(db).finish(
                    claim,
                    status=AttemptStatus.SUCCEEDED,
                    now=datetime.now(UTC) if heartbeat_thread is not None else now,
                    result=result,
                )
                if not completed:
                    db.rollback()
                    logger.warning("Durable job completion rejected because its lease was lost: %s", claim.job_id)
                    return
                db.commit()
        except Exception:
            logger.exception("Durable job handler failed: %s", claim.job_id)
            if not lease_lost.is_set():
                self._finish_failure(
                    claim,
                    datetime.now(UTC) if heartbeat_thread is not None else now,
                    ReasonCode.JOB_HANDLER_FAILED,
                    "Job handler failed.",
                    handler=handler,
                )
        finally:
            heartbeat_stop.set()
            if heartbeat_thread is not None:
                heartbeat_thread.join(timeout=1.0)

    def _start_heartbeat(self, claim: ClaimedJob, stop_event: threading.Event, lease_lost: threading.Event) -> threading.Thread | None:
        if self._heartbeat_interval is None:
            return None

        def renew() -> None:
            while not stop_event.wait(self._heartbeat_interval):
                with self._session_factory() as db:
                    accepted = DurableJobRepository(db).heartbeat(
                        claim,
                        now=datetime.now(UTC),
                        lease_duration=self._lease_duration,
                    )
                    if not accepted:
                        db.rollback()
                        lease_lost.set()
                        return
                    db.commit()

        thread = threading.Thread(target=renew, daemon=True, name="durable-job-heartbeat")
        thread.start()
        return thread

    def _finish_failure(self, claim: ClaimedJob, now: datetime, reason: ReasonCode, message: str, handler=None) -> None:
        with self._session_factory() as db:
            adapter = getattr(handler, "__self__", None)
            on_failure = getattr(adapter, "on_failure", None)
            if callable(on_failure):
                on_failure(db, claim, message)
            completed = DurableJobRepository(db).finish(
                claim,
                status=AttemptStatus.FAILED,
                now=now,
                error_code=reason,
                error_message=message,
            )
            if completed:
                db.commit()
            else:
                db.rollback()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                did_work = self.run_once()
            except Exception:
                logger.exception("Durable worker poll failed.")
                did_work = False
            if not did_work:
                self._stop_event.wait(self._poll_interval)
