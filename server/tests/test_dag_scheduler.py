from __future__ import annotations

import asyncio
from time import perf_counter

import pytest

from inkdesk_skill_sdk.scheduler import DagTask, DagValidationError, KahnDagScheduler, breadth_first_layers


def test_breadth_first_layers_use_kahn_topological_order() -> None:
    tasks = [
        DagTask("kb"),
        DagTask("repo"),
        DagTask("security"),
        DagTask("synthesis", dependencies=("kb", "repo", "security")),
        DagTask("delivery", dependencies=("synthesis",)),
    ]

    assert breadth_first_layers(tasks) == (
        ("kb", "repo", "security"),
        ("synthesis",),
        ("delivery",),
    )


def test_kahn_validation_rejects_missing_edges_and_cycles() -> None:
    with pytest.raises(DagValidationError, match="missing dependencies"):
        breadth_first_layers([DagTask("a", dependencies=("missing",))])

    with pytest.raises(DagValidationError, match="cycle"):
        breadth_first_layers(
            [DagTask("a", dependencies=("b",)), DagTask("b", dependencies=("a",))]
        )


@pytest.mark.asyncio
async def test_scheduler_runs_independent_tasks_concurrently_and_waits_for_dependencies() -> None:
    active = 0
    peak_active = 0
    finished_at: dict[str, float] = {}
    started_at: dict[str, float] = {}
    events: list[str] = []
    lock = asyncio.Lock()

    async def runner(task, dependency_results):
        nonlocal active, peak_active
        async with lock:
            active += 1
            peak_active = max(peak_active, active)
            started_at[task.id] = perf_counter()
        if task.id == "synthesis":
            assert set(dependency_results) == {"kb", "repo", "security"}
        await asyncio.sleep(0.03)
        async with lock:
            active -= 1
            finished_at[task.id] = perf_counter()
        return f"{task.id}-done"

    async def on_event(event):
        events.append(event.type)

    scheduler = KahnDagScheduler(max_concurrency=4)
    result = await scheduler.execute(
        [
            DagTask("kb"),
            DagTask("repo"),
            DagTask("security"),
            DagTask("synthesis", dependencies=("kb", "repo", "security")),
        ],
        runner,
        on_event,
    )

    assert peak_active == 3
    assert started_at["synthesis"] >= max(finished_at[name] for name in ("kb", "repo", "security"))
    assert result.results["synthesis"].output == "synthesis-done"
    assert result.completed_order[-1] == "synthesis"
    assert events[0] == "dag.started"
    assert events[-1] == "dag.completed"


@pytest.mark.asyncio
async def test_scheduler_stops_the_dag_on_task_failure() -> None:
    async def runner(task, _dependencies):
        if task.id == "broken":
            raise RuntimeError("agent failed")
        await asyncio.sleep(0.01)
        return "ok"

    with pytest.raises(RuntimeError, match="agent failed"):
        await KahnDagScheduler().execute(
            [DagTask("broken"), DagTask("blocked", dependencies=("broken",))],
            runner,
        )
