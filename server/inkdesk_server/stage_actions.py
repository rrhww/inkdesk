from __future__ import annotations

import asyncio
import logging
import shutil
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from inkdesk_server.deposit_service import DepositService
from inkdesk_server.mcp_services import ContextPackService
from inkdesk_server.run_service import RunService
from inkdesk_server.schemas import DevRunResponse
from inkdesk_server.security import ApiError
from inkdesk_server.vault import VaultService

try:
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover
    ChatOpenAI = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


# Inkdesk 仓库的技术栈上下文，注入 LLM prompt 避免生成错误的技术方案
INKDESK_TECH_STACK_CONTEXT = """## 仓库技术栈（Inkdesk）
- 后端：Python 3.12 + FastAPI + SQLAlchemy + PostgreSQL+pgvector（不是 Node.js/Prisma）
- 前端：Next.js 16 + React 19 + TypeScript（App Router，不是 Pages Router）
- 后端 ORM：SQLAlchemy 2.x，模型在 server/inkdesk_server/models.py
- 后端路由：server/inkdesk_server/main.py（FastAPI 路由）
- 前端页面：web/app/app/ 下按 App Router 约定组织
- 前端组件：web/components/
- 前端 API 封装：web/lib/research.ts（封装 fetchInkdeskJson/postInkdeskJson 调用后端 /api/*）
- 测试：后端 pytest（server/tests/），前端 vitest + playwright
- 运行：后端 uvicorn（端口 8080），前端 next dev（端口 3000）
"""


class SolutionDraftOutput(BaseModel):
    draft: str = Field(description="技术方案草案文本（Markdown）")
    risks: list[str] = Field(default_factory=list, description="主要风险点")


class ReviewChecklistOutput(BaseModel):
    checklist: list[str] = Field(description="审阅清单条目列表")
    summary: str = Field(default="", description="审阅总结")


class TestingChecklistOutput(BaseModel):
    checklist: list[str] = Field(description="测试清单条目列表")
    summary: str = Field(default="", description="测试总结")


def _extract_stage_payload(events: list[dict], stage: str, event_type: str) -> dict[str, Any] | None:
    """从事件列表中提取指定阶段和类型的最后一条 payload。"""
    for event in reversed(events):
        if event.get("stage") == stage and event.get("eventType") == event_type:
            payload = event.get("payload")
            if isinstance(payload, dict):
                return payload
    return None


