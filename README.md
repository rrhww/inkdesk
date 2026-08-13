# Inkdesk

Inkdesk 是一个面向研发人员的**知识上下文与执行工作台**（Knowledge Context Runtime），本地优先、Vault-first：先编译带来源、带不确定性的主题知识上下文，再组织可执行任务，逐步接入 Agent 执行与人工门禁。它以主题知识看板为主入口，同时提供可搜索、可缩放的研发知识图谱。

## 当前能力

- **主题知识看板**：`/app/wiki` 汇总项目知识主题，每个主题提供简报（当前理解、关键决策、开放问题）、来源追溯与置信度。
- **知识健康**：Claim / Evidence / Signal 信号流，人工复核（acknowledge / resolve / dismiss）与评审闭环。
- **任务收件箱**：多来源建卡（实时需求、知识信号、执行发现、人工），上下文装配（Context Pack / Knowledge Gap）与状态流转。
- **文件图谱**：扫描 `INKDESK_VAULT_ROOT/wiki` 与 `INKDESK_REPO_ROOT` 中的 Markdown，解析文档关系，在图谱画布中展示完整拓扑。
- **实时更新**：Watchdog 监听文件变化，通过 SSE 推送新快照；图谱降噪、语义缩放与侧滑 Markdown 阅读器。
- **DAG 引擎**：纯内存 Kahn/BFS 调度和 SSE 流式结果，不依赖任务表或数据库。
- **技术方案 Skill**：从 Markdown PRD 并发完成需求、知识库、代码仓和安全分析，生成合规方案并原子写入 Vault。
- **Harness 审计**：确定性采集仓库证据，三路只读 Specialist 并发分析，由 Lead 冻结五维评分和 Findings。
- **持久 Run**：JSONL 事件、Evidence、Findings 与报告可在服务重启后继续读取。

## 架构

```text
Markdown files (Vault 为长期真相)
      |
      v
FastAPI graph index + knowledge / task runtimes + Harness Runtime
      |  JSON / SSE
      v
Next.js 知识看板 / 图谱 / 任务 / 健康工作台
```

PostgreSQL、pgvector、持久化 Job 队列和旧 CRUD 页面不在当前运行链路中；知识健康与任务使用本地 SQLite 投影（`server/.data/`），可随时从 Vault 文件重建。

## 页面与入口

| 路径 | 用途 |
| --- | --- |
| `/app` | 重定向到主题知识看板 |
| `/app/wiki` | 主题知识看板（第一产品主入口） |
| `/app/wiki/[id]` | 主题简报：当前理解、关键决策、来源与相关资料 |
| `/app/wiki/graph` | 知识图谱画布（辅助探索视图） |
| `/app/tasks` | 任务收件箱：建卡、上下文装配、状态流转 |
| `/app/health` | 知识健康信号与人工复核 |
| `/app/runs/[runId]` | 只读 Harness Run 检查器 |

## 本地启动

后端需要 Python 3.12+：

```powershell
Set-Location server
python -m pip install -e ".[dev]"
python -m uvicorn inkdesk_server.main:app --host 127.0.0.1 --port 8080
```

新开终端启动前端（Node.js 20.9+）：

```powershell
Set-Location web
npm install
npm run dev
```

打开 `http://localhost:3000/app/wiki`。前端默认代理到 `http://localhost:8080`，也可通过 `INKDESK_API_BASE_URL` 覆盖。

## Docker 快速启动

```powershell
docker compose -f infra/docker-compose.local-docker.yml up -d --build
```

容器健康后执行官方演示：

```powershell
docker compose -f infra/docker-compose.local-docker.yml exec local-server inkdesk run tech-solution --prd /app/repository/examples/mock-interview-prd.md
```

打开 `http://localhost:3000/app/wiki/graph`，可以观察来源 PRD 节点运行脉冲、新技术方案节点、依赖边和侧栏 Mermaid 时序图。默认 `deterministic` 模式用于无密钥演示；配置 `INKDESK_AGENT_RUNTIME=provider`（兼容旧值 `langgraph`）和对应 Provider 密钥后使用真实模型，调用失败不会降级到本地输出。

