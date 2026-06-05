# Inkdesk

> 个人 AI 知识工坊 —— LLM-Wiki 知识库 + Skill 技能包 + 评测系统，整合成一个完整的应用。

Inkdesk 被塑造成面向 AI 时代的个人知识控制台。灵感来源于文章《AI研发自动化：Wiki知识库+技能包》及其背后 Andrej Karpathy 提出的 LLM-Wiki 模式：知识不再每次重新发现，而是被一次次摄入、合并、交叉引用，沉淀为一份不断生长的、活的、可演化的知识库。

产品方向是：

```text
LLM-Wiki + Skill Workbench + Agent Harness
```

Inkdesk 不替代 Obsidian、Claude Code、LangGraph 或未来的 Agent Runtime。它管理这些执行器所需要的记忆层与工作流底座：

```text
Inkdesk 管理记忆、技能、评测、运行状态和审阅。
外部 Agent Runtime 负责执行。
Vault Markdown 保持可迁移、可检查、可版本化。
```

如果你也用 Claude Code 或 Codex，Inkdesk 通过 MCP 接入它们，作为统一的知识底座。但 Inkdesk 本身是一个独立、完整的产品。

## 产品理念

Inkdesk 不是普通 RAG 应用。

传统 RAG 在查询时从原始文档切片里检索并生成答案。Inkdesk 更接近一种写入时知识系统：来源材料会被编译成持续生长的 Markdown Wiki，查询结果可以变成可审阅的 Wiki 提案，Skills 把重复工作固化为可复用流程，评测系统检查知识库和技能是否真的变好。

当前内部研究闭环仍然是：

```text
raw -> ingest -> wiki -> ask
```

- `raw/` 保存网页、PDF、导入笔记，以及未来的代码或项目上下文等原始材料。
- `ingest` 把 raw 材料转成 AI 生成的审阅提案，由 owner 接受或拒绝。
- `wiki/` 保存已经接受的长期知识页，格式是 Markdown。
- `ask` 优先基于已接受的 Wiki 回答，再回退到 raw，并能把有价值回答送回审阅。

Ask 不只是问答，而是知识生产的起点：

```text
提问 → 基于 Wiki 回答（带来源引用）
     → 追问（上下文自动关联）
     → 选中有价值片段 → 一键沉淀
     → 后台拆解 → 生成 Wiki patch 提案
     → 进入审阅队列
```

下一层产品能力会扩展为：

```text
schema -> skills -> evals -> runs -> harness
```

- `schema/` 定义 Agent 应该如何维护 Wiki。
- `skills/` 保存可复用的工作流说明。
- `evals/` 保存 golden tasks 和 rubrics。
- `runs/` 记录 Agent 输出、决策和审阅状态。
- `harness` 用门禁、重试和回滚记录来编排多步骤工作。

## 产品形态

### 界面结构

```text
/app
├── ask/           主工作区 —— 提问、追问、沉淀
├── review/        审阅台 —— 待处理的 AI 提案（接受/拒绝/修改）
├── wiki/          知识库浏览 —— 页面、关联图、来源追溯
├── skills/        技能工作台 —— 浏览、运行、审阅输出
├── health/        健康仪表盘 —— 问题列表、质量趋势
├── evals/         评测中心 —— 跑分、版本对比、改进建议
└── settings/      基础设置
```

### MCP Server

MCP Server 是产品的延伸，让已经在用 Claude Code 或 Codex 的用户也能接入同一套知识底座：

```text
人在 Inkdesk Web → 提问、审阅、管理
人在 Claude Code  → 通过 MCP 取上下文、提交沉淀 → 回到 Inkdesk 审阅
```

两条路径共享同一个 vault 和同一个审阅队列。

## 与文章方案的区别

| | 文章方案（工具拼装） | Inkdesk（产品） |
|------|------|------|
| 知识摄入 | Claude Code 对话中执行 skill | Web 引导式上传 → 后台编译 → 审阅队列 |
| 审阅提案 | 对话中逐条确认 | 独立审阅台，diff 预览，批量操作 |
| 知识浏览 | Obsidian | Web 内浏览 + 关联图 + 来源追溯 |
| 搜索 | qmd CLI | 内置搜索，搜索即对话 |
| 健康检查 | 手动跑 lint | 自动定期扫描 + 仪表盘 + 趋势图 |
| 评测 | `claude -p` 子进程 | 评测中心：配置 golden tasks → 跑分 → 对比版本 |
| 多平台 | 手动配置各平台 | 开箱即用，MCP 作为可选扩展 |
| 上手 | 需学会 Obsidian + qmd + Git + Claude Code | 打开浏览器，登录，开始 |