@dataclass
class StageActionService:
    db: Session
    settings: Any  # Settings

    def _build_solution_llm(self):
        provider = self.settings.resolved_agent_provider
        if ChatOpenAI is None or not provider.api_key or self.settings.agent_runtime == "deterministic":
            return None
        method = "json_schema" if provider.structured_output_method == "json_schema" else "json_mode"
        llm = ChatOpenAI(
            model=provider.model,
            api_key=provider.api_key,
            base_url=provider.base_url,
            temperature=0.1,
            timeout=(
                self.settings.agent_connect_timeout_seconds,
                self.settings.agent_read_timeout_seconds,
            ),
        )
        return llm.with_structured_output(SolutionDraftOutput, method=method)

    def _render_solution_prompt(self, run: Any) -> str:
        context_summary = ""
        for event in reversed(run.events):
            if event.stage == "context" and event.eventType == "context_pack_generated":
                ctx = event.payload
                context_summary = (
                    f"  - Ask 历史: {ctx.get('askHistoryCount', 0)} 条\n"
                    f"  - 待审阅项: {ctx.get('pendingReviewCount', 0)} 个\n"
                    f"  - Wiki 关联: {ctx.get('wikiPageCount', 0)} 页"
                )
                break

        lines = [
            "You are the technical architect for Inkdesk.",
            "Based on the task and context, generate a concise technical solution draft in Simplified Chinese.",
            "The draft should include: approach, key files to modify, and implementation steps.",
            "",
            INKDESK_TECH_STACK_CONTEXT,
            "",
            f"## 任务类型\n{run.type}",
            f"## 任务标题\n{run.title}",
            f"## 目标\n{run.goal}",
        ]
        if run.repoContext:
            lines.append(f"## 仓库\n{run.repoContext}")
        if context_summary:
            lines.append(f"## 上下文摘要\n{context_summary}")
        lines.append("")
        lines.append("Respond in Simplified Chinese. Output a draft (Markdown) and a list of risks.")
        lines.append("Return only valid JSON with keys: draft (string), risks (array of strings).")
        return "\n".join(lines)

    def _deterministic_solution(self, run: Any) -> dict[str, Any]:
        """deterministic 模式下的模板方案。"""
        draft = (
            f"## 方案草案（deterministic）\n\n"
            f"### 任务\n{run.title}\n\n"
            f"### 目标\n{run.goal}\n\n"
            f"### 建议步骤\n"
            f"1. 分析现有代码结构\n"
            f"2. 确定需要修改的文件\n"
            f"3. 实现核心逻辑\n"
            f"4. 编写测试\n"
            f"5. 运行测试并验证\n"
        )
        if run.repoContext:
            draft += f"\n### 仓库\n{run.repoContext}\n"
        return {"draft": draft, "risks": ["deterministic 模式生成的草案，未经 LLM 推理"]}

    def generate_solution(self, run_id: str, workspace_id: str) -> DevRunResponse:
        run = RunService(self.db).get_run(run_id, workspace_id)

        if run.currentStage != "solution":
            raise ApiError(409, "INVALID_STAGE", f"Expected solution stage, got {run.currentStage}")

        llm = self._build_solution_llm()
        if llm is None:
            result = self._deterministic_solution(run)
        else:
            try:
                prompt = self._render_solution_prompt(run)
                output = llm.invoke(prompt)
                result = {"draft": output.draft, "risks": output.risks}
            except Exception:
                logger.exception("Solution LLM invocation failed; falling back to deterministic.")
                result = self._deterministic_solution(run)

        return RunService(self.db).add_event(
            run_id=run_id,
            stage="solution",
            event_type="solution_draft_generated",
            payload=result,
            workspace_id=workspace_id,
        )

    # ── Review ──

    def _build_review_llm(self):
        provider = self.settings.resolved_agent_provider
        if ChatOpenAI is None or not provider.api_key or self.settings.agent_runtime == "deterministic":
            return None
        method = "json_schema" if provider.structured_output_method == "json_schema" else "json_mode"
        llm = ChatOpenAI(
            model=provider.model,
            api_key=provider.api_key,
            base_url=provider.base_url,
            temperature=0.1,
            timeout=(
                self.settings.agent_connect_timeout_seconds,
                self.settings.agent_read_timeout_seconds,
            ),
        )
        return llm.with_structured_output(ReviewChecklistOutput, method=method)

    def _render_review_prompt(self, run: Any) -> str:
        solution_draft = ""
        for event in reversed(run.events):
            if event.stage == "solution" and event.eventType == "solution_draft_generated":
                solution_draft = event.payload.get("draft", "")
                break

        lines = [
            "You are the technical reviewer for Inkdesk.",
            "Based on the task and solution draft, generate a review checklist in Simplified Chinese.",
            "Each item should be a specific, checkable concern (e.g. '是否处理了空值情况', '是否覆盖了边界条件').",
            "",
            INKDESK_TECH_STACK_CONTEXT,
            "",
            f"## 任务类型\n{run.type}",
            f"## 任务标题\n{run.title}",
            f"## 目标\n{run.goal}",
        ]
        if solution_draft:
            lines.append(f"## 方案草案\n{solution_draft}")
        lines.append("")
        lines.append("Generate 3-6 checklist items. Also provide a brief summary of the review.")
        lines.append("Return only valid JSON with keys: checklist (array of strings), summary (string).")
        return "\n".join(lines)

    def _deterministic_review(self, run: Any) -> dict[str, Any]:
        solution_draft = ""
        for event in reversed(run.events):
            if event.stage == "solution" and event.eventType == "solution_draft_generated":
                solution_draft = event.payload.get("draft", "")
                break

        checklist = [
            "方案是否与任务目标一致？",
            "是否考虑了对现有功能的影响？",
            "是否覆盖了错误处理和边界情况？",
            "测试计划是否充分？",
        ]
        if solution_draft:
            checklist.insert(0, "方案中的实现路径是否可行？")
        return {"checklist": checklist, "summary": "deterministic 模式生成的审阅清单"}

    def generate_review_checklist(self, run_id: str, workspace_id: str) -> DevRunResponse:
        run = RunService(self.db).get_run(run_id, workspace_id)

        if run.currentStage != "review":
            raise ApiError(409, "INVALID_STAGE", f"Expected review stage, got {run.currentStage}")

        llm = self._build_review_llm()
        if llm is None:
            result = self._deterministic_review(run)
        else:
            try:
                prompt = self._render_review_prompt(run)
                output = llm.invoke(prompt)
                result = {"checklist": output.checklist, "summary": output.summary}
            except Exception:
                logger.exception("Review LLM invocation failed; falling back to deterministic.")
                result = self._deterministic_review(run)

        return RunService(self.db).add_event(
            run_id=run_id,
            stage="review",
            event_type="review_checklist_generated",
            payload=result,
            workspace_id=workspace_id,
        )

    # ── Coding ──

    @staticmethod
    def _claude_available() -> bool:
        return shutil.which("claude") is not None

    def _assemble_briefing(self, run: Any) -> str:
        solution_draft = ""
        for event in reversed(run.events):
            if event.stage == "solution" and event.eventType == "solution_draft_generated":
                solution_draft = event.payload.get("draft", "")
                break

        review_checklist: list[str] = []
        for event in reversed(run.events):
            if event.stage == "review" and event.eventType == "review_checklist_generated":
                review_checklist = event.payload.get("checklist", [])
                break

        lines = [
            "# Dev Run Coding Briefing",
            "",
            f"## 任务\n{run.title}",
            "",
            f"## 目标\n{run.goal}",
            "",
        ]
        if run.repoContext:
            lines.append(f"## 仓库\n{run.repoContext}")
            lines.append("")

        if solution_draft:
            lines.append(f"## 技术方案\n{solution_draft}")
            lines.append("")

        if review_checklist:
            lines.append("## 审阅要点")
            for item in review_checklist:
                lines.append(f"- {item}")
            lines.append("")

        lines.extend([
            "## 约束",
            "- 只修改与目标直接相关的文件",
            "- 不做无关重构",
            "- 遵循现有代码风格和命名约定",
            "- 修改后运行测试确认不破坏已有功能",
            "",
            "## 执行完成后",
            "请输出：改了哪些文件、核心逻辑、测试结果。",
        ])
        return "\n".join(lines)

    async def execute_coding(self, run_id: str, workspace_id: str) -> DevRunResponse:
        run = RunService(self.db).get_run(run_id, workspace_id)

        if run.currentStage != "coding":
            raise ApiError(409, "INVALID_STAGE", f"Expected coding stage, got {run.currentStage}")

        briefing = self._assemble_briefing(run)

        # 写入 briefing_prepared 事件
        run = RunService(self.db).add_event(
            run_id=run_id,
            stage="coding",
            event_type="coding_briefing_prepared",
            payload={"briefing": briefing},
            workspace_id=workspace_id,
        )

        # 检测 claude CLI
        if not self._claude_available():
            logger.warning("Claude Code CLI not found; writing placeholder result.")
            run = RunService(self.db).add_event(
                run_id=run_id,
                stage="coding",
                event_type="coding_result_submitted",
                payload={
                    "result": "[Claude Code CLI 未安装] 请手动执行 briefing 中的内容。",
                    "success": False,
                    "error": "claude CLI not found",
                },
                workspace_id=workspace_id,
            )
            return run

        # 启动 claude 子进程
        cwd = run.repoContext or "."
        try:
            proc = await asyncio.create_subprocess_exec(
                "claude", "-p", briefing, "--output-format", "text",
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=300
            )

            stdout_text = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()

            if proc.returncode == 0:
                payload = {
                    "result": stdout_text,
                    "success": True,
                    "error": None,
                }
            else:
                payload = {
                    "result": stdout_text,
                    "success": False,
                    "error": f"exit code {proc.returncode}: {stderr_text[:500]}",
                }
        except asyncio.TimeoutError:
            payload = {
                "result": "",
                "success": False,
                "error": "Claude Code execution timed out (300s)",
            }
        except Exception as e:
            payload = {
                "result": "",
                "success": False,
                "error": f"Failed to execute claude: {e}",
            }

        run = RunService(self.db).add_event(
            run_id=run_id,
            stage="coding",
            event_type="coding_result_submitted",
            payload=payload,
            workspace_id=workspace_id,
        )
        return run

    def get_coding_status(self, run_id: str, workspace_id: str) -> dict[str, Any]:
        run = RunService(self.db).get_run(run_id, workspace_id)

        briefing = None
        result = None
        error = None
        success = None

        for event in run.events:
            if event.eventType == "coding_briefing_prepared":
                briefing = event.payload.get("briefing")
            elif event.eventType == "coding_result_submitted":
                result = event.payload.get("result")
                error = event.payload.get("error")
                success = event.payload.get("success")

        if result is not None:
            status = "completed" if success else "failed"
        elif briefing is not None:
            status = "running"
        else:
            status = "idle"

        return {
            "status": status,
            "briefing": briefing,
            "result": result,
            "error": error,
            "success": success,
        }

    # ── Testing ──

    def _build_testing_llm(self):
        provider = self.settings.resolved_agent_provider
        if ChatOpenAI is None or not provider.api_key or self.settings.agent_runtime == "deterministic":
            return None
        method = "json_schema" if provider.structured_output_method == "json_schema" else "json_mode"
        llm = ChatOpenAI(
            model=provider.model,
            api_key=provider.api_key,
            base_url=provider.base_url,
            temperature=0.1,
            timeout=(
                self.settings.agent_connect_timeout_seconds,
                self.settings.agent_read_timeout_seconds,
            ),
        )
        return llm.with_structured_output(TestingChecklistOutput, method=method)

    def _render_testing_prompt(self, run: Any) -> str:
        coding_result = ""
        for event in reversed(run.events):
            if event.stage == "coding" and event.eventType == "coding_result_submitted":
                coding_result = event.payload.get("result", "")
                break

        lines = [
            "You are the test engineer for Inkdesk.",
            "Based on the task and the coding result, generate a testing checklist in Simplified Chinese.",
            "Each item should be a specific, checkable test concern (e.g. '单元测试是否覆盖了核心分支', '是否验证了错误路径').",
            "",
            INKDESK_TECH_STACK_CONTEXT,
            "",
            f"## 任务类型\n{run.type}",
            f"## 任务标题\n{run.title}",
            f"## 目标\n{run.goal}",
        ]
        if coding_result:
            lines.append(f"## 编码产出\n{coding_result}")
        lines.append("")
        lines.append("Generate 3-6 checklist items covering unit tests, integration tests, edge cases, and regression. Also provide a brief summary.")
        lines.append("Return only valid JSON with keys: checklist (array of strings), summary (string).")
        return "\n".join(lines)

    def _deterministic_testing(self, run: Any) -> dict[str, Any]:
        coding_result = ""
        for event in reversed(run.events):
            if event.stage == "coding" and event.eventType == "coding_result_submitted":
                coding_result = event.payload.get("result", "")
                break

        checklist = [
            "单元测试是否覆盖了核心逻辑分支？",
            "是否验证了错误处理和异常路径？",
            "是否覆盖了边界条件（空值、超长输入、并发）？",
            "回归测试是否通过，未破坏已有功能？",
        ]
        if coding_result:
            checklist.insert(0, "编码产出中的核心逻辑是否都有对应测试？")
        return {"checklist": checklist, "summary": "deterministic 模式生成的测试清单"}

    def generate_testing_checklist(self, run_id: str, workspace_id: str) -> DevRunResponse:
        run = RunService(self.db).get_run(run_id, workspace_id)

        if run.currentStage != "testing":
            raise ApiError(409, "INVALID_STAGE", f"Expected testing stage, got {run.currentStage}")

        llm = self._build_testing_llm()
        if llm is None:
            result = self._deterministic_testing(run)
        else:
            try:
                prompt = self._render_testing_prompt(run)
                output = llm.invoke(prompt)
                result = {"checklist": output.checklist, "summary": output.summary}
            except Exception:
                logger.exception("Testing LLM invocation failed; falling back to deterministic.")
                result = self._deterministic_testing(run)

        return RunService(self.db).add_event(
            run_id=run_id,
            stage="testing",
            event_type="testing_checklist_generated",
            payload=result,
            workspace_id=workspace_id,
        )

    def generate_context_pack(self, run_id: str, workspace_id: str) -> DevRunResponse:
        run = RunService(self.db).get_run(run_id, workspace_id)

        if run.currentStage != "context":
            raise ApiError(409, "INVALID_STAGE", f"Expected context stage, got {run.currentStage}")

        pack = ContextPackService(self.db).build(workspace_id, run_id)

        summary = {
            "wikiPageCount": 0,
            "askHistoryCount": len(pack.get("askHistory", [])),
            "pendingReviewCount": len(pack.get("relatedReviews", [])),
            "title": run.title,
            "goal": run.goal,
            "repoContext": run.repoContext,
        }

        return RunService(self.db).add_event(
            run_id=run_id,
            stage="context",
            event_type="context_pack_generated",
            payload=summary,
            workspace_id=workspace_id,
        )

    def create_deposit(self, run_id: str, workspace_id: str) -> DevRunResponse:
        run = RunService(self.db).get_run(run_id, workspace_id)

        if run.currentStage != "deposit":
            raise ApiError(409, "INVALID_STAGE", f"Expected deposit stage, got {run.currentStage}")

        # 收集各阶段产出（run.events 是 RunEventResponse 列表）
        stage_outputs: dict[str, Any] = {}
        for stage in ["context", "solution", "review", "coding", "testing"]:
            for event in reversed(run.events):
                if event.stage == stage and event.eventType == "stage_output":
                    if isinstance(event.payload, dict):
                        stage_outputs[stage] = event.payload
                    break

        deposit_payload = {
            "title": f"[Dev Run] {run.title}",
            "summary": run.goal,
            "understanding": run.goal,
            "stageOutputs": stage_outputs,
            "runType": run.type,
        }

        deposit_service = DepositService(self.db, VaultService(self.settings))
        result = deposit_service.deposit(
            workspace_id=workspace_id,
            source="stage_output",
            payload=deposit_payload,
            run_id=run_id,
            stage="deposit",
        )

        return RunService(self.db).add_event(
            run_id=run_id,
            stage="deposit",
            event_type="deposit_created",
            payload={"reviewId": result.reviewId, "isNew": result.isNew},
            workspace_id=workspace_id,
        )
