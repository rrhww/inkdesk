# Coding 阶段交互式 SSE 架构设计（BBC 方案）

> **状态：待实施** | 日期：2026-07-10 | 作者：Codex
>
> 配套计划：../plans/2026-07-10-coding-interactive-sse-plan.md
>
> 前置工作：2026-07-09-dev-run-stage-actions-design.md（已实施）

## 1. 背景

### 1.1 当前状态

Dev Run 的 coding 阶段已经完成 Claude Agent SDK 集成（[stage_actions.py](file:///e:/dev/projects/inkdesk/server/inkdesk_server/stage_actions.py)），核心能力齐备：

- `execute_coding` 通过 `claude_query` 拉起 SDK 会话
- `ClaudeAgentOptions` 配置：`setting_sources=[]`、`permission_mode="bypassPermissions"`、`sandbox={"enabled": False}`、`enable_file_checkpointing=False`、MCP servers 已加载
- 模型映射通过 env 显式注入，DeepSeek 端点可用
- dogfooding 验证：99s、25 turns、$0.84、正确产出文件

前端 [coding-stage-panel.tsx](file:///e:/dev/projects/inkdesk/web/components/workbench/stages/coding-stage-panel.tsx) 当前用 **2000ms `setInterval` 轮询** `getCodingStatus(runId)`，三个分支：pending / executing / has-result。

### 1.2 问题

当前 `permission_mode="bypassPermissions"` 让 SDK 自动批准所有工具调用。这带来两个隐患：

1. **DeepSeek 模型会调用 `EnterWorktree`**：模型倾向于在 `.claude/worktrees/` 下创建文件，而不是直接写入 cwd。`bypassPermissions` 让这种倾向无人拦截，残留大量 worktree 目录。
2. **dogfooding 场景下用户失去控制权**：模型可以执行任意 Bash/Write/PowerShell，用户既看不到对话过程，也无法在危险操作前介入。

用户希望将 Claude Code 的对话上下文、工具调用、权限提示**提取到前端**，通过用户交互来决定是否允许执行。

### 1.3 用户选择（BBC 组合）

用户从三个决策点各选一项：

| 决策点 | 选择 | 含义 |
|--------|------|------|
| **B** 通信通道 | SSE + POST | 后端→前端用 Server-Sent Events 推流；前端→后端用 HTTP POST 回传权限决定 |
| **B** 默认权限行为 | 危险工具弹窗 | 仅对"危险工具"（Write/Bash/Edit/PowerShell 等）弹窗等待用户决定；只读工具（Read/Glob/Grep 等）自动放行 |
| **C** 实现范围 | 完整体验 | 权限弹窗 + 流式对话 + 中断/恢复，三者全做 |

### 1.4 设计目标

- 用户在前端实时看到 Claude Code 的思考与工具调用
- 危险工具调用前弹出权限对话框，用户批准/拒绝后才继续
- 用户可随时中断执行；中断后保留已生成的对话历史
- 保留现有 `bypassPermissions` 模式作为"快速执行"开关（非破坏性兼容）

## 2. 已有可复用能力

| 能力 | 位置 | 说明 |
|------|------|------|
| SDK 消息流 | `stage_actions.py:476` `async for message in claude_query(...)` | 天然的 SSE 事件源，目前聚合到 list |
| `can_use_tool` 回调 | `ClaudeAgentOptions(can_use_tool=...)` | SDK 在每次工具调用前调用，可阻塞等待用户授权 |
| `include_partial_messages` | `ClaudeAgentOptions` 选项 | 开启后流式返回 token 级增量 |
| FastAPI StreamingResponse | FastAPI 内置 | `media_type="text/event-stream"` 即可推 SSE |
| 事件持久化 | `RunService.add_event()` | 对话片段和工具调用可存为 `coding_*` 事件 |
| 前端 `onRunUpdate` 回调 | `runs/[id]/page.tsx` | 状态提升模式，coding 面板可用同样模式上报 |

**关键缺口**：

- 无 SSE 消费端（前端 `server-api.ts` 只有 `fetchInkdeskJson` / `postInkdeskJson`）
- 无 Modal/Dialog 组件（最接近的是 [ink-select.tsx](file:///e:/dev/projects/inkdesk/web/components/ui/ink-select.tsx) 的 useRef + click-outside）
- 无 asyncio 后台任务管理（`compile_worker.py` 是线程模型，与 async SDK 不兼容）
- 无权限请求挂起/恢复机制

## 3. 设计方案

### 3.1 总体架构

```text
┌───────────────────────────── 前端 ─────────────────────────────┐
│  CodingStagePanel                                            │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  对话流渲染区（SSE 推送）                                │  │
│  │  - assistant 文本增量                                   │  │
│  │  - tool_use 卡片（工具名 + 输入预览）                    │  │
│  │  - tool_result 摘要                                     │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌──────────────────┐  ┌──────────────────────────────────┐  │
│  │  权限弹窗         │  │  [中断执行] 按钮                  │  │
│  │  (Modal)         │  │  → POST /coding/abort             │  │
│  │  工具：Bash       │  └──────────────────────────────────┘  │
│  │  输入：rm -rf ...│                                        │
│  │  [允许] [拒绝]    │                                        │
│  └──────────────────┘                                        │
│        │ 允许/拒绝                                            │
│        ▼                                                      │
│  POST /api/runs/{id}/coding/permission/respond               │
└───────────────────────────────────────────────────────────────┘
        ▲ SSE 事件流                │ POST 决定
        │ event: assistant_delta    │
        │ event: tool_use           │
        │ event: permission_request │
        │ event: tool_result        │
        │ event: result             │
        │ event: aborted            │
┌───────┴───────────────────────────┴───────────────────────────┐
│                       后端（FastAPI）                          │
│                                                               │
│  GET /api/runs/{id}/coding/stream    ← SSE 推流端点            │
│       │                                                       │
│       ▼                                                       │
│  CodingSessionManager（进程级单例）                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  run_id → CodingSession 映射                            │ │
│  │                                                         │ │
│  │  CodingSession:                                         │ │
│  │   - async task（运行 claude_query）                     │ │
│  │   - asyncio.Queue（SSE 事件缓冲）                       │ │
│  │   - pending_permission: PermissionRequest | None        │ │
│  │   - permission_response: asyncio.Future                 │ │
│  │   - abort_event: asyncio.Event                          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  POST /api/runs/{id}/coding/execute      ← 启动（非阻塞）     │
│  POST /api/runs/{id}/coding/permission/respond  ← 权限回应    │
│  POST /api/runs/{id}/coding/abort        ← 中断               │
└───────────────────────────────────────────────────────────────┘
        │                                                       │
        ▼                                                       │
┌───────────────────────────────────────────────────────────────┐
│                  Claude Agent SDK（不变）                      │
│  claude_query(prompt, options)  ← can_use_tool 回调           │
│                                  ← include_partial_messages   │
└───────────────────────────────────────────────────────────────┘
```

### 3.2 后端核心抽象：`CodingSessionManager`

**职责**：管理 run_id → CodingSession 的映射，隔离各 run 的执行状态。

**位置**：新建 `server/inkdesk_server/coding_session.py`

```python
@dataclass
class PermissionRequest:
    """can_use_tool 回调产出的权限请求，通过 SSE 推给前端。"""
    request_id: str           # UUID，前端回应时带上
    tool_name: str            # "Bash" / "Write" / ...
    tool_input: dict          # 工具入参（如 {"command": "rm -rf ..."}）
    created_at: float         # 创建时间戳，前端可显示倒计时

@dataclass
class PermissionResponse:
    """前端 POST 回来的决定。"""
    request_id: str
    allow: bool               # True=允许，False=拒绝
    reason: str | None        # 拒绝原因（可选，传给模型作为反馈）

@dataclass
class CodingSession:
    run_id: str
    task: asyncio.Task | None              # 运行 claude_query 的后台任务
    event_queue: asyncio.Queue             # SSE 事件缓冲（满了丢弃最老的 partial）
    pending_permission: PermissionRequest | None
    permission_future: asyncio.Future[PermissionResponse] | None
    abort_event: asyncio.Event
    started_at: float
    finished_at: float | None

class CodingSessionManager:
    """进程级单例，所有 coding 请求通过它路由。"""
    _sessions: dict[str, CodingSession] = {}

    def get_or_create(self, run_id: str) -> CodingSession: ...
    def get(self, run_id: str) -> CodingSession | None: ...
    def remove(self, run_id: str) -> None: ...

    async def request_permission(
        self, run_id: str, tool_name: str, tool_input: dict,
        timeout: float = 120.0,
    ) -> PermissionResponse:
        """供 can_use_tool 回调调用：构造请求 → 推入 SSE 队列 → 等待前端回应。"""
        ...

    async def emit(self, run_id: str, event_type: str, data: dict) -> None:
        """向 SSE 队列推事件，队列满时丢弃 partial 增量。"""
        ...

    async def abort(self, run_id: str) -> None:
        """设置 abort_event，取消 task，推 aborted 事件。"""
        ...
```

**为什么用进程级单例**：

- `can_use_tool` 回调在 SDK 的 event loop 中执行，必须能找到对应的 session 来挂起
- 前端的 POST 回应也需要一个全局入口找到 session 推 future
- FastAPI 的依赖注入不适合跨请求共享可变状态，单例 + 锁更直接

**并发约束**：

- 同一 run_id 同时只允许一个活跃 session（`execute` 检测到已有活跃 session 时返回 409）
- 不同 run_id 之间完全隔离

### 3.3 后端：`can_use_tool` 回调

```python
# 危险工具白名单：只有这些工具调用才弹窗，其他自动放行
DANGEROUS_TOOLS = frozenset({
    "Write", "Edit", "MultiEdit", "Bash", "PowerShell",
    "NotebookEdit", "WebFetch",
    # MCP 工具按命名空间前缀匹配
})

def _is_dangerous(tool_name: str) -> bool:
    if tool_name in DANGEROUS_TOOLS:
        return True
    # MCP 工具名形如 "mcp__filesystem__write_file"
    for prefix in ("mcp__filesystem__", "mcp__memory__"):
        if tool_name.startswith(prefix):
            return "write" in tool_name.lower() or "delete" in tool_name.lower()
    return False

async def _can_use_tool(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext,
) -> PermissionResultAllow | PermissionResultDeny:
    session = _session_manager.get(context.run_id)
    if session is None:
        # session 已被清理，默认拒绝避免失控
        return PermissionResultDeny(reason="session not found")

    if session.abort_event.is_set():
        return PermissionResultDeny(reason="aborted by user")

    if not _is_dangerous(tool_name):
        # 只读工具自动放行，但仍推一个 tool_use 事件让前端可见
        await _session_manager.emit(
            session.run_id, "tool_use",
            {"tool": tool_name, "input": tool_input, "auto_allowed": True},
        )
        return PermissionResultAllow()

    # 危险工具：推权限请求，挂起等待前端回应
    response = await _session_manager.request_permission(
        session.run_id, tool_name, tool_input,
        timeout=session.permission_timeout,
    )
    await _session_manager.emit(
        session.run_id, "tool_use",
        {
            "tool": tool_name, "input": tool_input,
            "approved": response.allow, "reason": response.reason,
        },
    )
    if response.allow:
        return PermissionResultAllow()
    return PermissionResultDeny(reason=response.reason or "denied by user")
```

**关键点**：

- 回调内不直接访问 db，避免阻塞 SDK event loop
- 拒绝原因通过 `PermissionResultDeny(reason=...)` 传回模型，模型可以调整策略
- 权限超时（默认 120s）由 `asyncio.wait_for` 实现，超时视为拒绝

### 3.4 后端：改造 `execute_coding` 与 `_run_claude_cli`

**`execute_coding` 改为非阻塞**：

```python
async def execute_coding(self, run_id: str, workspace_id: str) -> DevRunResponse:
    run = RunService(self.db).get_run(run_id, workspace_id)
    if run.currentStage != "coding":
        raise ApiError(409, "INVALID_STAGE", ...)

    # 已有活跃 session 时拒绝重启
    existing = _session_manager.get(run_id)
    if existing is not None and existing.task is not None and not existing.task.done():
        raise ApiError(409, "CODING_IN_PROGRESS", "coding session already running")

    briefing = self._assemble_briefing(run)
    run = RunService(self.db).add_event(
        run_id=run_id, stage="coding",
        event_type="coding_briefing_prepared",
        payload={"briefing": briefing},
        workspace_id=workspace_id,
    )

    if not self._claude_available():
        # 走原有的 placeholder 路径
        ...
        return run

    # 创建 session 并启动后台任务，不等待完成
    session = _session_manager.get_or_create(run_id)
    session.task = asyncio.create_task(
        self._run_claude_cli_streaming(run_id, briefing, cwd)
    )
    # 立即返回，让前端去连 SSE
    return run
```

**新增 `_run_claude_cli_streaming`**：

```python
async def _run_claude_cli_streaming(
    self, run_id: str, briefing: str, cwd: str,
) -> None:
    """后台任务：运行 SDK 查询，把消息推到 SSE 队列，结束后写事件。"""
    session = _session_manager.get(run_id)
    try:
        options = self._build_sdk_options(
            cwd=cwd,
            can_use_tool=lambda name, inp, ctx: _can_use_tool(name, inp, ctx, run_id),
            include_partial_messages=True,
        )
        async for message in claude_query(prompt=briefing, options=options):
            if session.abort_event.is_set():
                break
            await self._dispatch_sdk_message(run_id, message)
        await _session_manager.emit(run_id, "result", {"status": "completed"})
    except asyncio.CancelledError:
        await _session_manager.emit(run_id, "aborted", {"reason": "user aborted"})
        raise
    except Exception as e:
        await _session_manager.emit(run_id, "result", {"status": "failed", "error": str(e)})
    finally:
        # 写最终的 coding_result_submitted 事件
        await self._persist_coding_result(run_id)
        _session_manager.remove(run_id)
```

**`_dispatch_sdk_message`**：

```python
async def _dispatch_sdk_message(self, run_id: str, message: Any) -> None:
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                await _session_manager.emit(run_id, "assistant_text", {"text": block.text})
            elif isinstance(block, ToolUseBlock):
                # 注意：can_use_tool 已在工具实际执行前先回调，
                # 这里是工具执行后的结果摘要，不是请求权限
                await _session_manager.emit(run_id, "tool_use_block", {
                    "id": block.id, "tool": block.name, "input": block.input,
                })
    elif isinstance(message, UserMessage):  # SDK 把 tool_result 也包成 UserMessage
        for block in message.content:
            if isinstance(block, ToolResultBlock):
                await _session_manager.emit(run_id, "tool_result", {
                    "tool_use_id": block.tool_use_id,
                    "content": _truncate(block.content, 500),
                    "is_error": block.is_error,
                })
    elif isinstance(message, ResultMessage):
        await _session_manager.emit(run_id, "result_message", {
            "subtype": message.subtype,
            "is_error": message.is_error,
            "num_turns": message.num_turns,
            "total_cost_usd": message.total_cost_usd,
            "duration_ms": message.duration_ms,
            "result": message.result,
        })
```

> **partial messages**：开启 `include_partial_messages=True` 后，SDK 还会推 `partial_message` 类型，含 `partial_json` 增量。这些直接转发给前端做 token 级流式渲染即可。partial 事件优先级最低，队列满时优先丢弃。

### 3.5 后端：SSE 端点

```python
@app.get("/api/runs/{run_id}/coding/stream")
async def run_coding_stream(run_id: str, ...):
    session = _session_manager.get(run_id)
    if session is None:
        raise ApiError(404, "NO_SESSION", "no active coding session")

    async def event_generator():
        # 先推一个 session_started 让前端知道连上了
        yield _format_sse("session_started", {"run_id": run_id})
        while True:
            if session.finished_at is not None:
                # 队列可能还有残余事件，先 drain
                while not session.event_queue.empty():
                    event_type, data = await session.event_queue.get()
                    yield _format_sse(event_type, data)
                yield _format_sse("session_end", {"run_id": run_id})
                return
            try:
                event_type, data = await asyncio.wait_for(
                    session.event_queue.get(), timeout=15.0,
                )
                yield _format_sse(event_type, data)
            except asyncio.TimeoutError:
                # 心跳，保持连接
                yield ": ping\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**SSE 事件格式**：

```
event: permission_request
data: {"request_id":"...","tool_name":"Bash","tool_input":{"command":"rm -rf .git"},"created_at":...}

event: assistant_text
data: {"text":"I'll create the file..."}

event: tool_result
data: {"tool_use_id":"toolu_...","content":"File created","is_error":false}

event: result_message
data: {"subtype":"success","num_turns":25,"total_cost_usd":0.84,...}
```

### 3.6 后端：权限回应端点

```python
class PermissionRespondRequest(BaseModel):
    request_id: str
    allow: bool
    reason: str | None = None

@app.post("/api/runs/{run_id}/coding/permission/respond")
async def run_coding_permission_respond(
    run_id: str, request: PermissionRespondRequest, ...
):
    session = _session_manager.get(run_id)
    if session is None or session.permission_future is None:
        raise ApiError(404, "NO_PENDING_PERMISSION", "no pending permission request")
    if session.pending_permission is None or session.pending_permission.request_id != request.request_id:
        raise ApiError(409, "STALE_PERMISSION", "request_id mismatch")
    response = PermissionResponse(
        request_id=request.request_id,
        allow=request.allow,
        reason=request.reason,
    )
    session.permission_future.set_result(response)
    session.permission_future = None
    session.pending_permission = None
    return {"ok": True}
```

### 3.7 后端：中断端点

```python
@app.post("/api/runs/{run_id}/coding/abort")
async def run_coding_abort(run_id: str, ...):
    session = _session_manager.get(run_id)
    if session is None or session.task is None:
        raise ApiError(404, "NO_SESSION", "no active coding session")
    if session.task.done():
        raise ApiError(409, "ALREADY_FINISHED", "session already finished")
    await _session_manager.abort(run_id)
    # abort 会设置 abort_event + cancel task + 推 aborted 事件
    return {"ok": True}
```

**中断语义**：

- 用户中断后，`can_use_tool` 后续调用一律返回 Deny
- 正在执行的工具调用（如长时间 Bash）通过 `task.cancel()` 中断
- 已经写入的文件不回滚（dogfooding 场景下保留产物）
- SSE 队列推 `aborted` 事件，前端切到中断状态

### 3.8 前端：SSE 消费层

**新增 `web/lib/coding-stream.ts`**：

```typescript
export type CodingStreamEvent =
  | { type: "session_started"; runId: string }
  | { type: "assistant_text"; text: string }
  | { type: "partial_message"; partialJson: string }
  | { type: "tool_use"; tool: string; input: unknown; autoAllowed?: boolean; approved?: boolean }
  | { type: "tool_result"; toolUseId: string; content: string; isError: boolean }
  | { type: "permission_request"; requestId: string; toolName: string; toolInput: unknown; createdAt: number }
  | { type: "result_message"; subtype: string; isError: boolean; numTurns: number; totalCostUsd: number; result: string }
  | { type: "aborted"; reason: string }
  | { type: "session_end"; runId: string };

export function subscribeCodingStream(
  runId: string,
  onEvent: (event: CodingStreamEvent) => void,
  onError: (error: Event) => void,
): () => void {
  const es = new EventSource(`/api/runs/${runId}/coding/stream`);
  // 注册所有 event 类型监听器
  const types = [
    "session_started", "assistant_text", "partial_message",
    "tool_use", "tool_result", "permission_request",
    "result_message", "aborted", "session_end",
  ];
  const handlers = types.map((type) => {
    const h = (e: MessageEvent) => onEvent({ type, ...JSON.parse(e.data) } as CodingStreamEvent);
    es.addEventListener(type, h);
    return { type, h };
  });
  es.onerror = onError;
  return () => {
    handlers.forEach(({ type, h }) => es.removeEventListener(type, h));
    es.close();
  };
}

export async function respondPermission(
  runId: string,
  requestId: string,
  allow: boolean,
  reason?: string,
): Promise<void> {
  await postInkdeskJson(`/runs/${runId}/coding/permission/respond`, {
    request_id: requestId, allow, reason,
  });
}

export async function abortCoding(runId: string): Promise<void> {
  await postInkdeskJson(`/runs/${runId}/coding/abort`, {});
}
```

**注意**：`EventSource` 不支持自定义 header，鉴权依赖 cookie。后端的 SSE 端点不能用 `Authorization` header，得走 session cookie 或 query token。当前 Inkdesk 是单用户本地应用，可暂不鉴权。

### 3.9 前端：`CodingStagePanel` 重构

**状态机扩展**：

```typescript
type CodingPanelState =
  | { kind: "idle" }
  | { kind: "running"; events: CodingStreamEvent[]; pendingPermission: PermissionRequest | null }
  | { kind: "permission_pending"; events: CodingStreamEvent[]; request: PermissionRequest }
  | { kind: "completed"; events: CodingStreamEvent[]; result: ResultMessage }
  | { kind: "aborted"; events: CodingStreamEvent[]; reason: string }
  | { kind: "failed"; events: CodingStreamEvent[]; error: string };
```

**组件结构**：

```text
CodingStagePanel
├── BriefingPreview（pending 时显示，可复制）
├── CodingDialog（running/permission_pending/completed/aborted/failed 时显示）
│   ├── DialogMessageList（滚动列表，渲染 events 数组）
│   │   ├── AssistantTextBubble
│   │   ├── ToolUseCard（工具名 + 输入预览 + 状态徽章）
│   │   └── ToolResultCard
│   ├── PermissionDialog（permission_pending 时弹出，Modal）
│   │   ├── 工具名 + 输入预览
│   │   ├── [允许] [拒绝] + 拒绝原因输入框
│   │   └── 倒计时（120s）
│   └── ActionBar
│       └── [中断执行] 按钮（running 时显示）
└── CodingResultSummary（completed 时显示）
```

**关键交互**：

1. 用户点击"启动 Claude Code" → 调 `executeCoding(runId)` → 切到 `running` 状态 → 建立 SSE
2. SSE 推 `permission_request` → 切到 `permission_pending` → 弹 Modal
3. 用户点"允许" → 调 `respondPermission(runId, requestId, true)` → 切回 `running`
4. SSE 推 `result_message` → 切到 `completed`
5. 用户随时点"中断执行" → 调 `abortCoding(runId)` → SSE 推 `aborted` → 切到 `aborted`

**SSE 生命周期管理**：

```typescript
useEffect(() => {
  if (state.kind !== "running" && state.kind !== "permission_pending") return;
  const unsubscribe = subscribeCodingStream(runId, (event) => {
    // 累积到 events 数组
    // 根据事件类型更新 state
  }, (err) => {
    // 断线重连逻辑：3s 后重试，最多 3 次
  });
  return unsubscribe;
}, [runId, state.kind === "running" || state.kind === "permission_pending"]);
```

### 3.10 前端：`PermissionDialog` 组件

**新建 `web/components/workbench/stages/permission-dialog.tsx`**

用 `createPortal` 渲染到 `document.body`，避免被父容器的 `overflow: hidden` 裁剪。参考 [ink-select.tsx](file:///e:/dev/projects/inkdesk/web/components/ui/ink-select.tsx) 的 click-outside 模式。

```typescript
export function PermissionDialog({
  request, onRespond,
}: {
  request: PermissionRequest;
  onRespond: (allow: boolean, reason?: string) => void;
}) {
  const [reason, setReason] = useState("");
  const [remaining, setRemaining] = useState(120);
  useEffect(() => {
    const timer = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) { onRespond(false, "timeout"); return 0; }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="...">
        <h3>权限请求</h3>
        <p>工具：<code>{request.toolName}</code></p>
        <pre>{JSON.stringify(request.toolInput, null, 2)}</pre>
        <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="拒绝原因（可选）" />
        <div>
          <button onClick={() => onRespond(true)}>允许</button>
          <button onClick={() => onRespond(false, reason || undefined)}>拒绝</button>
        </div>
        <span>{remaining}s 后自动拒绝</span>
      </div>
    </div>,
    document.body,
  );
}
```

## 4. API 汇总

| 方法 | 路径 | 说明 | 状态 |
|------|------|------|------|
| POST | `/api/runs/{run_id}/coding/execute` | 启动 coding session（非阻塞） | 改造：从阻塞返回结果改为立即返回 |
| GET | `/api/runs/{run_id}/coding/stream` | SSE 推流对话/工具/权限事件 | 新增 |
| POST | `/api/runs/{run_id}/coding/permission/respond` | 前端回传权限决定 | 新增 |
| POST | `/api/runs/{run_id}/coding/abort` | 中断执行 | 新增 |
| GET | `/api/runs/{run_id}/coding/status` | 轮询状态（保留兼容） | 不变 |

**`coding/execute` 行为变化**：

- 旧：阻塞执行完 SDK 查询，返回带 `coding_result_submitted` 事件的 run
- 新：立即返回带 `coding_briefing_prepared` 事件的 run；最终结果由后台任务异步写入，前端通过 SSE 收到 `result_message` 后再调 `getCodingStatus` 或刷新 run

**向后兼容**：

- 保留 `getCodingStatus` 接口，后台任务结束时仍会写 `coding_result_submitted` 事件
- 旧的轮询前端在无 SSE 时仍能工作（只是看不到实时对话和权限弹窗）

## 5. 配置项

新增到 [core/config.py](file:///e:/dev/projects/inkdesk/server/inkdesk_server/core/config.py)：

```python
claude_permission_timeout_seconds: int = Field(
    default=120, alias="INKDESK_CLAUDE_PERMISSION_TIMEOUT_SECONDS",
    description="can_use_tool 等待前端回应的超时秒数，超时视为拒绝",
)
claude_sse_queue_maxsize: int = Field(
    default=100, alias="INKDESK_CLAUDE_SSE_QUEUE_MAXSIZE",
    description="SSE 事件队列上限，满了优先丢弃 partial_message",
)
claude_interactive_mode: bool = Field(
    default=True, alias="INKDESK_CLAUDE_INTERACTIVE_MODE",
    description="True=启用 can_use_tool 权限弹窗；False=保留 bypassPermissions 行为",
)
```

`claude_interactive_mode=False` 时，`_build_sdk_options` 不传 `can_use_tool`，保留 `permission_mode="bypassPermissions"`，作为"快速执行"开关。

## 6. 前端改动

### 6.1 新增文件

| 文件 | 说明 |
|------|------|
| `web/lib/coding-stream.ts` | SSE 消费 + 权限回应 + 中断 API |
| `web/components/workbench/stages/permission-dialog.tsx` | 权限弹窗组件 |
| `web/components/workbench/stages/coding-dialog-view.tsx` | 对话流渲染区（拆分自 coding-stage-panel） |

### 6.2 修改文件

| 文件 | 改动 |
|------|------|
| [coding-stage-panel.tsx](file:///e:/dev/projects/inkdesk/web/components/workbench/stages/coding-stage-panel.tsx) | 移除 2000ms 轮询，改为 SSE 订阅；接入 PermissionDialog；增加中断按钮 |
| [research.ts](file:///e:/dev/projects/inkdesk/web/lib/research.ts) | `executeCoding` 返回类型不变，新增 `respondCodingPermission` / `abortCoding` |
| [types.ts](file:///e:/dev/projects/inkdesk/web/lib/types.ts) | 新增 `PermissionRequest` / `CodingStreamEvent` / `CodingPanelState` 类型 |

## 7. 后端改动

### 7.1 新增文件

| 文件 | 说明 |
|------|------|
| `server/inkdesk_server/coding_session.py` | `CodingSessionManager` / `CodingSession` / `PermissionRequest` / `PermissionResponse` |

### 7.2 修改文件

| 文件 | 改动 |
|------|------|
| [stage_actions.py](file:///e:/dev/projects/inkdesk/server/inkdesk_server/stage_actions.py) | `execute_coding` 改为非阻塞；`_run_claude_cli` 拆分为 `_run_claude_cli_streaming` + `_dispatch_sdk_message` + `_build_sdk_options`；新增 `_can_use_tool` 回调；`_persist_coding_result` 在后台任务结束时写事件 |
| [main.py](file:///e:/dev/projects/inkdesk/server/inkdesk_server/main.py) | 新增 3 个路由：`coding/stream`、`coding/permission/respond`、`coding/abort` |
| [schemas.py](file:///e:/dev/projects/inkdesk/server/inkdesk_server/schemas.py) | 新增 `PermissionRespondRequest` |
| [core/config.py](file:///e:/dev/projects/inkdesk/server/inkdesk_server/core/config.py) | 新增 3 个配置项 |
| [tests/test_run_api.py](file:///e:/dev/projects/inkdesk/server/tests/test_run_api.py) | 新增 SSE/权限/中断测试；更新 mock 适配新的非阻塞 execute |
| [infra/.env.example](file:///e:/dev/projects/inkdesk/infra/.env.example) | 同步 3 个新配置项 |

## 8. 事件持久化策略

SSE 事件是瞬时的，但需要把关键节点持久化到 `RunEvent` 表，以便刷新页面后还能看到执行历史。

| SSE 事件 | 是否持久化 | 存为 |
|----------|-----------|------|
| `assistant_text` | 否 | 太碎，不存 |
| `partial_message` | 否 | 增量，不存 |
| `tool_use`（含权限决定） | 是 | `coding_tool_used`，payload 含 tool/input/approved/reason |
| `tool_result` | 是（截断） | 合并到对应的 `coding_tool_used` 事件 |
| `permission_request` | 否 | 瞬态事件，靠 SSE 推即可 |
| `result_message` | 是 | `coding_result_submitted`（沿用现有事件类型） |
| `aborted` | 是 | `coding_result_submitted`，payload 含 `success: false, error: "aborted by user"` |

后台任务结束时一次性 flush 所有待持久化事件，避免在 SDK 循环中频繁开 db session。

## 9. 风险

| 风险 | 应对 |
|------|------|
| `can_use_tool` 阻塞导致 SDK 超时 | 配置 120s 超时，超时自动拒绝；`max_turns` 兜底 |
| 用户关闭浏览器后权限请求永久挂起 | 后台任务有 `asyncio.wait_for` 超时；session 有 TTL 清理 |
| SSE 连接被代理中断（如 nginx 默认 60s） | 后端 15s 推心跳；前端 EventSource 自动重连 |
| 后端重启丢失 in-memory session | 接受这个限制；重启后前端检测到 SSE 断开 → 提示用户重新执行 |
| DeepSeek 模型不识别 Deny 反馈 | 拒绝原因作为 `PermissionResultDeny(reason=...)` 传回，模型可调整；如模型仍重试，`max_turns` 兜底 |
| 并发 run 同时跑 SDK 拖慢后端 | 进程级单例不限制并发，但单 run 串行；后续可加全局并发上限 |
| `include_partial_messages` 流量过大 | SSE 队列满时优先丢弃 partial；前端节流渲染 |
| 浏览器 `EventSource` 不支持自定义 header | SSE 端点走 cookie 鉴权或暂不鉴权（本地单用户） |
| 已写入的文件在中断后残留 | 接受这个行为；dogfooding 场景下保留产物是期望的 |

## 10. 验收标准

- [ ] 用户在 coding 阶段点击"启动 Claude Code"，前端立即显示对话流区域
- [ ] SSE 推送的 assistant 文本实时滚动显示
- [ ] 危险工具（Write/Bash 等）调用前弹出 PermissionDialog，显示工具名和输入
- [ ] 用户点击"允许"后工具执行，"拒绝"后模型收到拒绝原因
- [ ] 权限请求 120s 无回应自动拒绝
- [ ] 用户点击"中断执行"后，SDK 循环停止，前端显示中断状态
- [ ] 中断/完成/失败后，刷新页面仍能看到已持久化的工具调用历史
- [ ] `claude_interactive_mode=False` 时回退到原 `bypassPermissions` 行为，测试通过
- [ ] 后端测试覆盖：session 生命周期、权限超时、中断、SSE 事件格式
- [ ] 前端测试覆盖：SSE 事件解析、PermissionDialog 交互、状态机切换

## 11. 不做的事情

- **不做多 run 并发编排**：一次只关注一个 run 的 coding session
- **不做 SSE 鉴权**：本地单用户场景，暂不鉴权
- **不做权限策略配置化**：危险工具白名单硬编码在代码中，后续按需提取
- **不做对话历史的全文持久化**：只持久化工具调用和最终结果，对话文本刷新后丢失（可后续加）
- **不做断点恢复**：后端重启后 session 丢失，用户需重新执行
- **不修改 SDK 内部行为**：仅通过 `can_use_tool` 和 `include_partial_messages` 两个公开选项接入

## 12. 实施顺序

按依赖关系分 4 个切片，每个切片可独立验证：

1. **后端骨架**：`CodingSessionManager` + 非阻塞 `execute_coding` + SSE 端点 + 心跳
   - 验证：curl 连 SSE 能收到 session_started 和心跳
2. **权限回路**：`can_use_tool` 回调 + `permission/respond` 端点 + 超时
   - 验证：mock SDK 调用，curl 模拟前端回应
3. **前端对话流**：SSE 消费 + 对话渲染 + 中断按钮
   - 验证：浏览器看到实时对话和中断生效
4. **权限弹窗 + 集成**：PermissionDialog 组件 + 端到端 dogfooding
   - 验证：真实 DeepSeek 模型跑完整 coding 任务，弹窗能拦截危险工具

详细任务分解见配套计划文档。
