# Inkdesk

> AI 研发自动化控制台 —— 用 LLM-Wiki 提供长期上下文，用 Skills 固化研发动作，用 Evaluation / Harness 把 PRD 到交付编排成可控流程。

Inkdesk 的灵感来自文章《AI研发自动化：Wiki知识库+技能包》和 Andrej Karpathy 的 LLM-Wiki 模式：知识不再每次重新发现，而是被摄入、合并、交叉引用，沉淀为服务后续研发任务的长期上下文。

## 控制面 vs 执行面

Inkdesk **不替代** Claude Code 或 Codex，而是把自己定位成**控制面**，把代码执行委托给外部 Agent：

```text
Inkdesk 控制面（知识 + 流程）
  ├─ 管理记忆：raw → ingest → wiki，长期知识持续生长
  ├─ 准备上下文：Context Pack，让每个任务带着完整背景开始
  ├─ 编排流程：技术方案 → 评审 → gate → coding briefing
  ├─ 审阅门禁：阶段产物不通过审阅不进下一阶段
  └─ 评测验证：Golden Tasks + LLM Judge，用数据驱动改进

外部 Agent 执行面（代码 + 测试）
  ├─ 读代码仓库、写文件
  ├─ 执行 coding
  ├─ 跑测试、看报错
  └─ debugging / 修复
```

Inkdesk 做外部 Agent 做不到的事：让这次 coding 的判断不散掉，让下次任务知道上次发生了什么。Harness 在 gate 放行后调用外部 Agent 执行，执行结果通过 `run_event` 自动回写——用户始终待在 Inkdesk Web 里，不需要切窗口。

同时 MCP 保留手动路径：用户在 Claude Code 里做探索性工作时，可以手动拉 context_pack、手动 deposit。两条路径共用同一套 MCP 工具。

## 当前闭环

已实现的内部闭环：

```text
raw -> ingest -> wiki -> ask
```

- `raw/`：网页、PDF、导入笔记等原始材料。
- `ingest`：AI 理解材料，生成审阅提案，由 owner 接受或拒绝。
- `wiki/`：已接受的长期知识页（Markdown），可脱离 Inkdesk 阅读。
- `ask`：优先基于 wiki 回答，再回退 raw，有价值回答可沉淀回审阅队列。

Ask 不是产品首页，而是 Dev Run 里的上下文查询能力（Context Ask）。

## 目标形态

产品主入口从 Ask-first 调整为 Dev Run-first：

```text
PRD / bug / 改造任务
  → Dev Run
  → Context Pack
  → 技术方案 / 技术评审 / Coding / 测试
  → Review / Deposit
  → Wiki / Runs / Evals
```

界面结构：

```text
/app
├── runs/          研发任务台 —— PRD / bug / 改造任务的入口与阶段轨道
├── ask/           Context Ask —— 为当前任务查询长期上下文
├── review/        审阅台 —— AI 提案、方案、wiki patch、沉淀裁决
├── wiki/          知识库浏览 —— 页面、claim、来源追溯
├── skills/        技能工作台 —— 技术方案、评审、coding、测试、排查
├── health/        健康仪表盘 —— 知识、Skill、评测与运行质量
├── evals/         评测中心 —— golden tasks、版本对比、晋级门禁
└── settings/      基础设置
```

Vault 文件结构保持 portable：

```text
vault/
  raw/        原始材料
  wiki/       已接受的长期知识页
  schema/     面向 Agent 的维护规则
  skills/     可复用工作流说明
  evals/      golden tasks、rubrics 和评测运行记录
  runs/       Agent 运行记录、输出和审阅状态
```

PostgreSQL 负责索引、队列和工作流状态。已接受的知识必须能从 vault Markdown 中恢复。

## 设计原则

- **File-first**：已接受知识应能在 Inkdesk 外部阅读、编辑、版本化。
- **Review-first**：AI 可提案，不能静默改写正式知识。
- **Skill-first**：重复工作固化为显式文件，含输入、输出契约和 Hard Gates。
- **Control-plane-first**：Inkdesk 管知识和流程，coding 执行委托给外部 Agent。
- **Runtime-agnostic**：当前用 LangGraph 做知识编排，未来也要能接入 Claude Code、Codex 等执行器。
- **Evaluation-driven**：Wiki 和 Skill 优化靠 health checks 和 golden tasks 验证，不只凭感觉。

## 与文章方案的区别

| | 文章方案（工具拼装） | Inkdesk（产品） |
|------|------|------|
| 知识摄入 | Claude Code 对话中执行 skill | Web 引导式上传 → 后台编译 → 审阅队列 |
| 审阅提案 | 对话中逐条确认 | 独立审阅台，diff 预览，批量操作 |
| 知识浏览 | Obsidian | Web 内浏览 + 来源追溯 |
| 搜索 | qmd CLI | Context Ask，服务当前研发任务 |
| 健康检查 | 手动跑 lint | 自动定期扫描 + 仪表盘 + 趋势图 |
| 评测 | `claude -p` 子进程 | 评测中心：golden tasks → 跑分 → 版本对比 |
| 多平台 | 手动配置各平台 | MCP 作为可选扩展 |
| 上手 | 需学会 Obsidian + qmd + Git + Claude Code | 自行部署后打开浏览器即可使用 |