Docker 组合只包含 Web 和 FastAPI 服务；镜像内置 `inkdesk` CLI 与官方 Skills，Markdown Vault 使用具名卷，仓库以只读方式挂载，生成目录保持可写。

Docker 中可以运行离线 Harness 演示：

```powershell
docker compose -f infra/docker-compose.local-docker.yml exec local-server `
  inkdesk run harness-audit --executor deterministic --depth quick --repo /app/repository
```

真实 Claude Executor 首期只支持宿主机 Server。Claude 凭据由 Claude Agent
SDK/Claude Code 自身管理，Inkdesk 不读取或记录凭据。Executor 使用 Claude
Code 原生 safe mode，只从 user settings 获取 Provider 认证与模型映射，因此
兼容 CCSwitch 管理的 DeepSeek 等第三方 API，同时禁用 CLAUDE.md、Skills、
Hooks、Plugins、MCP 与 Commands。Inkdesk 的 PreToolUse Policy 独立于用户
权限设置执行，防止 allow 规则绕过 Harness：

```powershell
Set-Location server
python -m pip install -e ".[dev,claude]"
inkdesk executor claude --live
inkdesk run harness-audit --executor claude --depth quick --repo ..
```

运行开始后 CLI 会打印 `runId`。三个 Specialist 在冻结到同一 HEAD 的独立
临时 worktree 中并发使用只读 Agent 工具；Lead 只读取冻结 Evidence。浏览器可打开
`http://localhost:3000/app/runs/<runId>` 查看阶段、证据、五维评分、Findings
、工具时间线、一次性只读审批与报告。选择 `codex` 会明确返回
`EXECUTOR_NOT_AVAILABLE`；本版本不宣称
支持 Codex、代码生成或自动修复。

本地运行 CLI：

```powershell
inkdesk run tech-solution --prd examples/mock-interview-prd.md
```

旧版 `--target` 暂时作为 `--prd` 的弃用别名保留。

## 验证

```powershell
Set-Location server
python -m pytest -q

Set-Location ../web
npm test
npm run typecheck
npm run lint
npm run build
npm run e2e
```

## 核心接口

- `GET /health`
- `GET /api/graph?source=vault|repo`
- `GET /api/graph/document?nodeId=...`
- `GET /api/graph/stream?source=vault|repo`
- `GET /api/knowledge/topics`、`GET /api/knowledge/search?q=...`
- `GET /api/knowledge/topics/{topic_id}/briefing|sources|claims`
- `GET /api/knowledge/signals`、`POST /api/knowledge/signals/{signal_id}/actions`
- `GET /api/knowledge/health/summary`、`GET/POST /api/knowledge/reviews`
- `GET /api/knowledge/stream`（SSE）
- `GET /api/tasks`、`POST /api/tasks`
- `GET /api/tasks/stream`（SSE）、`POST /api/tasks/{task_id}/context|transition`
- `GET /api/engine/health`
- `POST /api/engine/stream`
- `POST /api/skills/{skill_id}/stream`
- `POST /api/runs`、`GET /api/runs/{run_id}`、`GET /api/runs/{run_id}/events`、`POST /api/runs/{run_id}/cancel`

## 版本范围

v0.2.0 保留 Observer、Indexer 和 `tech-solution` 闭环，交付首个 Inkdesk-native
Harness、Claude 只读 Executor、Better Harness 审计与 Run Inspector；本分支在此之上
叠加知识健康与任务工作流（K1-K3）与 K0「Knowledge Context-first」方向修订。
Codex Adapter、Finding 修复、代码生成、隔离工作树与人工审批进入下一迭代。

## 仓库结构

```text
web/       Next.js 知识看板 / 图谱 / 任务 / 健康工作台与前端测试
server/    FastAPI 文件索引、知识运行时、DAG 引擎与 Skill SDK
infra/     无数据库依赖的本地容器配置
docs/      设计、决策与历史交付资料
```

## 文档

- [产品愿景](docs/product/产品愿景.md) · [产品定位与形态](docs/product/产品定位与形态.md) · [产品路线图](docs/product/产品路线图.md)
- [K0 长期路线图](docs/superpowers/plans/2026-08-04-inkdesk-codex-integrated-long-term-roadmap.md)
- [领域模型](docs/architecture/领域模型.md)
- [文档索引](docs/文档索引.md)
