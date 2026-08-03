from __future__ import annotations

import asyncio
import inspect
from collections import deque
from contextlib import asynccontextmanager
from time import perf_counter
from types import MappingProxyType
from typing import Any, Awaitable, Callable, Mapping

from inkdesk_server.harness.models import (
    StageEffect,
    StageStatus,
    WorkflowExecutionEvent,
    WorkflowExecutionResult,
    WorkflowStage,
    WorkflowStageResult,
    utc_now,
)


class WorkflowValidationError(ValueError):
    pass


StageRunner = Callable[
    [WorkflowStage, Mapping[str, WorkflowStageResult]],
    Awaitable[Any | WorkflowStageResult] | Any | WorkflowStageResult,
]
EventSink = Callable[[WorkflowExecutionEvent], Awaitable[None] | None]


class WorkflowScheduler:
    """Kahn-style scheduler for observable Harness stages."""

    def __init__(self, max_concurrency: int = 3):
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        self.max_concurrency = max_concurrency
        self._effect_locks = {
            StageEffect.WORKSPACE_WRITE: asyncio.Lock(),
            StageEffect.VAULT_WRITE: asyncio.Lock(),
            StageEffect.EXTERNAL: asyncio.Lock(),
        }

    async def execute(
        self,
        stages: list[WorkflowStage] | tuple[WorkflowStage, ...],
        runner: StageRunner,
        on_event: EventSink | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> WorkflowExecutionResult:
        started = perf_counter()
        stage_by_id = _validate_stages(stages)
        _topological_layers(stage_by_id)
        if not stage_by_id:
            return WorkflowExecutionResult({}, (), {}, 0.0)

        indegree = {stage.id: len(stage.dependencies) for stage in stage_by_id.values()}
        dependents = _dependents(stage_by_id)
        ready: asyncio.Queue[str] = asyncio.Queue()
        states = {stage_id: StageStatus.PENDING for stage_id in stage_by_id}
        for stage_id in sorted(item for item, degree in indegree.items() if degree == 0):
            states[stage_id] = StageStatus.READY
            ready.put_nowait(stage_id)

        results: dict[str, WorkflowStageResult] = {}
        completed_order: list[str] = []
        state_lock = asyncio.Lock()
        all_done = asyncio.Event()
        failure: Exception | None = None
        sequence = 0

        async def emit(event_type: str, stage_id: str | None, data: Mapping[str, Any]) -> None:
            nonlocal sequence
            sequence += 1
            if on_event is None:
                return
            value = on_event(
                WorkflowExecutionEvent(sequence, event_type, stage_id, utc_now(), data)
            )
            if inspect.isawaitable(value):
                await value

        async def worker() -> None:
            nonlocal failure
            while not all_done.is_set():
                if cancel_event is not None and cancel_event.is_set():
                    all_done.set()
                    return
                try:
                    stage_id = await asyncio.wait_for(ready.get(), timeout=0.05)
                except asyncio.TimeoutError:
                    continue
                stage = stage_by_id[stage_id]
                states[stage_id] = StageStatus.RUNNING
                await emit("stage.started", stage_id, {"kind": stage.kind, "effect": stage.effect.value})
                stage_started = perf_counter()
                try:
                    dependencies = MappingProxyType(
                        {dependency: results[dependency] for dependency in stage.dependencies}
                    )
                    async with self._effect_guard(stage.effect):
                        value = runner(stage, dependencies)
                        if inspect.isawaitable(value):
                            value = await value
                    duration_ms = (perf_counter() - stage_started) * 1000
                    result = (
                        value
                        if isinstance(value, WorkflowStageResult)
                        else WorkflowStageResult(stage.id, value, duration_ms)
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    states[stage_id] = StageStatus.FAILED
                    if failure is None:
                        failure = exc
                    await emit("stage.failed", stage_id, {"error": str(exc)})
                    all_done.set()
                    ready.task_done()
                    return

                async with state_lock:
                    results[stage_id] = result
                    states[stage_id] = StageStatus.SUCCEEDED
                    completed_order.append(stage_id)
                    for dependent_id in dependents[stage_id]:
                        indegree[dependent_id] -= 1
                        if indegree[dependent_id] == 0:
                            states[dependent_id] = StageStatus.READY
                            ready.put_nowait(dependent_id)
                    if len(results) == len(stage_by_id):
                        all_done.set()
                await emit("stage.completed", stage_id, {"durationMs": round(result.duration_ms, 3)})
                ready.task_done()

        await emit("workflow.started", None, {"stageCount": len(stage_by_id)})
        workers = [
            asyncio.create_task(worker())
            for _ in range(min(self.max_concurrency, len(stage_by_id)))
        ]
        await all_done.wait()
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

        if cancel_event is not None and cancel_event.is_set() and failure is None:
            for stage_id, status in tuple(states.items()):
                if status in {StageStatus.PENDING, StageStatus.READY, StageStatus.RUNNING}:
                    states[stage_id] = StageStatus.CANCELLED
            await emit("workflow.cancelled", None, {})
        elif failure is not None:
            for stage_id, status in tuple(states.items()):
                if status in {StageStatus.PENDING, StageStatus.READY}:
                    states[stage_id] = StageStatus.BLOCKED
            raise failure
        else:
            await emit("workflow.completed", None, {})

        return WorkflowExecutionResult(
            MappingProxyType(dict(results)),
            tuple(completed_order),
            MappingProxyType(dict(states)),
            (perf_counter() - started) * 1000,
        )

    @asynccontextmanager
    async def _effect_guard(self, effect: StageEffect):
        lock = self._effect_locks.get(effect)
        if lock is None:
            yield
            return
        async with lock:
            yield


def _validate_stages(
    stages: list[WorkflowStage] | tuple[WorkflowStage, ...],
) -> dict[str, WorkflowStage]:
    stage_by_id: dict[str, WorkflowStage] = {}
    for stage in stages:
        if not stage.id.strip():
            raise WorkflowValidationError("Stage id cannot be blank")
        if stage.id in stage_by_id:
            raise WorkflowValidationError(f"Duplicate stage id: {stage.id}")
        if stage.id in stage.dependencies:
            raise WorkflowValidationError(f"Stage cannot depend on itself: {stage.id}")
        stage_by_id[stage.id] = stage
    all_ids = set(stage_by_id)
    for stage in stage_by_id.values():
        missing = sorted(set(stage.dependencies) - all_ids)
        if missing:
            raise WorkflowValidationError(
                f"Stage {stage.id} has missing dependencies: {', '.join(missing)}"
            )
    return stage_by_id


def _dependents(stage_by_id: Mapping[str, WorkflowStage]) -> dict[str, list[str]]:
    values = {stage_id: [] for stage_id in stage_by_id}
    for stage in stage_by_id.values():
        for dependency in stage.dependencies:
            values[dependency].append(stage.id)
    for item in values.values():
        item.sort()
    return values


def _topological_layers(stage_by_id: Mapping[str, WorkflowStage]) -> tuple[tuple[str, ...], ...]:
    indegree = {stage.id: len(stage.dependencies) for stage in stage_by_id.values()}
    dependents = _dependents(stage_by_id)
    frontier = deque(sorted(stage_id for stage_id, degree in indegree.items() if degree == 0))
    layers: list[tuple[str, ...]] = []
    visited = 0
    while frontier:
        layer = tuple(frontier)
        frontier.clear()
        layers.append(layer)
        for stage_id in layer:
            visited += 1
            for dependent_id in dependents[stage_id]:
                indegree[dependent_id] -= 1
                if indegree[dependent_id] == 0:
                    frontier.append(dependent_id)
        frontier = deque(sorted(frontier))
    if visited != len(stage_by_id):
        raise WorkflowValidationError("Workflow contains a cycle")
    return tuple(layers)
