from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Mapping

import httpx

from inkdesk_server.core.config import Settings
from inkdesk_server.graph_index import GraphSnapshot
from inkdesk_server.schemas import EngineCommandRequest
from inkdesk_skill_sdk.scheduler import DagExecutionEvent, DagTask, DagTaskResult, KahnDagScheduler


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineItem:
    event: str
    data: Mapping[str, Any]


class DualQueueSsePipeline:
    def __init__(self, maxsize: int = 256):
        self.producer_queue: asyncio.Queue[PipelineItem | None] = asyncio.Queue(maxsize=maxsize)
        self.client_queue: asyncio.Queue[PipelineItem] = asyncio.Queue(maxsize=maxsize)

    async def assemble(self) -> None:
        sequence = 0
        while True:
            item = await self.producer_queue.get()
            if item is None:
                await self.client_queue.put(
                    PipelineItem("stream.end", {"sequence": sequence + 1})
                )
                return
            sequence += 1
            await self.client_queue.put(
                PipelineItem(item.event, {"sequence": sequence, **dict(item.data)})
            )


class EngineRuntime:
    def __init__(
        self,
        settings: Settings,
        graph_snapshot: Callable[[], GraphSnapshot],
        runtime_event_sink: Callable[[str, Mapping[str, Any]], None] | None = None,
    ):
        self.settings = settings
        self.graph_snapshot = graph_snapshot
        self.runtime_event_sink = runtime_event_sink
        self._thread_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="inkdesk-agent")
        provider = settings.resolved_agent_provider
        self._provider = provider
        self._http_client = httpx.AsyncClient(
            base_url=provider.base_url or "https://api.openai.com/v1",
            timeout=httpx.Timeout(
                connect=settings.agent_connect_timeout_seconds,
                read=settings.agent_read_timeout_seconds,
                write=settings.agent_read_timeout_seconds,
                pool=settings.agent_connect_timeout_seconds,
            ),
        )

    async def close(self) -> None:
        await self._http_client.aclose()
        self._thread_pool.shutdown(wait=True, cancel_futures=True)

    async def stream(self, request: EngineCommandRequest) -> AsyncIterator[PipelineItem]:
        pipeline = DualQueueSsePipeline()
        assembler = asyncio.create_task(pipeline.assemble())
        producer = asyncio.create_task(self._produce(request, pipeline.producer_queue))
        try:
            while True:
                item = await pipeline.client_queue.get()
                yield item
                if item.event == "stream.end":
                    return
        finally:
            if not producer.done():
                producer.cancel()
            if not assembler.done():
                assembler.cancel()
            await asyncio.gather(producer, assembler, return_exceptions=True)

    async def _produce(
        self,
        request: EngineCommandRequest,
        queue: asyncio.Queue[PipelineItem | None],
    ) -> None:
        await queue.put(PipelineItem("stream.open", {"command": request.command}))
        try:
            tasks = self._build_tasks(request)
            scheduler = KahnDagScheduler(max_concurrency=request.maxConcurrency)
            graph_node_ids = [node.id for node in self.graph_snapshot().nodes if node.status != "missing"]
            active_nodes = {
                task.id: graph_node_ids[index % len(graph_node_ids)]
                for index, task in enumerate(tasks)
            } if graph_node_ids else {}

            async def on_event(event: DagExecutionEvent) -> None:
                active_node_id = active_nodes.get(event.task_id or "")
                if self.runtime_event_sink is not None and active_node_id is not None:
                    if event.type == "task.started":
                        self.runtime_event_sink(
                            "node.active",
                            {"nodeId": active_node_id, "taskId": event.task_id},
                        )
                    elif event.type in {"task.completed", "task.failed"}:
                        self.runtime_event_sink(
                            "node.idle",
                            {"nodeId": active_node_id, "taskId": event.task_id},
                        )
                await queue.put(
                    PipelineItem(
                        event.type,
                        {
                            "taskId": event.task_id,
                            "timestamp": event.timestamp,
                            **dict(event.data),
                        },
                    )
                )

            async def runner(task: DagTask, dependencies: Mapping[str, DagTaskResult]):
                output_parts: list[str] = []
                async for token in self._tokens(task, request.command, dependencies):
                    output_parts.append(token)
                    await queue.put(PipelineItem("token", {"taskId": task.id, "token": token}))
                return "".join(output_parts)

            result = await scheduler.execute(tasks, runner, on_event)
            await queue.put(
                PipelineItem(
                    "result",
                    {
                        "completedOrder": list(result.completed_order),
                        "durationMs": round(result.duration_ms, 3),
                        "outputs": {task_id: task_result.output for task_id, task_result in result.results.items()},
                    },
                )
            )
        except Exception as exc:
            logger.exception("DAG execution failed")
            await queue.put(PipelineItem("stream.error", {"error": str(exc)}))
        finally:
            await queue.put(None)

    def _build_tasks(self, request: EngineCommandRequest) -> tuple[DagTask, ...]:
        if request.tasks:
            return tuple(
                DagTask(
                    id=task.id,
                    dependencies=tuple(task.dependencies),
                    kind=task.kind,
                    prompt=task.prompt,
                    metadata=task.metadata,
                )
                for task in request.tasks
            )
        return (
            DagTask("kb-match", kind="kb_match", prompt="Match the command to the local knowledge graph."),
            DagTask("repo-analysis", kind="repo_analysis", prompt="Inspect the repository implications."),
            DagTask("security-investigation", kind="security", prompt="Identify security and governance risks."),
            DagTask(
                "synthesis",
                dependencies=("kb-match", "repo-analysis", "security-investigation"),
                kind="synthesis",
                prompt="Synthesize the independent investigations into one execution brief.",
            ),
        )

    async def _tokens(
        self,
        task: DagTask,
        command: str,
        dependencies: Mapping[str, DagTaskResult],
    ) -> AsyncIterator[str]:
        if self._provider.api_key and self.settings.agent_runtime != "deterministic":
            try:
                async for token in self._provider_tokens(task, command, dependencies):
                    yield token
                return
            except Exception:
                logger.exception("Streaming provider failed; using the local runner")

        loop = asyncio.get_running_loop()
        output = await loop.run_in_executor(
            self._thread_pool,
            self._local_output,
            task,
            command,
            dependencies,
        )
        for start in range(0, len(output), 12):
            yield output[start : start + 12]
            await asyncio.sleep(0)

    async def _provider_tokens(
        self,
        task: DagTask,
        command: str,
        dependencies: Mapping[str, DagTaskResult],
    ) -> AsyncIterator[str]:
        dependency_context = "\n".join(
            f"[{task_id}] {result.output}" for task_id, result in dependencies.items()
        )
        payload = {
            "model": self._provider.model,
            "stream": True,
            "messages": [
                {
                    "role": "system",
                    "content": "You are one node in an in-memory DAG. Return a concise, evidence-oriented result.",
                },
                {
                    "role": "user",
                    "content": f"Task: {task.prompt or task.kind}\nCommand: {command}\nDependencies:\n{dependency_context}",
                },
            ],
        }
        headers = {"Authorization": f"Bearer {self._provider.api_key}"}
        async with self._http_client.stream(
            "POST",
            "/chat/completions",
            json=payload,
            headers=headers,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                try:
                    payload = json.loads(data)
                    token = payload["choices"][0]["delta"].get("content") or ""
                except (KeyError, IndexError, TypeError, json.JSONDecodeError):
                    continue
                if token:
                    yield token

    def _local_output(
        self,
        task: DagTask,
        command: str,
        dependencies: Mapping[str, DagTaskResult],
    ) -> str:
        if task.kind == "kb_match":
            snapshot = self.graph_snapshot()
            labels = ", ".join(node.label for node in snapshot.nodes[:5]) or "no indexed nodes"
            return f"Knowledge match for '{command}': {labels}."
        if task.kind == "repo_analysis":
            return f"Repository analysis prepared for '{command}' with file-backed state only."
        if task.kind == "security":
            return "Security investigation: validate path boundaries, command authority, and secret handling."
        if task.kind == "synthesis":
            joined = " ".join(result.output for result in dependencies.values())
            return f"Execution brief: {joined}"
        return task.prompt or f"Completed {task.id} for '{command}'."
