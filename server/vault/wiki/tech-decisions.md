---
type: concept
created: 2026-07-10
updated: 2026-07-10
tags: [技术决策, 约束, 门禁]
related: [system-architecture]
source_file: docs/architecture/技术决策.md
status: stable
---

# 技术决策与约束

## 仓库与前端

- 单仓库（`web/` + `server/` + `infra/`），当前是单人私有部署模型
- 前端用 Next.js App Router，同源 API 代理（rewrites `/api/**` -> 后端）
- 路由固定工作区在 `/app`，`/` 直接重定向到 `/app`，无公开阅读面

## 认证与数据边界

- 无登录认证，单实例、默认 workspace（slug: `inkdesk`）
- API 通过 Next.js 同源代理无 CORS
- 数据真相边界：`raw/` 和 `wiki/` 的 Markdown 是长期真相，PostgreSQL 只存索引/关系/队列/问答记录，DB 缺失时允许从 vault frontmatter 回补

## 写入策略（关键门禁）

**AI 不能直接写 wiki**，所有编译和 writeback 结果先进入 `review_items`，只有 owner 接受后才落入 `wiki/`。明确拆开"AI 提议"与"正式知识"。

## Context Ask 策略

默认 `wiki first, raw second`；`vault_plus_web` 只在 owner 显式选择时启用；外部网页证据不自动进 vault，必须通过 writeback 流程。

## LangGraph 编排边界

LangGraph 负责知识层有状态编排（ingest 管线、Context Ask 多阶段检索、Wiki Health 扫描、Skill gate 状态机），**不负责代码生成/文件读写/命令执行**，coding/test/debugging 委托外部 Agent。

## Claude Agent SDK 集成约束

- 使用 `claude-agent-sdk` 包（非 CLI subprocess），通过 stream-json 协议通信
- `setting_sources=[]` 禁用 CLAUDE.md / skills / 用户 settings
- `permission_mode="bypassPermissions"` 自动批准工具调用（非交互模式）
- `sandbox={"enabled": False}` + `enable_file_checkpointing=False`
- 加载 MCP servers（filesystem, memory, everything, sequential-thinking）
- 禁用 EnterWorktree/ExitWorktree 工具，强制直接写 cwd
- 配置 `max_turns`, `max_budget_usd`, `asyncio timeout` 控制执行

## 当前明确不做

- 公开文章系统
- plans/search/settings 主路径
- 多租户/多人协作
