from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from inkdesk_server.deposit_service import DepositService
from inkdesk_server.hard_gate_checker import HardGateChecker
from inkdesk_server.mcp_services import ContextPackService, VaultSearchService
from inkdesk_server.run_service import RunService
from inkdesk_server.schemas import DevRunResponse
from inkdesk_server.security import ApiError
from inkdesk_server.skill_loader import LoadedSkill, get_skill_loader
from inkdesk_server.vault import VaultService

try:
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover
    ChatOpenAI = None  # type: ignore[assignment]

# Claude Agent SDK（可选依赖，未安装时 coding 阶段降级为不可用）
try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        PermissionResultAllow,
        PermissionResultDeny,
        ResultMessage,
        StreamEvent,
        TextBlock,
        ToolPermissionContext,
        ToolResultBlock,
        ToolUseBlock,
        UserMessage,
        query as claude_query,
    )
    _CLAUDE_SDK_AVAILABLE = True
except Exception:  # pragma: no cover
    ClaudeAgentOptions = None  # type: ignore[assignment,misc]
    claude_query = None  # type: ignore[assignment]
    AssistantMessage = None  # type: ignore[assignment]
    ResultMessage = None  # type: ignore[assignment]
    StreamEvent = None  # type: ignore[assignment]
    TextBlock = None  # type: ignore[assignment]
    ToolPermissionContext = None  # type: ignore[assignment]
    ToolResultBlock = None  # type: ignore[assignment]
    ToolUseBlock = None  # type: ignore[assignment]
    UserMessage = None  # type: ignore[assignment]
    PermissionResultAllow = None  # type: ignore[assignment]
    PermissionResultDeny = None  # type: ignore[assignment]
    _CLAUDE_SDK_AVAILABLE = False

