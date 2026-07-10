"""Coding session 管理器：支持 SSE 推流 + can_use_tool 权限回路 + 中断。

进程级单例，管理 run_id → CodingSession 映射。每个 session 独立持有：
- asyncio.Task：运行 claude_query
- asyncio.Queue：SSE 事件缓冲
- pending_permission / permission_future：挂起 can_use_tool 等待前端回应
- abort_event：用户中断信号

设计文档：docs/development/specs/2026-07-10-coding-interactive-sse-design.md
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class PermissionRequest:
    """can_use_tool 回调产出的权限请求，通过 SSE 推给前端。"""

    request_id: str
    tool_name: str
    tool_input: dict[str, Any]
    created_at: float


@dataclass
class PermissionResponse:
    """前端 POST 回来的决定。"""

    request_id: str
    allow: bool
    reason: str | None = None


@dataclass
class CodingSession:
    """单个 run 的 coding 执行状态。"""

    run_id: str
    task: asyncio.Task[Any] | None = None
    event_queue: asyncio.Queue[tuple[str, dict[str, Any]]] = field(
        default_factory=lambda: asyncio.Queue(maxsize=100)
    )
    pending_permission: PermissionRequest | None = None
    permission_future: asyncio.Future[PermissionResponse] | None = None
    abort_event: asyncio.Event = field(default_factory=asyncio.Event)
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    # 累积的工具调用和结果，后台任务结束时一次性持久化
    tool_records: list[dict[str, Any]] = field(default_factory=list)
    final_result: dict[str, Any] | None = None
    permission_timeout: float = 120.0


class CodingSessionManager:
    """进程级单例，所有 coding 请求通过它路由。"""

    def __init__(self) -> None:
        self._sessions: dict[str, CodingSession] = {}

    def get_or_create(self, run_id: str, *, permission_timeout: float = 120.0) -> CodingSession:
        existing = self._sessions.get(run_id)
        if existing is not None and existing.task is not None and not existing.task.done():
            return existing
        session = CodingSession(run_id=run_id, permission_timeout=permission_timeout)
        self._sessions[run_id] = session
        return session

    def get(self, run_id: str) -> CodingSession | None:
        return self._sessions.get(run_id)

    def remove(self, run_id: str) -> None:
        self._sessions.pop(run_id, None)

    def is_active(self, run_id: str) -> bool:
        session = self._sessions.get(run_id)
        return session is not None and session.task is not None and not session.task.done()

    async def emit(self, run_id: str, event_type: str, data: dict[str, Any]) -> None:
        """向 SSE 队列推事件。

        队列满时丢弃 partial_message 事件（低优先级），其他事件阻塞等待。
        """
        session = self._sessions.get(run_id)
        if session is None:
            return
        try:
            session.event_queue.put_nowait((event_type, data))
        except asyncio.QueueFull:
            # 队列满：丢弃 partial 事件，保留关键事件
            if event_type == "partial_message":
                return
            # 其他事件：尝试挤掉一个 partial
            self._drop_one_partial(session)
            try:
                session.event_queue.put_nowait((event_type, data))
            except asyncio.QueueFull:
                logger.warning("SSE queue full for run %s, dropping %s", run_id, event_type)

    @staticmethod
    def _drop_one_partial(session: CodingSession) -> None:
        """从队列里挤掉一个 partial_message 事件。Queue 不支持随机删除，这里用 drain+refill。"""
        # asyncio.Queue 没有 peek/remove，只能 drain 再 put back。为了避免无限阻塞，
        # 用 non-get 的方式不太可能。这里简单实现：尝试 get_nowait 直到拿到 partial 或空。
        drained: list[tuple[str, dict[str, Any]]] = []
        removed = False
        while not session.event_queue.empty():
            try:
                item = session.event_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            if not removed and item[0] == "partial_message":
                removed = True
                continue
            drained.append(item)
        for item in drained:
            try:
                session.event_queue.put_nowait(item)
            except asyncio.QueueFull:
                break

    async def request_permission(
        self,
        run_id: str,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> PermissionResponse:
        """供 can_use_tool 回调调用：构造请求 → 推 SSE → 等前端回应。"""
        session = self._sessions.get(run_id)
        if session is None:
            return PermissionResponse(request_id="", allow=False, reason="session not found")

        request = PermissionRequest(
            request_id=uuid4().hex,
            tool_name=tool_name,
            tool_input=tool_input,
            created_at=time.time(),
        )
        session.pending_permission = request
        loop = asyncio.get_event_loop()
        session.permission_future = loop.create_future()

        await self.emit(
            run_id,
            "permission_request",
            {
                "request_id": request.request_id,
                "tool_name": request.tool_name,
                "tool_input": request.tool_input,
                "created_at": request.created_at,
            },
        )

        try:
            response = await asyncio.wait_for(
                session.permission_future, timeout=session.permission_timeout
            )
            return response
        except asyncio.TimeoutError:
            return PermissionResponse(
                request_id=request.request_id, allow=False, reason="permission timeout"
            )
        finally:
            session.pending_permission = None
            session.permission_future = None

    def respond_permission(self, run_id: str, response: PermissionResponse) -> bool:
        """前端 POST 回应时调用，解除 can_use_tool 的挂起。返回是否成功投递。"""
        session = self._sessions.get(run_id)
        if session is None or session.permission_future is None:
            return False
        if (
            session.pending_permission is None
            or session.pending_permission.request_id != response.request_id
        ):
            return False
        if session.permission_future.done():
            return False
        session.permission_future.set_result(response)
        return True

    async def abort(self, run_id: str) -> bool:
        """设置 abort_event，取消 task。返回是否找到了活跃 session。"""
        session = self._sessions.get(run_id)
        if session is None:
            return False
        session.abort_event.set()
        # 如果有挂起的权限请求，立即拒绝
        if session.permission_future is not None and not session.permission_future.done():
            session.permission_future.set_result(
                PermissionResponse(request_id="", allow=False, reason="aborted by user")
            )
        if session.task is not None and not session.task.done():
            session.task.cancel()
        await self.emit(run_id, "aborted", {"reason": "user aborted"})
        return True


# 进程级单例
_session_manager = CodingSessionManager()


def get_session_manager() -> CodingSessionManager:
    return _session_manager


# 危险工具白名单：只有这些工具调用才弹窗，其他自动放行
DANGEROUS_TOOLS = frozenset(
    {
        "Write",
        "Edit",
        "MultiEdit",
        "Bash",
        "PowerShell",
        "NotebookEdit",
        "WebFetch",
    }
)


def is_dangerous_tool(tool_name: str) -> bool:
    """判断工具是否需要弹窗。MCP 工具按命名空间 + 关键词匹配。"""
    if tool_name in DANGEROUS_TOOLS:
        return True
    # MCP 工具名形如 "mcp__filesystem__write_file"
    if tool_name.startswith("mcp__"):
        lower = tool_name.lower()
        return "write" in lower or "delete" in lower or "edit" in lower or "move" in lower
    return False
