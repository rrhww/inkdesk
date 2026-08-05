from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Mapping

import httpx
import yaml

from inkdesk_server.core.config import Settings
from inkdesk_server.engine import DualQueueSsePipeline, PipelineItem
from inkdesk_server.graph_index import GraphSnapshot
from inkdesk_server.harness.models import WorkflowStage, WorkflowStageResult
from inkdesk_server.harness.scheduler import WorkflowScheduler
from inkdesk_server.schemas import SkillRunRequest


logger = logging.getLogger(__name__)

MAX_KNOWLEDGE_BYTES = 128 * 1024
MAX_REPOSITORY_BYTES = 200 * 1024
MAX_TRACKED_PATHS = 5000
MAX_SOURCE_FILES = 20
REQUIRED_SECTIONS = (
    "方案概述",
    "模块职责",
    "接口设计",
    "数据流",
    "风险",
    "测试范围",
)
SKIPPED_PARTS = {
    ".git",
    ".idea",
    ".next",
    ".pytest_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}
SKIPPED_SUFFIXES = {
    ".7z",
    ".bin",
    ".class",
    ".dll",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jar",
    ".jpeg",
    ".jpg",
    ".lock",
    ".pdf",
    ".png",
    ".pyc",
    ".so",
    ".tar",
    ".webp",
    ".woff",
    ".woff2",
    ".zip",
}
SECRET_NAME_PATTERN = re.compile(
    r"(^|[._-])(env|secret|secrets|credential|credentials|private[-_]?key)([._-]|$)",
    re.IGNORECASE,
)


class SkillExecutionError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class TechSolutionRuntime:
    def __init__(
        self,
        settings: Settings,
        graph_snapshot: Callable[[], GraphSnapshot],
        graph_refresh: Callable[[str], GraphSnapshot],
        runtime_event_sink: Callable[[str, Mapping[str, Any]], None] | None = None,
    ):
        self.settings = settings
        self.graph_snapshot = graph_snapshot
        self.graph_refresh = graph_refresh
        self.runtime_event_sink = runtime_event_sink
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

    def preflight(self, skill_id: str, request: SkillRunRequest) -> None:
        if skill_id != "tech-solution":
            raise SkillExecutionError("SKILL_NOT_FOUND", f"Skill '{skill_id}' is not available.")

        contract_path = Path(self.settings.skills_root) / skill_id / "contract.json"
        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SkillExecutionError("SKILL_UNAVAILABLE", "The tech-solution Skill is not installed.") from exc
        if contract.get("status") != "active":
            raise SkillExecutionError("SKILL_INACTIVE", "The tech-solution Skill is not active.")
        if not request.inputs.requirement.strip():
            raise SkillExecutionError("INVALID_REQUIREMENT", "The requirement cannot be empty.")
        vault_root = Path(self.settings.vault_root)
        if not vault_root.is_dir():
            raise SkillExecutionError("VAULT_NOT_INITIALIZED", "The configured Vault does not exist.")

        runtime = self._runtime_mode()
        if runtime == "provider" and not self._provider.api_key:
            raise SkillExecutionError(
                "PROVIDER_NOT_CONFIGURED",
                f"No API key is configured for provider profile '{self._provider.profile}'.",
            )

    async def stream(self, request: SkillRunRequest) -> AsyncIterator[PipelineItem]:
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
        request: SkillRunRequest,
        queue: asyncio.Queue[PipelineItem | None],
    ) -> None:
        source_reference = self._source_reference(request.inputs.sourcePath)
        source_node_id = self._source_node_id(source_reference, request.inputs.sourceTitle)
        await queue.put(PipelineItem("stream.open", {"skillId": "tech-solution"}))
        if source_node_id and self.runtime_event_sink is not None:
            self.runtime_event_sink("node.active", {"nodeId": source_node_id, "skillId": "tech-solution"})

        try:
            tasks = self._build_tasks()
            scheduler = WorkflowScheduler(max_concurrency=request.maxConcurrency)

            async def on_event(event) -> None:
                legacy_event_type = event.type.replace("stage.", "task.").replace("workflow.", "dag.")
                if legacy_event_type in {"task.started", "task.completed", "task.failed"}:
                    await queue.put(
                        PipelineItem(
                            legacy_event_type,
                            {
                                "taskId": event.stage_id,
                                "timestamp": event.timestamp,
                                **dict(event.data),
                            },
                        )
                    )

            async def runner(task: WorkflowStage, dependencies: Mapping[str, WorkflowStageResult]) -> str:
                output_parts: list[str] = []
                async for token in self._task_tokens(
                    task,
                    request,
                    dependencies,
                    source_reference,
                ):
                    output_parts.append(token)
                    await queue.put(PipelineItem("token", {"taskId": task.id, "token": token}))
                return "".join(output_parts)

            result = await scheduler.execute(tasks, runner, on_event)
            document = result.results["synthesis"].output
            findings = validate_solution_document(document, source_reference)
            repaired = False
            if findings and self._runtime_mode() == "provider":
                repaired = True
                document = await self._repair_document(document, findings, request, source_reference, queue)
                findings = validate_solution_document(document, source_reference)
            if findings:
                raise SkillExecutionError(
                    "ARTIFACT_VALIDATION_FAILED",
                    "Generated artifact failed validation: " + "; ".join(findings),
                )

            await queue.put(
                PipelineItem(
                    "artifact.validated",
                    {"source": source_reference, "repaired": repaired},
                )
            )
            output_path = self._write_artifact(document, request, source_reference)
            relative_output = output_path.relative_to(Path(self.settings.vault_root).resolve()).as_posix()
            await asyncio.to_thread(self.graph_refresh, f"artifact.written:{relative_output}")
            await queue.put(
                PipelineItem(
                    "artifact.written",
                    {"path": str(output_path), "relativePath": relative_output},
                )
            )
            await queue.put(
                PipelineItem(
                    "result",
                    {
                        "skillId": "tech-solution",
                        "artifactPath": str(output_path),
                        "completedOrder": list(result.completed_order),
                        "durationMs": round(result.duration_ms, 3),
                    },
                )
            )
        except SkillExecutionError as exc:
            await queue.put(PipelineItem("stream.error", {"code": exc.code, "message": exc.message}))
        except httpx.HTTPStatusError as exc:
            logger.warning("Provider returned HTTP %s", exc.response.status_code)
            await queue.put(
                PipelineItem(
                    "stream.error",
                    {
                        "code": "PROVIDER_ERROR",
                        "message": f"Provider request failed with HTTP {exc.response.status_code}.",
                    },
                )
            )
        except (httpx.HTTPError, TimeoutError) as exc:
            logger.warning("Provider request failed: %s", type(exc).__name__)
            await queue.put(
                PipelineItem(
                    "stream.error",
                    {"code": "PROVIDER_ERROR", "message": "Provider request failed."},
                )
            )
        except Exception:
            logger.exception("tech-solution execution failed")
            await queue.put(
                PipelineItem(
                    "stream.error",
                    {"code": "INTERNAL_ERROR", "message": "Skill execution failed."},
                )
            )
        finally:
            if source_node_id and self.runtime_event_sink is not None:
                self.runtime_event_sink("node.idle", {"nodeId": source_node_id, "skillId": "tech-solution"})
            await queue.put(None)

    def _build_tasks(self) -> tuple[WorkflowStage, ...]:
        investigations = (
            WorkflowStage("requirement-analysis", kind="requirement", prompt="Analyze scope and acceptance criteria."),
            WorkflowStage("knowledge-analysis", kind="knowledge", prompt="Find relevant Vault knowledge and constraints."),
            WorkflowStage("repository-analysis", kind="repository", prompt="Inspect relevant tracked repository files."),
            WorkflowStage("security-analysis", kind="security", prompt="Identify security and governance risks."),
        )
        return investigations + (
            WorkflowStage(
                "synthesis",
                dependencies=tuple(task.id for task in investigations),
                kind="synthesis",
                prompt="Produce the complete technical solution document.",
            ),
        )

    async def _task_tokens(
        self,
        task: WorkflowStage,
        request: SkillRunRequest,
        dependencies: Mapping[str, WorkflowStageResult],
        source_reference: str,
    ) -> AsyncIterator[str]:
        context = ""
        if task.kind == "knowledge":
            context = await asyncio.to_thread(self._knowledge_context, request.inputs.requirement)
        elif task.kind == "repository":
            context = await asyncio.to_thread(self._repository_context, request.inputs.requirement)
        elif task.kind == "synthesis":
            context = await asyncio.to_thread(self._skill_context)

        if self._runtime_mode() == "provider":
            prompt = self._provider_prompt(task, request, dependencies, source_reference, context)
            async for token in self._provider_tokens(prompt):
                yield token
            return

        output = self._deterministic_output(task, request, dependencies, source_reference, context)
        for start in range(0, len(output), 96):
            yield output[start : start + 96]
            await asyncio.sleep(0)

    def _runtime_mode(self) -> str:
        runtime = (self.settings.agent_runtime or "deterministic").strip().lower()
        return "deterministic" if runtime == "deterministic" else "provider"

    def _provider_prompt(
        self,
        task: WorkflowStage,
        request: SkillRunRequest,
        dependencies: Mapping[str, WorkflowStageResult],
        source_reference: str,
        context: str,
    ) -> str:
        dependency_context = "\n\n".join(
            f"## {task_id}\n{result.output}" for task_id, result in dependencies.items()
        )
        if task.kind == "synthesis":
            return (
                "Write a complete Chinese Markdown technical solution. Return Markdown only. "
                "It must start with YAML frontmatter containing title, type: tech-solution, status: generated, "
                f"generatedBy: inkdesk, and source: {source_reference}. Include a source backlink "
                f"[[{source_reference}|{request.inputs.sourceTitle}]]. Required headings are 方案概述, 模块职责, "
                "接口设计, 数据流, 风险, 测试范围. Include a fenced Mermaid sequenceDiagram.\n\n"
                f"Requirement:\n{request.inputs.requirement}\n\nInvestigations:\n{dependency_context}\n\n"
                f"Skill resources:\n{context}"
            )
        return (
            f"Task: {task.prompt}\nRequirement:\n{request.inputs.requirement}\n\n"
            f"Available context (may be empty):\n{context}\n\n"
            "Return concise evidence-oriented analysis. Do not invent files or interfaces."
        )

    async def _provider_tokens(self, prompt: str) -> AsyncIterator[str]:
        payload = {
            "model": self._provider.model,
            "stream": True,
            "messages": [
                {
                    "role": "system",
                    "content": "You are the NeuWeave tech-solution execution engine.",
                },
                {"role": "user", "content": prompt},
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

    async def _repair_document(
        self,
        document: str,
        findings: list[str],
        request: SkillRunRequest,
        source_reference: str,
        queue: asyncio.Queue[PipelineItem | None],
    ) -> str:
        prompt = (
            "Repair this Markdown technical solution. Return the full corrected Markdown only. "
            f"Keep source {source_reference} and backlink [[{source_reference}|{request.inputs.sourceTitle}]]. "
            f"Validation findings: {'; '.join(findings)}\n\n{document}"
        )
        parts: list[str] = []
        async for token in self._provider_tokens(prompt):
            parts.append(token)
            await queue.put(PipelineItem("token", {"taskId": "artifact-repair", "token": token}))
        return "".join(parts)

    def _deterministic_output(
        self,
        task: WorkflowStage,
        request: SkillRunRequest,
        dependencies: Mapping[str, WorkflowStageResult],
        source_reference: str,
        context: str,
    ) -> str:
        if task.kind == "requirement":
            return f"目标与验收依据来自 {request.inputs.sourceTitle}；保持 MVP 范围并以可观察闭环为准。"
        if task.kind == "knowledge":
            return context or "未找到相关 Vault 文档；方案需显式记录知识缺口。"
        if task.kind == "repository":
            return context or "未找到可读取的相关受 Git 管理文件。"
        if task.kind == "security":
            return "保护路径边界、密钥、Provider 失败关闭、产物冲突与原子写入。"
        return self._deterministic_document(request, dependencies, source_reference)

    def _deterministic_document(
        self,
        request: SkillRunRequest,
        dependencies: Mapping[str, WorkflowStageResult],
        source_reference: str,
    ) -> str:
        title = f"{request.inputs.sourceTitle} 技术方案"
        evidence = "\n".join(f"- **{name}**：{result.output}" for name, result in dependencies.items())
        return f"""---
title: {json.dumps(title, ensure_ascii=False)}
type: tech-solution
status: generated
generatedBy: inkdesk
source: {json.dumps(source_reference, ensure_ascii=False)}
sourceTitle: {json.dumps(request.inputs.sourceTitle, ensure_ascii=False)}
---
# {title}

来源需求：[[{source_reference}|{request.inputs.sourceTitle}]]

## 1. 方案概述

围绕 PRD 建立可验证的最小实现闭环。范围以需求原文为准，不扩展未声明的业务能力。

### 调研依据

{evidence}

## 2. 模块职责

| 模块 | 职责 | 输入 | 输出 |
| --- | --- | --- | --- |
| CLI | 校验 PRD 并消费 SSE | Markdown 路径 | 执行状态与产物路径 |
| Skill Runtime | 调度分析与综合任务 | 需求和受限上下文 | 合规技术方案 |
| Graph Index | 刷新 Vault 拓扑并推送事件 | 新 Markdown | 节点、依赖边和 SSE 快照 |

## 3. 接口设计

- `POST /api/skills/tech-solution/stream`：接收 `inputs` 与 `maxConcurrency`，返回命名 SSE 事件。
- 错误使用稳定错误码；流启动后的错误由 `stream.error` 表达。

## 4. 数据流

```mermaid
sequenceDiagram
  participant CLI
  participant Skill as Skill Runtime
  participant Vault
  participant Graph as Graph Index
  participant UI as Browser
  CLI->>Skill: PRD inputs
  Skill->>Skill: 并发分析与方案综合
  Skill->>Vault: 原子写入技术方案
  Skill->>Graph: 显式刷新
  Graph-->>UI: graph.updated SSE
```

## 5. 风险

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| Provider 超时或限流 | 生成中断 | 失败关闭并返回稳定错误码 |
| 同名人工文档 | 误覆盖 | 校验 `generatedBy` 与来源一致后才覆盖 |
| 上下文泄密 | 凭据暴露 | 跳过密钥、环境文件、依赖与二进制目录 |

## 6. 测试范围

- 单元测试覆盖 CLI、DAG 顺序、Provider 失败、验证与原子写入。
- 集成测试验证写入后图谱节点和 PRD 依赖边。
- 浏览器测试验证节点脉冲、扩张、Markdown 与 Mermaid 阅读。
"""

    def _knowledge_context(self, requirement: str) -> str:
        snapshot = self.graph_snapshot()
        keywords = _keywords(requirement)
        candidates = [node for node in snapshot.nodes if node.source == "vault" and node.status != "missing"]
        candidates.sort(
            key=lambda node: (
                -sum(keyword in f"{node.label} {node.summary}".casefold() for keyword in keywords),
                node.path.casefold(),
            )
        )
        total = 0
        chunks: list[str] = []
        vault_root = Path(self.settings.vault_root).resolve()
        for node in candidates[:10]:
            path = (vault_root / node.path).resolve()
            if not _is_within(path, vault_root) or not _safe_context_path(path, vault_root):
                continue
            content = _read_limited_text(path, MAX_KNOWLEDGE_BYTES - total)
            if not content:
                continue
            chunk = f"### {node.path}\n{content}"
            chunks.append(chunk)
            total += len(content.encode("utf-8"))
            if total >= MAX_KNOWLEDGE_BYTES:
                break
        return "\n\n".join(chunks)

    def _repository_context(self, requirement: str) -> str:
        repo_root = self._repo_root()
        if not repo_root.is_dir():
            return ""
        try:
            completed = subprocess.run(
                ["git", "-C", str(repo_root), "ls-files", "-z"],
                check=True,
                capture_output=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        tracked = completed.stdout.decode("utf-8", errors="replace").split("\0")[:MAX_TRACKED_PATHS]
        keywords = _keywords(requirement)
        safe_paths = [path for path in tracked if path and _safe_relative_repo_path(path)]
        safe_paths.sort(
            key=lambda path: (
                -sum(keyword in path.casefold() for keyword in keywords),
                path.casefold(),
            )
        )
        total = 0
        chunks: list[str] = []
        for relative in safe_paths:
            path = (repo_root / relative).resolve()
            if not _is_within(path, repo_root):
                continue
            content = _read_limited_text(path, MAX_REPOSITORY_BYTES - total)
            if not content:
                continue
            chunks.append(f"### {relative.replace(os.sep, '/')}\n{content}")
            total += len(content.encode("utf-8"))
            if len(chunks) >= MAX_SOURCE_FILES or total >= MAX_REPOSITORY_BYTES:
                break
        return "\n\n".join(chunks)

    def _skill_context(self) -> str:
        package_root = (Path(self.settings.skills_root) / "tech-solution").resolve()
        candidates = [
            package_root / "references" / "architecture-patterns.md",
            package_root / "templates" / "solution-template.md",
        ]
        chunks: list[str] = []
        total = 0
        for path in candidates:
            if not _is_within(path, package_root):
                continue
            content = _read_limited_text(path, MAX_KNOWLEDGE_BYTES - total)
            if not content:
                continue
            chunks.append(f"### {path.relative_to(package_root).as_posix()}\n{content}")
            total += len(content.encode("utf-8"))
        return "\n\n".join(chunks)

    def _source_reference(self, source_path: str) -> str:
        candidate = Path(source_path).expanduser()
        if not candidate.is_absolute():
            candidate = self._repo_root() / candidate
        candidate = candidate.resolve()
        for root in (self._repo_root(), Path(self.settings.vault_root).resolve()):
            if _is_within(candidate, root):
                return candidate.relative_to(root).as_posix()
        return candidate.name

    def _source_node_id(self, source_reference: str, source_title: str) -> str | None:
        for node in self.graph_snapshot().nodes:
            if node.path.casefold() == source_reference.casefold() or node.label.casefold() == source_title.casefold():
                return node.id
        return None

    def _repo_root(self) -> Path:
        if self.settings.repo_root:
            return Path(self.settings.repo_root).expanduser().resolve()
        return Path(__file__).resolve().parents[2]

    def _write_artifact(
        self,
        document: str,
        request: SkillRunRequest,
        source_reference: str,
    ) -> Path:
        stem = _safe_stem(Path(request.inputs.sourcePath).stem)
        vault_root = Path(self.settings.vault_root).resolve()
        output_dir = (vault_root / "wiki" / "generated").resolve()
        if not _is_within(output_dir, vault_root):
            raise SkillExecutionError("INVALID_ARTIFACT_PATH", "Artifact path escapes the Vault.")
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / f"{stem}-tech-solution.md"
        if target.exists():
            metadata = _frontmatter(target.read_text(encoding="utf-8"))
            if metadata.get("generatedBy") != "inkdesk" or str(metadata.get("source")) != source_reference:
                raise SkillExecutionError(
                    "ARTIFACT_CONFLICT",
                    f"Refusing to overwrite non-Inkdesk or different-source artifact: {target.name}",
                )

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=output_dir,
                prefix=f".{target.stem}-",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(document.rstrip() + "\n")
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, target)
            temporary_path = None
            return target
        except SkillExecutionError:
            raise
        except OSError as exc:
            raise SkillExecutionError("ARTIFACT_WRITE_FAILED", "Could not atomically write the artifact.") from exc
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)


def validate_solution_document(document: str, source_reference: str) -> list[str]:
    findings: list[str] = []
    metadata = _frontmatter(document)
    if not metadata:
        findings.append("missing YAML frontmatter")
    else:
        if metadata.get("generatedBy") != "inkdesk":
            findings.append("generatedBy must be inkdesk")
        if str(metadata.get("source")) != source_reference:
            findings.append("source does not match the PRD")
        if not metadata.get("title"):
            findings.append("frontmatter title is required")
    backlink = re.compile(r"\[\[" + re.escape(source_reference) + r"(?:\|[^\]]+)?\]\]", re.IGNORECASE)
    if not backlink.search(document):
        findings.append("missing source backlink")
    for section in REQUIRED_SECTIONS:
        if not re.search(r"^#{2,4}\s+(?:\d+(?:\.\d+)?[.、]?\s*)?.*" + re.escape(section), document, re.MULTILINE):
            findings.append(f"missing section: {section}")
    if not re.search(r"```mermaid\s+sequenceDiagram\b", document, re.IGNORECASE):
        findings.append("missing Mermaid sequenceDiagram")
    return findings


def _frontmatter(document: str) -> dict[str, Any]:
    normalized = document.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return {}
    end = normalized.find("\n---\n", 4)
    if end < 0:
        return {}
    try:
        value = yaml.safe_load(normalized[4:end]) or {}
    except yaml.YAMLError:
        return {}
    return value if isinstance(value, dict) else {}


def _safe_stem(value: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip(".-").lower()
    if not stem or stem in {"con", "prn", "aux", "nul"}:
        return "requirement"
    return stem[:120]


def _keywords(text: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            token.casefold()
            for token in re.findall(r"[A-Za-z0-9_-]{3,}|[\u4e00-\u9fff]{2,}", text)
        )
    )[:32]


def _safe_relative_repo_path(relative: str) -> bool:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        return False
    if any(part.casefold() in SKIPPED_PARTS for part in path.parts):
        return False
    if SECRET_NAME_PATTERN.search(path.name) or path.name.casefold().startswith(".env"):
        return False
    if path.suffix.casefold() in SKIPPED_SUFFIXES:
        return False
    return True


def _safe_context_path(path: Path, root: Path) -> bool:
    if not _is_within(path, root):
        return False
    relative = path.relative_to(root)
    return _safe_relative_repo_path(relative.as_posix())


def _read_limited_text(path: Path, remaining_bytes: int) -> str:
    if remaining_bytes <= 0 or not path.is_file():
        return ""
    try:
        raw = path.read_bytes()[: min(remaining_bytes, 64 * 1024)]
    except OSError:
        return ""
    if b"\0" in raw:
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return ""


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