## 从文章吸收的结构改进

- Schema 在内容灌入前就位，不做事后补救
- 初始化就生成 `index.md`、`log.md`、`KB-META.md`
- 页面 frontmatter 从初始化就包含 `status` 字段（stub / draft / stable / outdated）
- 评测系统按四层设计：结构层 → 实用层 → 信号层 → 治理层
- 盲评机制：分离生成和评分，避免自我偏好

## 目标形态

长期 vault 结构应该保持 file-first 和 portable：

```text
vault/
  raw/        原始材料
  wiki/       已接受的长期知识页
  schema/     面向 Agent 的维护规则
  skills/     可复用工作流说明
  evals/      golden tasks、rubrics 和评测运行记录
  runs/       Agent 运行记录、输出和审阅状态
```

应用层覆盖在 vault 之上：

```text
Raw Library
Ingest Review
Wiki Browser
Ask / Research Chat
Skill Workbench
Wiki Health
Evaluation Harness
Agent Run Console
```

PostgreSQL 负责索引文件、排队提案、保存工作流状态和缓存读模型。已经接受的长期知识必须始终能从 vault Markdown 中恢复。

## 设计原则

- File-first：已接受知识应该能在 Inkdesk 外部阅读、编辑、版本化。
- Review-first：AI 可以提出 Wiki 修改，但不能静默改写正式知识。
- Skill-first：重复工作应该成为显式文件，包含输入、上下文、输出契约、安全规则和验证要求。
- Runtime-agnostic：Inkdesk 现在可以使用 LangGraph，未来也要能接入 Claude Code、Codex 等外部工具。
- Evaluation-driven：Wiki 和 Skill 的优化要通过 health checks 与 golden tasks 判断，不能只凭感觉。
- Obsidian-compatible where useful：vault 应该能被普通 Markdown 工具理解，但不把 Obsidian 作为硬依赖。

## 开发进度

Inkdesk 不是从零开始转向新形态。当前已经有一条可运行的私有研究闭环，接下来是在这个闭环上叠加 MCP 接入、回答沉淀、Skills、评测和外部 Agent 接入。

### 已完成：阶段一主体闭环

- [x] 单 owner 私有登录、本地 `/app` 工作区、隐藏登录入口。
- [x] Vault-first 的 `raw -> ingest -> wiki -> ask` 主闭环。
- [x] raw 文本、网页、PDF 导入。
- [x] AI 生成审阅提案，支持接受 / 拒绝。
- [x] 已接受 Wiki 页面写回 vault Markdown。
- [x] Ask-first 工作区，支持引用回答、追问上下文和 writeback 提案。
- [x] claim 级证据状态、来源链接、usage、stale/conflict 信号。
- [x] 本地 Docker 栈：Next.js、FastAPI、PostgreSQL、pgvector。
- [x] 后端 `python -m pytest` 与前端 `npm run typecheck` 已作为当前基线验证。

### 当前重点：MCP Server

开发顺序调整为：

```text
MCP Server → 后台编译流水线 → 薄仪表盘 → 完整产品
```

先打造 MCP Server（context_pack / deposit / search），让知识能在 Claude Code 等外部 Agent 的对话中自然流转。然后建设后台异步编译流水线和审阅队列，再逐步叠加产品侧的完整体验。

- [ ] MCP Server：`context_pack`、`deposit`、`search`、`health_check`
- [ ] 后台异步知识编译流水线（Insight Extractor → Evidence Binder → Topic Router → Conflict Checker → Patch Writer）
- [ ] 审阅队列：结构化提案审阅、diff 预览、批量操作
- [ ] 每个回答固定提供"沉淀这次回答"
- [ ] 支持完整回答与选中片段两种沉淀入口
- [ ] 增加基础 Wiki Health：缺 frontmatter、缺来源、断链、孤页
- [ ] vault 初始化生成 `index.md`、`log.md`、`KB-META.md`

### 下一阶段：Schema 与 Skill Workbench

