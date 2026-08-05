# AGENTS.md

## Skill Policy

Do not invoke `omni-superdev` or any `superpowers:*` skill for work in this repository. This project-level rule takes precedence over default skill routing and applies to all tasks in the repository.

## Project Architecture Overview

Inkdesk 是一个知识治理平台，采用 **单实例、默认 workspace、无登录** 架构。系统由三个核心模块组成：

### `server/` — Python 后端

- 基于 **FastAPI** 的 REST/SSE 服务，入口 `inkdesk_server.main:app`
- 职责：知识索引、问答（Ask）、Dev Run 阶段推进、Wiki 编译、健康检查
- 关键子模块：
  - `inkdesk_server/` — 核心业务逻辑（engine、graph_index、knowledge、tasks、schemas）
  - `inkdesk_skill_sdk/` — Skill 开发 SDK（registry、scaffolder、scheduler、validation）
  - `tests/` — pytest 测试套件
- 默认端口 `8080`

### `web/` — Next.js 前端

- 基于 **Next.js + React + TypeScript + Tailwind CSS** 的单页应用
- 职责：Dev Run Console（`/app`）、Wiki 浏览、Ask 交互、Ingest 审阅、Compile/Health 页面
- 关键目录：
  - `app/` — 页面路由（layout、page、login、app 子路由）
  - `components/` — 共享 UI 组件
  - `lib/` — API 客户端与工具函数
  - `tests/` — Vitest 单元/集成测试 + Playwright E2E
- 默认端口 `3000`，API 通过同源 `/api/**` 代理到后端

### `server/vault/` — 知识库与技能

- Vault 是知识长期真相的存储层，包含 `raw/`（原始素材）、`wiki/`（结构化知识页）、`skills/`（13 个正式技能）
- 职责：知识沉淀（ingest → wiki → ask 主路径）、技能执行、知识治理
- 技能列表：`answer-from-wiki`、`coding`、`deposit-answer`、`extract-insight`、`ingest-source`、`patch-wiki-page`、`problem-solve`、`run-wiki-health`、`skill-router`、`tech-review`、`tech-solution`、`test-fix`、`test-prep`
- 默认数据目录 `server/inkdesk-vault/`（可通过 `INKDESK_VAULT_ROOT` 环境变量覆盖）

### 基础设施

- **PostgreSQL**（端口 5432）：索引、提案、session、问答记录
- **MinIO**（API 9000 / Console 9001）：对象存储占位
- 通过 `infra/docker-compose.yml` 统一管理

## Key Design Documents

深入理解项目设计时，参考以下文档：

| 主题 | 路径 |
|------|------|
| 系统架构总览 | `docs/architecture/系统总览.md` |
| 领域模型 | `docs/architecture/领域模型.md` |
| 数据库结构 | `docs/architecture/数据库结构.md` |
| 接口草案 | `docs/architecture/接口草案.md` |
| 技术决策 | `docs/architecture/技术决策.md` |
| 工具链与 MCP | `docs/architecture/工具链与模型上下文协议.md` |
| 开发计划总指南 | `docs/development/plans/开发计划总指南.md` |
| Dev Run 阶段动作设计 | `docs/development/specs/2026-07-09-dev-run-stage-actions-design.md` |
| Coding Interactive SSE 设计 | `docs/development/specs/2026-07-10-coding-interactive-sse-design.md` |
| 知识库初始化设计 | `docs/development/specs/4.1.1-最初建设-知识库初始化设计.md` |
| 大模型维基与技能工作台设计 | `docs/development/specs/2026-06-04-大模型维基与技能工作台产品设计.md` |

## Local Development Commands

### 环境准备

```powershell
# 复制环境模板
Copy-Item infra/.env.example infra/.env
Copy-Item web/.env.local.example web/.env.local
```

### 启动基础设施（PostgreSQL + MinIO）

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

### 启动后端

```powershell
cd server
python -m pip install -e .[dev]
python -m uvicorn inkdesk_server.main:app --host 127.0.0.1 --port 8080
```

### 启动前端

```powershell
cd web
npm install
npm run dev
```

### 验证命令

```powershell
# 后端测试
cd server && python -m pytest

# 前端单元/集成测试 + 类型检查 + lint + 构建
cd web && npm test && npm run typecheck && npm run lint && npm run build

# 前端默认 E2E
cd web && npm run e2e

# 全链路 E2E（需要后端 + 基础设施就绪）
cd web && npm run e2e:fullstack
```

### 访问入口

- 前端工作区：`http://localhost:3000/app`
- 后端 API：`http://localhost:8080`

## Engineering Rules

- Read the minimal local context required for the task.
- Keep changes scoped and avoid unrelated refactors.
- For bug fixes, write the failing test first, confirm it fails for the expected reason, then fix the bug.
- For user-visible changes in `web/**`, review the affected flow in a real browser before signoff.
- For documentation screenshots in Markdown, avoid fixed `height` attributes on `<img>` tags; prefer Markdown images or width-only HTML so previews preserve aspect ratio.
- Never commit secrets or credentials.
- Keep `.env*.example` files synchronized with required environment variables.

