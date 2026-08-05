# Inkdesk

Inkdesk 是一个面向研发知识的轻量观测与治理中枢。它以只读拓扑呈现知识节点、来源、证据覆盖和风险信号，并通过 Vault 与 MCP 接收外部工具产生的结果。

## 当前能力

当前版本已提供单实例、无需登录的本地工作区，核心闭环如下：

```text
外部 CLI / Agent -> Vault 文件 -> 检索索引 -> Wiki 拓扑
                         \-> Ask 文件快照
```

- **Wiki 拓扑与证据治理**：浏览长期知识、来源、Claim 状态、冲突与待解决问题。
- **只读监控卡片**：前端不承载编辑、提交、编译或阶段状态机。
- **文件快照**：Ask 的线程、检索和判断快照写入 Vault，不再扩张关系型数据库表。
- **MCP CLI 接口**：提供 `search`、`deposit` 和 `health_check` 三个精简工具。
- **Skill Workbench**：浏览和查看可复用研发动作的契约与门禁。
- **Compile / Health**：查看编译流水线和知识库健康状态。
- **本地基线与恢复工具**：保存关键行为契约、数据指纹和恢复演练证据，防止后续迭代破坏已有闭环。

## 产品方向

Inkdesk 的长期链路是：

```text
Sources -> Wiki / Schema / Skills / Policies -> Evaluation -> Harness
        -> Delivery -> Outcome Observation -> Capability Feedback
```

当前优先验证 `PRD -> Context Pack -> 技术方案 -> 独立技术评审`，并逐步扩展至编码、测试和受控执行。完整的动态 Harness、团队级权限治理、Capability Replay & Relay 与结果观测仍处于设计和验证阶段，不应视为已完成能力。

## 架构

```text
Next.js Web
  |  /api proxy and server actions
  v
FastAPI service
  |-- PostgreSQL + pgvector: 权限元数据与检索索引
  |-- Vault Markdown / JSON: 长期知识、能力文件与 Ask 快照
  |-- LLM providers / external executors
  `-- local compiler, review and evaluation services
```

已接受的知识以 Vault 中的 Markdown 形式保留，数据库负责工作流状态与可重建的派生索引。AI 可以生成提案，但不能静默改写正式知识。

## 页面与入口

| 路径 | 用途 |
| --- | --- |
| `/app` | 重定向到 Wiki 拓扑 |
| `/app/wiki` | 知识拓扑监控 |
| `/app/wiki/[id]` | Wiki 节点只读详情 |
| `/app/raw` | 来源只读快照 |
| `/app/skills` | Skill Workbench |
| `/app/health` | 知识库健康检查 |

## 技术栈

- Web：Next.js 16、React 19、TypeScript、Tailwind CSS
- Service：Python 3.12+、FastAPI、SQLAlchemy、LangGraph
- Data：PostgreSQL 16、pgvector、Vault Markdown
- Integrations：OpenAI-compatible providers、DeepSeek、Claude Agent SDK、MCP
- Tests：pytest、Vitest、node:test、Playwright

## 快速启动

### 前置条件

- Docker Desktop
- Node.js 20+
- Python 3.12+（本地开发和后端测试需要）

### 一键启动完整本地栈

在 PowerShell 中执行：

```powershell
Copy-Item infra/.env.example infra/.env
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml up -d --build
```

按需编辑 `infra/.env`，配置模型服务。最低配置示例：

```env
INKDESK_AGENT_RUNTIME=langgraph
INKDESK_AGENT_PROVIDER_PROFILE=openai
INKDESK_AGENT_MODEL=gpt-4.1-mini
OPENAI_API_KEY=your-api-key
INKDESK_EMBEDDING_PROVIDER_PROFILE=openai
INKDESK_EMBEDDING_MODEL=text-embedding-3-small
```

服务启动后访问：

- Web：`http://localhost:3000/app`
- API health：`http://localhost:8080/actuator/health`

停止服务但保留数据：

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml down
```

重置本地容器数据：

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml down -v
```

### 前后端分开开发

先启动 PostgreSQL 和 MinIO：

```powershell
Copy-Item infra/.env.example infra/.env
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d postgres minio
```

启动后端：

```powershell
Set-Location server
python -m pip install -e ".[dev]"
python -m uvicorn inkdesk_server.main:app --host 127.0.0.1 --port 8080
```

新开终端启动前端：

```powershell
Copy-Item web/.env.local.example web/.env.local
# 将 web/.env.local 中两个 API 地址改为 http://localhost:8080
Set-Location web
npm install
npm run dev
```

## 验证

```powershell
# 后端
Set-Location server
python -m pytest

# 前端
Set-Location ../web
npm test
npm run typecheck
npm run lint
npm run build
npm run e2e
```

真实后端全链路验证需要本地服务已启动：

```powershell
Set-Location web
npm run e2e:fullstack
```

`e2e` 与 `e2e:fullstack` 都会构建并启动 Next.js，建议串行执行。

## 仓库结构

```text
web/       Next.js 工作区与 Playwright 测试
server/    FastAPI 服务、知识编译、运行与评测逻辑
infra/     Docker Compose、镜像与环境变量模板
docs/      产品、架构、交付、运维和设计规范
scripts/   本地基线、恢复与验证脚本
```

## 文档

- [产品总设计](docs/superpowers/specs/2026-07-11-inkdesk-team-rd-capability-platform-design.md)
- [前向开发路线图](docs/superpowers/plans/2026-07-11-inkdesk-capability-platform-master-roadmap.md)
- [文档索引](docs/文档索引.md)
- [本地全栈验收](docs/delivery/本地全栈验收.md)
- [环境变量](docs/ops/环境变量.md)
- [F01 行为契约与恢复基线](docs/delivery/baselines/f01/README.md)

## 贡献约定

- 不提交密钥、令牌或本地 `.env` 文件。
- 新增运行变量时，同时更新对应 `.example` 模板和环境变量文档。
- 改动用户可见的 `web/**` 流程时，运行受影响测试并在浏览器中检查实际流程。
- 以当前代码、行为契约和权威设计文档为准；历史计划用于追溯，不应覆盖已确认的产品边界。
