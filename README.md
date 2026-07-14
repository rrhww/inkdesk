# Inkdesk

Inkdesk 是一个面向研发团队的 AI 能力编译与运行平台。它把代码、文档、历史任务、测试和运行证据沉淀为可审阅、可版本化、可评测的知识与工作流，让同类研发任务能够在下一次更快、更可靠地完成。

它不是通用聊天工具、笔记软件、IDE 或编码 Agent 的替代品。Inkdesk 提供的是控制面：准备受边界约束的上下文、编排阶段、保存产物与证据、执行审阅门禁；Claude Code、Codex 等外部 Agent 可作为可替换执行器接入。

## 当前能力

当前版本已提供单实例、无需登录的本地工作区，核心闭环如下：

```text
原始材料 -> 知识编译 -> 审阅提案 -> Canonical Wiki
    ^                                  |
    |                                  v
沉淀 <---- Context Ask <---- Dev Run / 研发任务
```

- **Dev Run**：创建并追踪 PRD、缺陷或改造任务；使用阶段轨道推进任务，保存产物、证据与决策。
- **Knowledge Compiler**：导入文本、网页或 PDF，生成可接受或拒绝的知识提案，并写回 Vault。
- **Context Ask**：为当前任务查询带来源的上下文，识别知识缺口和下一步动作，并将有价值的结果沉淀回审阅队列。
- **Wiki 与证据治理**：浏览长期知识、来源、Claim 状态、冲突与待解决问题。
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
  |-- PostgreSQL + pgvector: 索引、队列、运行状态与派生视图
  |-- Vault Markdown: 长期知识和能力文件
  |-- LLM providers / external executors
  `-- local compiler, review and evaluation services
```

已接受的知识以 Vault 中的 Markdown 形式保留，数据库负责工作流状态与可重建的派生索引。AI 可以生成提案，但不能静默改写正式知识。

## 页面与入口

| 路径 | 用途 |
| --- | --- |
| `/app` | Dev Run 工作台 |
| `/app/runs/[id]` | 单个任务的阶段、产物与行动 |
| `/app/ask` | Context Ask 与沉淀 |
| `/app/raw` | 原始材料 |
| `/app/ingest` | 知识提案审阅 |
| `/app/wiki` | Wiki 浏览与来源追溯 |
| `/app/skills` | Skill Workbench |
| `/app/compile` | 知识编译流水线 |
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
