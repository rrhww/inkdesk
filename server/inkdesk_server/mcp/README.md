# Inkdesk MCP Server

向外部 Agent 暴露知识库能力的薄 MCP 服务，通过 FastMCP stateless HTTP 运行，挂载在 FastAPI `/mcp` 路由。

## 架构

```
外部 Agent (MCP Client)
    │  POST /mcp  (JSON-RPC over SSE)
    ▼
FastAPI lifespan ── MCP session_manager.run()
    │
    ▼
build_mcp_server(settings) → FastMCP("inkdesk", stateless_http=True)
    │
    ├── context_pack   → RunService
    ├── search         → VaultService
    ├── deposit        → DepositService + VaultService
    └── health_check   → HealthService + VaultService
```

MCP 工具不直接访问数据库或文件系统，所有能力通过既有应用服务完成。

## 认证

MCP 请求通过 Cookie 传递 owner 身份。请求必须携带 `inkdesk_owner_session` cookie，服务端解析为 workspace 后执行操作。

```
Cookie: inkdesk_owner_session=<token>
```

未认证或无有效 workspace 时，工具返回 `PermissionError`。

## 挂载方式

```python
from inkdesk_server.mcp import build_mcp_server

mcp = build_mcp_server(settings)
mcp_app = mcp.streamable_http_app()

# 纳入 FastAPI lifespan
async with mcp.session_manager.run():
    yield

app.mount("/mcp", mcp_app)
```

`main.py` 中已完成此集成，其他模块只需 `import build_mcp_server`。

## 工具列表

`POST /mcp` → `tools/list`

### 1. context_pack — 上下文包

获取 DevRun 的完整上下文。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `runId` | `string` | 是 | DevRun ID |

**返回**：JSON 字符串，包含 `id`、`type`、`title`、`goal`、`repoContext`、`status`、`currentStage`、`stages` 数组和 `eventCount`。

**错误**：`{"error": "runId is required"}` / `{"error": "DevRun not found: ..."}`

### 2. search — 搜索知识库

在 `wiki/` 和 `raw/` 目录的 Markdown 文件中全文搜索。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | `string` | 是 | 搜索关键词，最大 500 字符 |

**返回**：`{"results": [{"path": "...", "snippet": "..."}], "count": N}`

**错误**：`{"error": "query is required"}` / `{"error": "query too long (max 500 chars)"}`

### 3. deposit — 沉淀知识

将外部 Agent 的阶段输出提交到审阅队列。**不会直接写入 wiki**，必须经过 owner 审阅。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `source` | `string` | 是 | 来源类型：`"answer"` / `"selection"` / `"stage_output"` |
| `payload` | `object` | 是 | 提交内容 |
| `runId` | `string` | 否 | 关联的 DevRun ID |
| `askTurnId` | `string` | 否 | 关联的 Ask 对话轮次 |
| `stage` | `string` | 否 | 关联的阶段名 |

**返回**：`{"reviewId": "...", "status": "PENDING", "source": "stage_output", "isNew": true}`

重复提交相同内容（同 source + payload）返回 `isNew: false` 和相同的 `reviewId`。

### 4. health_check — 健康检查

返回 Vault 知识库的结构健康摘要。

无参数。

**返回**：`{"totalPages": N, "brokenLinkCount": N, "orphanPageCount": N, "missingFrontmatterCount": N, "missingSourceCount": N}`

## 调用示例（JSON-RPC）

```json
// → tools/call
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "search",
    "arguments": { "query": "知识库" }
  }
}

// ← SSE response
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\"results\":[...],\"count\":1}"}]}}
```

## 添加新工具

在 `build_mcp_server()` 中使用 `@mcp.tool(...)` 装饰器注册：

```python
@mcp.tool(name="my_tool", title="标题", description="说明")
def my_tool(ctx: Context, arg1: str, arg2: int = 0) -> str:
    return json.dumps({"result": arg1}, ensure_ascii=False)
```

- 驼峰命名参数使用 `Field(validation_alias="camelCase")`，确保 JSON Schema 显示 `camelCase` 但函数体接收 `snake_case`
- 需要认证时调用 `_resolve_workspace_id(ctx, settings)`
- 返回类型必须是 `str`