## 开发进度

### 已完成：阶段一主体闭环

- [x] 单实例、单用户、无登录的 `/app` 工作区。
- [x] `raw -> ingest -> wiki -> ask` 闭环。
- [x] raw 文本、网页、PDF 导入。
- [x] AI 审阅提案，接受 / 拒绝。
- [x] Wiki 页面写回 vault Markdown。
- [x] Ask 工作区：引用回答、追问、writeback 提案。
- [x] claim 级证据状态、来源链接、stale/conflict 信号。
- [x] 本地 Docker 栈：Next.js、FastAPI、PostgreSQL、pgvector。
- [x] 后端 pytest 和前端 typecheck 作为当前基线验证。

### 当前重点：第二步（2.1–2.5）

详细计划见 [开发计划总指南](docs/development/plans/开发计划总指南.md)。

**2.1 Dev Run Console**（最优先）

- [ ] `/app` 从 Ask 问答框改为研发任务台
- [ ] PRD / bug / 改造任务入口
- [ ] 阶段轨道、待确认输出、可用 Skills 摘要

**2.2 Context Ask + Deposit**

- [ ] 每次回答提供"沉淀"入口（整条回答 + 选中片段）
- [ ] 沉淀记录关联到 Dev Run，所有沉淀走 ingest 审阅
- [ ] Ask 降级为 Context Ask，不再作为 `/app` 首页

**2.3 Wiki Health 基础**

- [ ] 断链、孤页、缺 frontmatter、缺来源四类结构检查

**2.4 薄 MCP Server**

- [ ] `context_pack`、`search`、`deposit`、`health_check`
- [ ] 所有写入继续走 review-first

**2.5 异步编译流水线与审阅队列**

- [ ] Insight Extractor → Evidence Binder → Topic Router → Conflict Checker → Patch Writer
- [ ] 审阅队列：diff 预览、接受/拒绝、批量操作
- [ ] vault 初始化生成 `index.md`、`log.md`、`KB-META.md`

### 下一阶段：Skill Workbench + Evaluation

- [ ] vault 中加入 `schema/` 和 `skills/` 约定
- [ ] 首批 13 个 Skill（知识管理 6 个 + 研发自动化 7 个）
- [ ] Skill Workbench：浏览、运行、审阅、导出
- [ ] Evaluation：golden tasks、LLM Judge、σ₀ 基线
- [ ] review 与 evaluation 可靠后，推进 Harness

## 当前路由

- `/`：直接跳转到 `/app`。
- `/app`：当前已实现为 Ask 工作区；目标是 Dev Run Console。
- `/app/raw`：原始 vault 材料。
- `/app/ingest`：待处理的 AI 提案。
- `/app/wiki`：已接受的 Wiki 页面。
- `/app/wiki/[id]`：单个 Wiki 页面详情（understanding、claims、questions、sources）。
- `/app/ask`：Context Ask，服务研发任务的上下文查询和沉淀。

旧路由 `/app/inbox`、`/app/review`、`/app/topics`、`/app/sources` 不再是正式产品入口。

## 技术栈

- 前端：`Next.js 16`、`React 19`、`TypeScript`、`Tailwind CSS`
- 后端：`FastAPI`、`Python 3.12`、`SQLAlchemy`、`LangGraph`
- MCP Server：`Python`（`mcp` 包），作为 Harness 与外部 Agent 的通信协议
- 存储：`PostgreSQL + pgvector`（索引和队列），`Vault Markdown`（真相层）
- 测试：`node:test`、`Vitest`、`Playwright`、`pytest`

## 快速启动

```bash
cp infra/.env.example infra/.env
```

至少设置：

```env
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

启动：

```bash
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml up -d --build
```

- 应用：`http://localhost:3000/app`
- 后端健康：`http://localhost:8080/actuator/health`

停止（保留数据）：
```bash
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml down
```

重置：
```bash
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml down -v
```

## 验证

```powershell
# 后端
cd server
python -m pytest

# 前端
cd web
npm test
npm run typecheck
npm run lint
npm run build
npm run e2e
npm run e2e:fullstack
```

`npm run e2e` 和 `npm run e2e:fullstack` 需要串行运行，二者都会触发 Next.js build/start。

## 相关文档

**产品**
- [产品定位与形态](docs/product/产品定位与形态.md)
- [产品愿景](docs/product/产品愿景.md)
- [产品路线图](docs/product/产品路线图.md)

**架构**
- [系统总览](docs/architecture/系统总览.md)
- [工具链与模型上下文协议](docs/architecture/工具链与模型上下文协议.md)
- [技术决策](docs/architecture/技术决策.md)

**开发计划**
- [开发计划总指南](docs/development/plans/开发计划总指南.md)
- [知识库初始化设计](docs/development/specs/2026-06-05-知识库初始化设计.md)
- [大模型维基与技能工作台产品设计](docs/development/specs/2026-06-04-大模型维基与技能工作台产品设计.md)
