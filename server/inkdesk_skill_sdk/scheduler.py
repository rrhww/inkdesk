from __future__ import annotations

import asyncio
import inspect
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from types import MappingProxyType
from typing import Any, Awaitable, Callable, Mapping


class DagValidationError(ValueError):
    pass


@dataclass(frozen=True)
class DagTask:
    id: str
    dependencies: tuple[str, ...] = ()
    kind: str = "agent"
    prompt: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DagTaskResult:
    task_id: str
    output: str
    duration_ms: float
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DagExecutionEvent:
    sequence: int
    type: str
    task_id: str | None
    timestamp: str
    data: Mapping[str, Any]


@dataclass(frozen=True)
class DagExecutionResult:
    results: Mapping[str, DagTaskResult]
    completed_order: tuple[str, ...]
    duration_ms: float


TaskRunner = Callable[[DagTask, Mapping[str, DagTaskResult]], Awaitable[str | DagTaskResult] | str | DagTaskResult]
EventSink = Callable[[DagExecutionEvent], Awaitable[None] | None]


def breadth_first_layers(tasks: list[DagTask] | tuple[DagTask, ...]) -> tuple[tuple[str, ...], ...]:
    task_by_id = _validate_tasks(tasks)
    indegree = {task.id: len(task.dependencies) for task in task_by_id.values()}
    dependents = _dependents(task_by_id)
    frontier = deque(sorted(task_id for task_id, degree in indegree.items() if degree == 0))
    layers: list[tuple[str, ...]] = []
    visited = 0

    while frontier:
        layer = tuple(frontier)
        frontier.clear()
        layers.append(layer)
        for task_id in layer:
            visited += 1
            for dependent_id in dependents[task_id]:
                indegree[dependent_id] -= 1
                if indegree[dependent_id] == 0:
                    frontier.append(dependent_id)
        frontier = deque(sorted(frontier))

    if visited != len(task_by_id):
        blocked = sorted(task_id for task_id, degree in indegree.items() if degree > 0)
        raise DagValidationError(f"DAG contains a cycle involving: {', '.join(blocked)}")
    return tuple(layers)


class KahnDagScheduler:
    def __init__(self, max_concurrency: int = 8):
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        self.max_concurrency = max_concurrency

    async def execute(
        self,
        tasks: list[DagTask] | tuple[DagTask, ...],
        runner: TaskRunner,
        on_event: EventSink | None = None,
    ) -> DagExecutionResult:
        started = perf_counter()
        task_by_id = _validate_tasks(tasks)
        breadth_first_layers(tuple(task_by_id.values()))
        if not task_by_id:
            return DagExecutionResult(results={}, completed_order=(), duration_ms=0.0)

        indegree = {task.id: len(task.dependencies) for task in task_by_id.values()}
        dependents = _dependents(task_by_id)
        ready: asyncio.Queue[str] = asyncio.Queue()
        for task_id in sorted(task_id for task_id, degree in indegree.items() if degree == 0):
            ready.put_nowait(task_id)

        results: dict[str, DagTaskResult] = {}
        completed_order: list[str] = []
        state_lock = asyncio.Lock()
        all_done = asyncio.Event()
        failure: BaseException | None = None
        sequence = 0

        async def emit(event_type: str, task_id: str | None, data: Mapping[str, Any]) -> None:
            nonlocal sequence
            sequence += 1
            if on_event is None:
                return
            emitted = on_event(
                DagExecutionEvent(
                    sequence=sequence,
                    type=event_type,
                    task_id=task_id,
                    timestamp=datetime.now(UTC).isoformat(),
                    data=data,
                )
            )
            if inspect.isawaitable(emitted):
                await emitted

        async def worker() -> None:
            nonlocal failure
            while not all_done.is_set():
                try:
                    task_id = await asyncio.wait_for(ready.get(), timeout=0.05)
                except asyncio.TimeoutError:
                    continue
                task = task_by_id[task_id]
                task_started = perf_counter()
                await emit("task.started", task_id, {"kind": task.kind})
                try:
                    dependency_results = MappingProxyType(
                        {dependency: results[dependency] for dependency in task.dependencies}
                    )
                    value = runner(task, dependency_results)
                    if inspect.isawaitable(value):
                        value = await value
                    duration_ms = (perf_counter() - task_started) * 1000
                    result = (
                        value
                        if isinstance(value, DagTaskResult)
                        else DagTaskResult(task_id=task_id, output=str(value), duration_ms=duration_ms)
                    )
<<<<<<< HEAD
                except BaseException as exc:
                    failure = exc
=======
                except asyncio.CancelledError:
                    ready.task_done()
                    raise
                except Exception as exc:
                    if failure is None:
                        failure = exc
>>>>>>> origin/main
                    await emit("task.failed", task_id, {"error": str(exc)})
                    all_done.set()
                    ready.task_done()
                    return

                async with state_lock:
                    results[task_id] = result
                    completed_order.append(task_id)
                    for dependent_id in dependents[task_id]:
                        indegree[dependent_id] -= 1
                        if indegree[dependent_id] == 0:
                            ready.put_nowait(dependent_id)
                    if len(results) == len(task_by_id):
                        all_done.set()
                await emit(
                    "task.completed",
                    task_id,
                    {"durationMs": round(result.duration_ms, 3), "output": result.output},
                )
                ready.task_done()

        await emit("dag.started", None, {"taskCount": len(task_by_id)})
        workers = [asyncio.create_task(worker()) for _ in range(min(self.max_concurrency, len(task_by_id)))]
        await all_done.wait()
        for active_worker in workers:
            active_worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        if failure is not None:
            raise failure

        duration_ms = (perf_counter() - started) * 1000
        await emit("dag.completed", None, {"durationMs": round(duration_ms, 3)})
        return DagExecutionResult(
            results=MappingProxyType(dict(results)),
            completed_order=tuple(completed_order),
            duration_ms=duration_ms,
        )


def _validate_tasks(tasks: list[DagTask] | tuple[DagTask, ...]) -> dict[str, DagTask]:
    task_by_id: dict[str, DagTask] = {}
    for task in tasks:
        task_id = task.id.strip()
        if not task_id:
            raise DagValidationError("Task id cannot be blank")
        if task_id in task_by_id:
            raise DagValidationError(f"Duplicate task id: {task_id}")
        if task_id in task.dependencies:
            raise DagValidationError(f"Task cannot depend on itself: {task_id}")
        task_by_id[task_id] = task

    all_ids = set(task_by_id)
    for task in task_by_id.values():
        missing = sorted(set(task.dependencies) - all_ids)
        if missing:
            raise DagValidationError(f"Task {task.id} has missing dependencies: {', '.join(missing)}")
    return task_by_id


def _dependents(task_by_id: Mapping[str, DagTask]) -> dict[str, list[str]]:
    dependents = {task_id: [] for task_id in task_by_id}
    for task in task_by_id.values():
        for dependency in task.dependencies:
            dependents[dependency].append(task.id)
    for values in dependents.values():
        values.sort()
    return dependents
