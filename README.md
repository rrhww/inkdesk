我按 **2026-05-22** 的公开仓库现状写了一版首稿，目标是让人先看懂设计，再知道项目现在推进到哪一步。当前仓库名还是 `inkdesk`，所以我在开头加了一句临时说明，先把认知统一住。

```md
# Inkvault

> 一个面向单人研究工作的、私有的、vault-first 知识系统。

Inkvault 的核心目标，不是做一个“会自动帮你写答案”的笔记工具，而是构建一个**可回溯、可审阅、可恢复**的研究记忆系统。

它围绕一条很明确的主循环展开：

```text
raw -> ingest -> wiki -> ask
```

- `raw/`：保存原始研究材料，例如网页、PDF、迁移进来的笔记
- `ingest`：AI 生成提案，人来审核接受或拒绝
- `wiki/`：保存已经确认的长期知识
- `ask`：优先基于 `wiki` 提问，必要时回到 `raw`，并把新的理解重新带回审阅流程

## Why Inkvault

很多知识工具擅长保存“整理后的结果”，但不擅长保存结果是如何形成的。

Inkvault 想解决的是另一类问题：

- 原始材料和最终知识之间经常断链
- AI 可以快速生成内容，但不应该静默修改可信知识
- 研究过程需要不断回看来源、修正理解、沉淀长期记忆
- 最终留下来的知识，应该能从 vault 中被恢复出来，而不是只存在数据库里

所以 Inkvault 不是把 AI 放在最前面，而是把 **vault** 放在最前面，把 AI 放进一个**可审核的工作流**里。

## Core Model

Inkvault 的设计核心有四个层次：

### 1. Raw

`raw/` 保存原始资料，是研究过程的输入层。

它可以是网页、PDF、导入的旧笔记，重点不是“整洁”，而是完整保留上下文和来源。

### 2. Ingest

`ingest` 是候选知识生成层。

AI 可以基于原始资料提出摘要、结构化理解、wiki 新建建议或补丁建议，但这些内容都只是“待审核提案”，不能直接成为长期知识。

### 3. Wiki

`wiki/` 是已接受知识层。

只有经过人工确认的内容才会进入 wiki，成为系统中的长期记忆。wiki 不是聊天记录，也不是临时缓存，而是被明确接受的知识结果。

### 4. Ask

`ask` 是研究使用层。

提问时优先基于 `wiki` 回答，在需要时再回到 `raw`。如果一次问答产生了新的稳定理解，它应该能够重新进入 `ingest`，再经过审核回写到 `wiki`。

## Design Principles

### Vault-first

Vault 是事实来源和最终落点。数据库负责索引、状态跟踪和读模型缓存，但已接受知识必须能够从 vault markdown 中恢复。

### Human-reviewed knowledge

AI 可以提议，但不能静默改写 canonical knowledge。真正进入长期记忆的内容，必须经过人工接受。

### Provenance matters

每一个被接受的结论，都应该能追溯回原始材料，而不是只保留“结论本身”。

### Ask over accepted knowledge

系统优先基于已经确认的知识工作，而不是每次都直接对原始资料做一次新的生成。

### Single-owner by design

当前产品模型面向单一拥有者的私有研究空间，不以多用户协作为第一目标。

## Current App Shape

当前应用大致包含这些界面：

- `/`：根据 owner session 跳转到 `/login` 或 `/app`
- `/login`：隐藏式 owner 登录
- `/app`：ask-first 研究入口
- `/app/raw`：原始材料列表
- `/app/ingest`：等待审核的 AI 提案
- `/app/wiki`：已接受知识页列表
- `/app/wiki/[id]`：单篇 wiki 详情，包含 understanding、claims、questions 和 sources
- `/app/ask`：兼容别名路由

一些旧路由如 `/app/inbox`、`/app/review`、`/app/topics`、`/app/sources` 当前主要用于兼容跳转。

## Status

Inkvault 目前处于**持续演进中的早期阶段**。

当前重点不是做“大而全”的知识平台，而是先把下面几件事打磨扎实：

- vault 作为知识源的边界
- AI 提案到人工审核的工作流
- wiki 作为长期知识载体的结构
- ask-first 的研究使用体验
- 来源可追溯和知识可恢复这两条底线

如果你现在看到一些命名、路由或结构仍在调整中，这是项目当前阶段的一部分。

## Tech Stack

- Frontend: `Next.js 15`, `React 19`, `TypeScript`, `Tailwind CSS`
- Backend: `FastAPI`, `Python 3.12`, `SQLAlchemy`, `LangGraph`
- Storage: PostgreSQL + local vault markdown
- Testing: `node:test`, `Vitest`, `Playwright`, `pytest`

## Run Locally

先准备环境文件：

```powershell
Copy-Item infra/.env.example infra/.env
Copy-Item web/.env.local.example web/.env.local
```

设置必要环境变量：

```powershell
$env:INKVAULT_AUTH_SECRET='replace-with-a-long-random-secret'
$env:INKVAULT_VAULT_ROOT='C:\path\to\inkvault-vault'
$env:INKVAULT_AGENT_PROVIDER_PROFILE='openai' # or 'deepseek'
```

启动基础服务：

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

启动后端：

```powershell
cd server
python -m pip install -e .[dev]
python -m uvicorn inkvault_server.main:app --host 0.0.0.0 --port 8080
```

启动前端：

```powershell
cd web
npm install
npm run dev
```

打开：

```text
http://localhost:3000/login
```

Demo owner credentials:

- email: `owner@inkvault.local`
- password: `inkvault-owner`

## Verification

后端测试：

```powershell
cd server
python -m pytest
```

前端检查：

```powershell
cd web
npm test
npm run typecheck
npm run lint
npm run build
```

## Roadmap

接下来会优先继续打磨这些方向：

- raw -> ingest -> wiki -> ask 主循环的一致性
- wiki 页面结构和可追溯性
- 审核流程中的提案质量与可读性
- ask-first 体验和 grounded answer 边界
- 命名、路由和公开文档的统一

## Feedback

如果你对下面这些问题感兴趣，欢迎提 issue：

- vault-first 知识系统是否成立
- AI 提案 + 人工审核这个工作流是否合理
- wiki 结构是否足够清晰
- ask 与 wiki / raw 的边界应该怎么定义
- 当前 README 是否准确表达了项目设计
```

这版的重点是把“为什么存在”“系统主循环”“当前阶段”三件事讲清楚，避免现在这种只有技术信息、没有叙事骨架的状态。参考的是你的公开仓库页和当前 README：[repo](https://github.com/rrhww/inkdesk)、[current README](https://raw.githubusercontent.com/rrhww/inkdesk/main/README.md)。

下一步最值得做的不是继续润色文字，而是两件事一起补上：把仓库 `Description` 改成一句清晰定义，再加 `Topics`。我可以下一条直接给你这两个字段的推荐内容。
```