from inkdesk_server.coding_session import (
    PermissionResponse,
    get_session_manager,
    is_dangerous_tool,
)

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

    # ── Skill-driven 基础设施 ──

    def _get_skill(self, stage: str) -> LoadedSkill | None:
        """加载 stage 对应的 Skill package（SKILL.md + contract + references/templates）。"""
        return get_skill_loader(self.settings.vault_root).load(stage)

    def _check_hard_gates(self, run_id: str, stage: str) -> None:
        """执行 stage action 前检查 Skill contract 定义的 hard gates。

        失败时抛 ApiError(409, "HARD_GATE_FAILED", ...)。
        Skill package 不存在时跳过（向后兼容）。
        """
        loader = get_skill_loader(self.settings.vault_root)
        checker = HardGateChecker(
            skill_loader=loader,
            vault_service=VaultService(self.settings),
            db=self.db,
            vault_root=Path(self.settings.vault_root).expanduser().resolve(),
        )
        result = checker.check(run_id, stage)
        if not result.passed:
            messages = "; ".join(f"{f.gate_id}: {f.message}" for f in result.failures)
            raise ApiError(409, "HARD_GATE_FAILED", messages)

    def _render_skill_context(self, stage: str) -> str:
        """把 SKILL.md + references + templates 渲染成 prompt 注入段落。

        注入格式：
            ## Skill 指南（<skill_id>）
            <SKILL.md 内容>
            ## 参考资料
            ### <filename>
            <content>
            ## 模板
            ### <filename>
            <content>
        """
        skill = self._get_skill(stage)
        if skill is None:
            return ""

        lines: list[str] = [
            f"## Skill 指南（{skill.skill_id}）",
            "请严格遵循以下 Skill 定义的主流程、Hard Gates、关键决策点和输出规格：",
            "",
            skill.skill_md.strip(),
        ]

        if skill.references:
            lines.append("")
            lines.append("## 参考资料")
            for filename, content in skill.references.items():
                lines.append(f"### {filename}")
                lines.append(content.strip())
                lines.append("")

        if skill.templates:
            lines.append("## 模板")
            for filename, content in skill.templates.items():
                lines.append(f"### {filename}")
                lines.append(content.strip())
                lines.append("")

        return "\n".join(lines)

    def _search_wiki_for_context(self, query: str, limit: int = 5) -> str:
        """Query 操作：从 wiki/raw 检索相关页面，注入 prompt 作为预编译知识。

        文章思想：知识在 write-time 合成（wiki），query-time 直接读结论。
        wiki/ 存放已审阅的合成知识，raw/ 存放待 ingest 的原始资料。
        wiki 无命中时回退到 raw，保证未合成但有原始资料时也能提供上下文。
        """
        if not query or not query.strip():
            return ""
        vault = VaultService(self.settings)
        search_service = VaultSearchService(vault=vault)
        results = search_service.search(query, directories=("wiki",))[:limit]
        if not results:
            # wiki 无命中时回退到 raw 目录
            results = search_service.search(query, directories=("raw",))[:limit]
        if not results:
            return ""

        lines = ["## 相关 Wiki 页面（预编译知识）"]
        for r in results:
            lines.append(f"### {r['path']}")
            lines.append(r["snippet"])
            lines.append("")
        return "\n".join(lines)

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
        ]
        # Skill 指南注入（SKILL.md + references + templates）
        skill_ctx = self._render_skill_context("solution")
        if skill_ctx:
            lines.append(skill_ctx)
            lines.append("")
        # Query 操作：注入相关 wiki 预编译知识
        wiki_ctx = self._search_wiki_for_context(f"{run.title} {run.goal}")
        if wiki_ctx:
            lines.append(wiki_ctx)
            lines.append("")
        lines.extend([
            f"## 任务类型\n{run.type}",
            f"## 任务标题\n{run.title}",
            f"## 目标\n{run.goal}",
        ])
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

        self._check_hard_gates(run_id, "solution")

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
        ]
        # Skill 指南注入
        skill_ctx = self._render_skill_context("review")
        if skill_ctx:
            lines.append(skill_ctx)
            lines.append("")
        # Query 操作：注入相关 wiki 预编译知识
        wiki_ctx = self._search_wiki_for_context(f"{run.title} {solution_draft[:200]}")
        if wiki_ctx:
            lines.append(wiki_ctx)
            lines.append("")
        lines.extend([
            f"## 任务类型\n{run.type}",
            f"## 任务标题\n{run.title}",
            f"## 目标\n{run.goal}",
        ])
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

        self._check_hard_gates(run_id, "review")

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
        # 优先用 Claude Agent SDK（内置 CLI，不依赖系统 PATH）；
        # SDK 不可用时回退到检测系统 claude 命令（保留向后兼容）。
        if _CLAUDE_SDK_AVAILABLE:
            return True
        return shutil.which("claude") is not None

    @staticmethod
    def _load_mcp_servers() -> dict[str, Any]:
        """从 ~/.claude/settings.json 读取 mcpServers 字段。

        setting_sources=[] 禁用了 settings.json 加载（避免 CLAUDE.md 学生模式），
        但 MCP servers（filesystem/memory 等）是工具配置不是行为设置，
        手动加载以保持与 CLI 体验一致。只读 mcpServers，不读 env/auth。

        文件缺失或格式错误时返回空 dict（SDK 会正常工作，只是没有 MCP 工具）。
        """
        settings_path = Path.home() / ".claude" / "settings.json"
        try:
            content = settings_path.read_text(encoding="utf-8")
            data = json.loads(content)
            servers = data.get("mcpServers", {})
            # 过滤掉 disabled 的 server
            return {
                name: cfg
                for name, cfg in servers.items()
                if isinstance(cfg, dict) and not cfg.get("disabled", False)
            }
        except (OSError, json.JSONDecodeError):
            logger.debug("未找到或无法解析 %s，跳过 MCP servers 加载", settings_path)
            return {}

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
        ]
        # Skill 指南注入（coding SKILL.md 含 hard gates、主流程、guard rails）
        skill_ctx = self._render_skill_context("coding")
        if skill_ctx:
            lines.append(skill_ctx)
            lines.append("")
        # Query 操作：注入相关 wiki 预编译知识
        wiki_ctx = self._search_wiki_for_context(f"{run.title} {run.goal}")
        if wiki_ctx:
            lines.append(wiki_ctx)
            lines.append("")
        lines.extend([
            f"## 任务\n{run.title}",
            "",
            f"## 目标\n{run.goal}",
            "",
        ])
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

        self._check_hard_gates(run_id, "coding")

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

        # 子进程 cwd：repoContext 是 briefing 里的标签字符串（如 "inkdesk"），不是路径。
        # 用配置项 INKDESK_REPO_ROOT；未配置则用后端进程当前目录。
        cwd = self.settings.repo_root or "."

        # 交互模式：非阻塞启动后台任务，前端通过 SSE 获取实时对话和权限弹窗
        if self.settings.claude_interactive_mode and _CLAUDE_SDK_AVAILABLE:
            manager = get_session_manager()
            if manager.is_active(run_id):
                raise ApiError(409, "CODING_IN_PROGRESS", "coding session already running")
            session = manager.get_or_create(
                run_id,
                permission_timeout=float(self.settings.claude_permission_timeout_seconds),
            )
            session.task = asyncio.create_task(
                self._run_claude_cli_streaming(run_id, workspace_id, briefing, cwd)
            )
            # 立即返回，让前端连 SSE
            return run

        # 非交互模式：同步等待 SDK 完成（bypassPermissions，无前端交互）
        payload = await self._run_claude_cli(briefing, cwd)
        run = RunService(self.db).add_event(
            run_id=run_id,
            stage="coding",
            event_type="coding_result_submitted",
            payload=payload,
            workspace_id=workspace_id,
        )
        return run

    async def _run_claude_cli(self, briefing: str, cwd: str) -> dict[str, Any]:
        """调用 Claude Code 执行 coding 任务，返回 coding_result_submitted payload。

        优先使用 Claude Agent SDK（claude-agent-sdk 包），SDK 通过 stream-json 协议与内置 CLI
        子进程通信，规避了我们之前手写 subprocess 遇到的两类问题：
        1. MCP 孙进程继承 stdout/stderr pipe handle 导致 communicate() 永久阻塞
        2. 仓库根目录的 CLAUDE.md（如 student-driver 模式）让 Claude 卡住等用户输入

        通过 setting_sources=[] 禁用所有文件系统设置（CLAUDE.md / skills / 用户 settings），
        permission_mode="bypassPermissions" 自动批准工具调用（仅限 sandbox worktree 场景）。

        SDK 不可用时（包未安装）返回明确错误，不再回退到脆弱的手写 subprocess 实现。
        """
        if not _CLAUDE_SDK_AVAILABLE:
            return {
                "result": "",
                "success": False,
                "error": "claude-agent-sdk 未安装，无法执行 coding 阶段。请运行 pip install claude-agent-sdk",
            }

        # 构建 SDK 选项
        env: dict[str, str] = {}
        if self.settings.claude_api_base_url:
            env["ANTHROPIC_BASE_URL"] = self.settings.claude_api_base_url
        if self.settings.claude_api_token:
            env["ANTHROPIC_AUTH_TOKEN"] = self.settings.claude_api_token
        # 模型映射：setting_sources=[] 禁用了 settings.json，
        # 必须显式传入 ccswitch 的模型映射，否则 Claude Code 用默认 claude-* 模型名请求，
        # DeepSeek 等第三方端点不识别 → 工具调用空转。
        if self.settings.claude_model:
            env["ANTHROPIC_MODEL"] = self.settings.claude_model
        if self.settings.claude_default_sonnet_model:
            env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = self.settings.claude_default_sonnet_model
        if self.settings.claude_default_haiku_model:
            env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = self.settings.claude_default_haiku_model
        if self.settings.claude_default_opus_model:
            env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = self.settings.claude_default_opus_model

        # 加载 MCP servers：setting_sources=[] 禁用了 ~/.claude/settings.json 加载，
        # 但 MCP servers（filesystem/memory 等）是工具配置不是行为设置，
        # 手动加载以保持与 CLI 体验一致。只读 mcpServers 字段，不读 env/auth。
        mcp_servers = self._load_mcp_servers()

        options = ClaudeAgentOptions(
            cwd=cwd,
            # 禁用所有文件系统设置（CLAUDE.md / ~/.claude/settings.json / skills）
            # 避免 worktree 里的 student-driver 模式让 Claude 卡住等用户输入
            setting_sources=[],
            # 自动批准所有工具调用（仅限 sandbox worktree，dogfooding 场景安全）
            permission_mode="bypassPermissions",
            # 禁用 Claude Code 内置 sandbox：默认 sandbox 会阻止文件写入，
            # 导致 Write/Bash/PowerShell 全部失败，模型反复重试直到 max_turns。
            # worktree 本身已是隔离环境，不需要额外 OS 级 sandbox。
            sandbox={"enabled": False},
            # 禁用文件 checkpointing：Claude Code 默认在 agentic 循环中创建 checkpoint，
            # 循环后期可能回滚已写入的文件（观察到 cli_greeter.py 被创建后又被删除）。
            # dogfooding 场景需要保留模型写入的文件。
            enable_file_checkpointing=False,
            # 加载 MCP servers（filesystem/memory 等），保持与 CLI 体验一致
            mcp_servers=mcp_servers,
            # 轮次和预算上限，防止失控
            max_turns=self.settings.claude_max_turns,
            max_budget_usd=self.settings.claude_max_budget_usd,
        )
        if env:
            options.env = env

        assistant_text_parts: list[str] = []
        tool_uses: list[str] = []
        result_msg: Any = None

        try:
            async for message in claude_query(prompt=briefing, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            assistant_text_parts.append(block.text)
                        elif isinstance(block, ToolUseBlock):
                            tool_uses.append(block.name)
                elif isinstance(message, ResultMessage):
                    result_msg = message
        except Exception as e:
            logger.exception("Claude Agent SDK query failed.")
            return {
                "result": "".join(assistant_text_parts),
                "success": False,
                "error": f"Claude Agent SDK query failed: {e}",
                "tool_uses": tool_uses,
            }

        if result_msg is None:
            return {
                "result": "".join(assistant_text_parts),
                "success": False,
                "error": "SDK 未返回 ResultMessage",
                "tool_uses": tool_uses,
            }

        # SDK 在出错时（is_error=True）也会抛异常，这里兜底处理
        is_success = result_msg.subtype == "success" and not result_msg.is_error
        error_text = None
        if not is_success:
            error_text = f"subtype={result_msg.subtype}"
            if result_msg.errors:
                error_text += f"; errors={result_msg.errors}"
            if result_msg.api_error_status:
                error_text += f"; api_status={result_msg.api_error_status}"

        return {
            "result": result_msg.result or "".join(assistant_text_parts),
            "success": is_success,
            "error": error_text,
            "cost_usd": result_msg.total_cost_usd,
            "duration_ms": result_msg.duration_ms,
            "session_id": result_msg.session_id,
            "num_turns": result_msg.num_turns,
            "tool_uses": tool_uses,
        }

    async def _run_claude_cli_streaming(
        self, run_id: str, workspace_id: str, briefing: str, cwd: str
    ) -> None:
        """交互模式后台任务：运行 claude_query，把消息推到 SSE 队列，结束时持久化。

        与 _run_claude_cli 的区别：
        - 非阻塞：通过 asyncio.create_task 启动，execute_coding 立即返回
        - 流式：include_partial_messages=True，前端实时看到对话
        - 权限回路：can_use_tool 回调把危险工具调用挂起，等前端 POST 回应
        - 中断：abort_event 设置后，后续 can_use_tool 一律 Deny，task 被 cancel
        """
        manager = get_session_manager()
        session = manager.get(run_id)
        if session is None:
            logger.error("CodingSession disappeared before streaming started: %s", run_id)
            return

        options = self._build_sdk_options(cwd, run_id, interactive=True)
        assistant_text_parts: list[str] = []
        tool_uses: list[str] = []
        result_msg: Any = None
        error_text: str | None = None

        await manager.emit(run_id, "session_started", {"cwd": cwd})

        try:
            async for message in claude_query(prompt=briefing, options=options):
                if session.abort_event.is_set():
                    logger.info("Coding session aborted by user: %s", run_id)
                    break
                await self._dispatch_sdk_message(run_id, message, assistant_text_parts, tool_uses)
                if isinstance(message, ResultMessage):
                    result_msg = message
        except asyncio.CancelledError:
            logger.info("Coding task cancelled: %s", run_id)
            error_text = "aborted by user"
            await manager.emit(run_id, "aborted", {"reason": "task cancelled"})
            raise
        except Exception as e:
            logger.exception("Claude Agent SDK streaming query failed.")
            error_text = f"Claude Agent SDK query failed: {e}"
            await manager.emit(run_id, "error", {"message": error_text})
        finally:
            # 计算最终结果
            payload = self._build_coding_payload(
                result_msg, assistant_text_parts, tool_uses, error_text, session
            )
            session.final_result = payload
            session.finished_at = time.time()
            await manager.emit(run_id, "completed", payload)
            # 持久化到 DB（新开 session_scope，避免跨请求复用 db）
            try:
                await self._persist_coding_result(run_id, workspace_id, payload)
            except Exception:
                logger.exception("Failed to persist coding result for run %s", run_id)

    def _build_coding_payload(
        self,
        result_msg: Any,
        assistant_text_parts: list[str],
        tool_uses: list[str],
        error_text: str | None,
        session: Any,
    ) -> dict[str, Any]:
        """从 ResultMessage 和累积状态构造 coding_result_submitted payload。"""
        if result_msg is None:
            return {
                "result": "".join(assistant_text_parts),
                "success": False,
                "error": error_text or "SDK 未返回 ResultMessage",
                "tool_uses": tool_uses,
                "tool_records": session.tool_records,
                "aborted": session.abort_event.is_set(),
            }

        is_success = result_msg.subtype == "success" and not result_msg.is_error
        if not is_success and error_text is None:
            error_text = f"subtype={result_msg.subtype}"
            if result_msg.errors:
                error_text += f"; errors={result_msg.errors}"
            if result_msg.api_error_status:
                error_text += f"; api_status={result_msg.api_error_status}"

        return {
            "result": result_msg.result or "".join(assistant_text_parts),
            "success": is_success and not session.abort_event.is_set(),
            "error": error_text,
            "cost_usd": result_msg.total_cost_usd,
            "duration_ms": result_msg.duration_ms,
            "session_id": result_msg.session_id,
            "num_turns": result_msg.num_turns,
            "tool_uses": tool_uses,
            "tool_records": session.tool_records,
            "aborted": session.abort_event.is_set(),
        }

    async def _dispatch_sdk_message(
        self,
        run_id: str,
        message: Any,
        assistant_text_parts: list[str],
        tool_uses: list[str],
    ) -> None:
        """把 SDK 消息分发到 SSE 队列，同时累积 assistant_text / tool_uses / tool_records。"""
        manager = get_session_manager()

        if isinstance(message, AssistantMessage):
            text_chunks: list[str] = []
            tool_calls: list[dict[str, Any]] = []
            for block in message.content:
                if isinstance(block, TextBlock):
                    text_chunks.append(block.text)
                elif isinstance(block, ToolUseBlock):
                    tool_uses.append(block.name)
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
            text = "".join(text_chunks)
            if text:
                assistant_text_parts.append(text)
            await manager.emit(run_id, "assistant_message", {
                "text": text,
                "tool_calls": tool_calls,
            })

        elif isinstance(message, UserMessage):
            # UserMessage 包含 ToolResultBlock（工具执行结果）
            tool_results: list[dict[str, Any]] = []
            for block in message.content:
                if isinstance(block, ToolResultBlock):
                    content = block.content
                    # content 可能是 str 或 list[TextBlock]
                    if isinstance(content, list):
                        text_parts = []
                        for c in content:
                            text = getattr(c, "text", None)
                            if text:
                                text_parts.append(text)
                        content_str = "".join(text_parts)
                    else:
                        content_str = str(content)
                    tool_results.append({
                        "tool_use_id": block.tool_use_id,
                        "content": content_str,
                        "is_error": bool(getattr(block, "is_error", False)),
                    })
            if tool_results:
                # 累积到 session.tool_records 供持久化用
                session = manager.get(run_id)
                if session is not None:
                    session.tool_records.extend(tool_results)
                await manager.emit(run_id, "tool_result", {"results": tool_results})

        elif isinstance(message, ResultMessage):
            await manager.emit(run_id, "result_message", {
                "subtype": message.subtype,
                "is_error": message.is_error,
                "num_turns": message.num_turns,
                "total_cost_usd": message.total_cost_usd,
                "duration_ms": message.duration_ms,
                "session_id": message.session_id,
            })

        elif StreamEvent is not None and isinstance(message, StreamEvent):
            # partial message：流式增量，前端用于实时渲染
            await manager.emit(run_id, "partial_message", {"event": message.event})

    def _build_sdk_options(self, cwd: str, run_id: str, *, interactive: bool) -> Any:
        """构造 ClaudeAgentOptions。

        interactive=True：permission_mode="default" + can_use_tool 回调 + include_partial_messages
        interactive=False：permission_mode="bypassPermissions"（旧行为）
        """
        env: dict[str, str] = {}
        if self.settings.claude_api_base_url:
            env["ANTHROPIC_BASE_URL"] = self.settings.claude_api_base_url
        if self.settings.claude_api_token:
            env["ANTHROPIC_AUTH_TOKEN"] = self.settings.claude_api_token
        if self.settings.claude_model:
            env["ANTHROPIC_MODEL"] = self.settings.claude_model
        if self.settings.claude_default_sonnet_model:
            env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = self.settings.claude_default_sonnet_model
        if self.settings.claude_default_haiku_model:
            env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = self.settings.claude_default_haiku_model
        if self.settings.claude_default_opus_model:
            env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = self.settings.claude_default_opus_model

        mcp_servers = self._load_mcp_servers()

        kwargs: dict[str, Any] = dict(
            cwd=cwd,
            setting_sources=[],
            sandbox={"enabled": False},
            enable_file_checkpointing=False,
            mcp_servers=mcp_servers,
            max_turns=self.settings.claude_max_turns,
            max_budget_usd=self.settings.claude_max_budget_usd,
        )

        if interactive:
            # 交互模式：用 default 权限模式让 can_use_tool 回调被触发
            # （bypassPermissions 会跳过回调，无法弹窗）
            kwargs["permission_mode"] = "default"
            kwargs["can_use_tool"] = lambda name, inp, ctx: self._can_use_tool(
                run_id, name, inp, ctx
            )
            kwargs["include_partial_messages"] = True
        else:
            kwargs["permission_mode"] = "bypassPermissions"

        options = ClaudeAgentOptions(**kwargs)
        if env:
            options.env = env
        return options

    async def _can_use_tool(
        self, run_id: str, tool_name: str, tool_input: dict[str, Any], context: Any
    ) -> Any:
        """can_use_tool 回调：危险工具挂起等前端回应，只读工具直接放行。

        注意：PermissionResultDeny 用 message 字段（不是 reason）。
        run_id 通过闭包传入（ToolPermissionContext 没有 run_id 字段）。
        """
        manager = get_session_manager()
        session = manager.get(run_id)
        if session is None:
            return PermissionResultDeny(message="coding session not found")

        # 中断后一律 Deny
        if session.abort_event.is_set():
            return PermissionResultDeny(message="aborted by user")

        # 只读工具直接放行
        if not is_dangerous_tool(tool_name):
            return PermissionResultAllow()

        # 危险工具：推权限请求到前端，等回应
        await manager.emit(run_id, "tool_call_detected", {
            "tool_name": tool_name,
            "tool_input": tool_input,
        })

        response = await manager.request_permission(run_id, tool_name, tool_input)
        if response.allow:
            return PermissionResultAllow()
        return PermissionResultDeny(
            message=response.reason or "denied by user"
        )

    async def _persist_coding_result(
        self, run_id: str, workspace_id: str, payload: dict[str, Any]
    ) -> None:
        """后台任务结束时把最终结果写入 DB（coding_result_submitted 事件）。"""
        from inkdesk_server.db import session_scope
        with session_scope() as db:
            RunService(db).add_event(
                run_id=run_id,
                stage="coding",
                event_type="coding_result_submitted",
                payload=payload,
                workspace_id=workspace_id,
            )

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
        ]
        # Skill 指南注入
        skill_ctx = self._render_skill_context("testing")
        if skill_ctx:
            lines.append(skill_ctx)
            lines.append("")
        # Query 操作：注入相关 wiki 预编译知识
        wiki_ctx = self._search_wiki_for_context(f"{run.title} {coding_result[:200]}")
        if wiki_ctx:
            lines.append(wiki_ctx)
            lines.append("")
        lines.extend([
            f"## 任务类型\n{run.type}",
            f"## 任务标题\n{run.title}",
            f"## 目标\n{run.goal}",
        ])
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

        self._check_hard_gates(run_id, "testing")

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