MCP Server 和异步流水线稳定后，继续按文章流程推进：

- [ ] 在 vault 中加入 `schema/` 和 `skills/` 约定。
- [ ] 初始化 `schema/vault-layout.md`、`schema/wiki-page-template.md`、`schema/source-citation-rules.md` 等维护规则。
- [ ] 增加 Skill Workbench，用于浏览、运行、审阅、导出 skills。
- [ ] 增加 Evaluation Harness，用 golden tasks 对比 skill/wiki 版本效果。
- [ ] 只有当 review 与 evaluation 足够可靠后，再推进更高自治度的 Agent Harness。

完整阶段计划见 [产品路线图](docs/product/产品路线图.md)。

## 当前路由

- `/`：根据 owner session 跳转。
- `/login`：隐藏 owner 登录入口。
- `/app`：Ask-first 研究工作区。
- `/app/raw`：原始 vault 材料。
- `/app/ingest`：等待处理的 AI 提案。
- `/app/wiki`：已接受的 Wiki 页面。
- `/app/wiki/[id]`：单个 Wiki 页面详情，包含 understanding、claims、questions 和 sources。
- `/app/ask`：Ask 工作区的兼容别名。

旧路由 `/app/inbox`、`/app/review`、`/app/topics`、`/app/sources` 当前不再是正式产品入口。

## 技术栈

- 前端：`Next.js 16`、`React 19`、`TypeScript`、`Tailwind CSS`
- 后端：`FastAPI`、`Python 3.12`、`SQLAlchemy`、`LangGraph`
- MCP Server：`Python`（`mcp` 包），作为产品延伸
- 存储：`PostgreSQL + pgvector` 保存索引和工作流状态，挂载的 vault Markdown 保存 raw/wiki 真相层
- 测试：`node:test`、`Vitest`、`Playwright`、`pytest`

## 快速启动

准备环境变量：

```bash
cp infra/.env.example infra/.env
```

至少设置：

```env
INKDESK_AUTH_SECRET=replace-with-a-long-random-secret
INKDESK_AGENT_RUNTIME=langgraph
INKDESK_AGENT_PROVIDER_PROFILE=openai
OPENAI_API_KEY=sk-xxxx
INKDESK_AGENT_MODEL=gpt-4.1-mini
INKDESK_EMBEDDING_PROVIDER_PROFILE=openai
INKDESK_EMBEDDING_MODEL=text-embedding-3-small
INKDESK_ENABLE_WEB_ASSIST=true
```

如果使用 DeepSeek：

```env
INKDESK_AGENT_RUNTIME=langgraph
INKDESK_AGENT_PROVIDER_PROFILE=deepseek
DEEPSEEK_API_KEY=sk-xxxx
INKDESK_AGENT_MODEL=deepseek-v4-flash
```

启动本地 Docker 栈：

```bash
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml up -d --build
```

打开：

- 应用：`http://localhost:3000/login`
- 后端健康检查：`http://localhost:8080/actuator/health`

默认本地 owner：

- 邮箱：`owner@inkdesk.local`
- 密码：`inkdesk-owner`

停止容器但保留数据：

```bash
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml down
```

重置本地 demo 数据：

```bash
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml down -v
```

## 验证

后端：

```powershell
cd server
python -m pytest
```

前端：

```powershell
cd web
npm test
npm run typecheck
npm run lint
npm run build
npm run e2e
npm run e2e:fullstack
```

`npm run e2e` 和 `npm run e2e:fullstack` 需要串行运行，因为二者都会触发 Next.js build/start 流程。

## 相关设计文档

- [产品定位与形态](docs/product/产品定位与形态.md)
- [产品路线图](docs/product/产品路线图.md)
- [初步开发计划](docs/development/plans/2026-06-05-初步开发计划.md)
- [知识库初始化设计](docs/development/specs/2026-06-05-知识库初始化设计.md)
- [按文章流程开发计划](docs/superpowers/plans/2026-06-04-按文章流程开发计划.md)
- [大模型维基与技能工作台产品设计](docs/superpowers/specs/2026-06-04-大模型维基与技能工作台产品设计.md)
- [产品愿景](docs/product/产品愿景.md)
- [系统总览](docs/architecture/系统总览.md)
- [工具链与模型上下文协议](docs/architecture/工具链与模型上下文协议.md)
