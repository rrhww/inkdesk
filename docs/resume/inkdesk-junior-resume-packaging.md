# Inkdesk 校招生 / 初级程序员简历包装报告

生成日期：2026-05-15

## 0. 结论先行

Inkdesk 更适合包装为一个「私有研究记忆系统 / AI 应用工作流 / RAG 问答与人审知识沉淀平台」项目。最稳的主线是：用户导入网页、PDF 或旧笔记到 raw，系统用检索和 LangGraph 生成 ingest 提案，人工接受后写入 wiki，再通过 ask 基于 wiki 与 raw 进行带引用问答，并把高价值回答重新送回 ingest 审阅。

最推荐投递方向排序：

1. AI 应用开发工程师 / LLM 应用后端
2. Agent / RAG / Workflow 应用开发工程师
3. 平台开发工程师 / 研究工作台 / 知识库平台
4. 初级全栈工程师
5. 分布式 / 存储开发工程师，仅能保守表达为「数据存储、检索索引、文件持久化」
6. AI 性能 / 模型推理优化工程师，不建议主打

## 1. 项目识别

| 维度 | 判断 | 证据 |
| --- | --- | --- |
| 系统类型 | AI 应用 / RAG / LLM 编排 / 中后台平台 | [README.md](../../README.md) 写明 `raw -> ingest -> wiki -> ask`；[docs/architecture/system-overview.md](../architecture/system-overview.md) 明确 LangGraph、PostgreSQL、Vault Markdown |
| 核心业务对象 | Source、ReviewItem、Topic、TopicClaim、AskTurn、RetrievalChunk | [server/inkdesk_server/models.py](../../server/inkdesk_server/models.py) 定义模型；[docs/architecture/domain-model.md](../architecture/domain-model.md) 定义领域语言 |
| 主链路 | raw 导入 -> ingest 提案 -> 人工 accept/reject -> wiki 落库/落文件 -> ask 问答 -> writeback 提案 | API 在 [server/inkdesk_server/main.py](../../server/inkdesk_server/main.py)；编排在 [server/inkdesk_server/research.py](../../server/inkdesk_server/research.py) |
| 数据事实来源 | Vault Markdown 是长期真相，数据库做索引、队列和状态 | [README.md](../README.md)；[server/inkdesk_server/vault.py](../../server/inkdesk_server/vault.py) |
| 检索形态 | 应用层 chunk + lexical fallback / embedding hybrid | [server/inkdesk_server/retrieval.py](../../server/inkdesk_server/retrieval.py)；[server/inkdesk_server/embeddings.py](../../server/inkdesk_server/embeddings.py) |
| AI 编排 | LangGraph Ask / Compile graph，结构化输出，确定性 fallback | [server/inkdesk_server/agents.py](../../server/inkdesk_server/agents.py) |
| 前端形态 | Next.js 私有工作区，Ask / raw / ingest / wiki 页面 | [web/components/workbench/ask-workspace.tsx](../../web/components/workbench/ask-workspace.tsx)、[web/app/app/raw/page.tsx](../../web/app/app/raw/page.tsx)、[web/app/app/ingest/page.tsx](../../web/app/app/ingest/page.tsx) |
| 不建议包装 | 高并发系统、模型底层推理优化、大规模分布式存储、生产级对象存储平台 | 未发现 CUDA / Triton / RDMA / batching / KV cache / 多副本 / 分片 / 对象存储 SDK 等证据 |

## 2. 业务背景重建

### 2.1 代码明确可见的业务事实

- 私有单 owner 工作区：`users`、`workspaces`、owner session、私有路由保护。证据：[server/inkdesk_server/security.py](../../server/inkdesk_server/security.py)、[web/proxy.ts](../../web/proxy.ts)。
- raw 原始材料：支持 TEXT、WEB、PDF、legacy note，保存 `locator`、`excerpt`、`body`、`vault_path`、`content_hash`。证据：[server/inkdesk_server/models.py](../../server/inkdesk_server/models.py)、[server/inkdesk_server/importers.py](../../server/inkdesk_server/importers.py)。
- ingest 人工审阅队列：`review_items` 保存 AI 提案，支持 `TOPIC_CREATE` 和 `TOPIC_PATCH`，前端提供接受 / 忽略。证据：[server/inkdesk_server/research.py](../../server/inkdesk_server/research.py)、[web/app/app/ingest/page.tsx](../../web/app/app/ingest/page.tsx)。
- wiki 长期知识页：`topics`、`topic_claims`、`topic_sources`、`topic_thread_entries`，并写入 `wiki/*.md`。证据：[server/inkdesk_server/vault.py](../../server/inkdesk_server/vault.py)。
- ask 问答：`ask_turns` 记录问题、答案、引用、retrieval mode、知识缺口、follow-up、writeback 包。证据：[server/inkdesk_server/models.py](../../server/inkdesk_server/models.py)、[server/src/main/resources/db/migration/V8__ask_turn_snapshots.sql](../../server/src/main/resources/db/migration/V8__ask_turn_snapshots.sql)。
- RAG / 检索链路：`retrieval_chunks` 保存 chunk text、hash、embedding JSON；Ask 和 Compile 都调用 `RetrievalService` 选上下文。证据：[server/inkdesk_server/retrieval.py](../../server/inkdesk_server/retrieval.py)。
- LLM / Agent 链路：`AgentRuntime` 使用 LangGraph 构建 Ask graph 和 Compile graph，支持 OpenAI-compatible / DeepSeek 配置。证据：[server/inkdesk_server/agents.py](../../server/inkdesk_server/agents.py)、[server/inkdesk_server/core/config.py](../../server/inkdesk_server/core/config.py)。
- claim 治理：记录证据数量、provenance 状态、使用次数、最近验证、冲突和过期 claim。证据：[server/inkdesk_server/research.py](../../server/inkdesk_server/research.py)、[server/tests/test_research_api.py](../../server/tests/test_research_api.py)。

### 2.2 可强推导的业务诉求

| 业务诉求 | 为什么可以推导 | 简历可写性 |
| --- | --- | --- |
| 需要防止 AI 静默污染知识库 | README 和 vault `AGENTS.md` 都要求 AI 只能提案，不能直接改 wiki；代码通过 `review_items` accept 后才写 topic | 可写，适合 AI 应用治理亮点 |
| 需要保留来源和可追溯性 | Source、TopicClaim、ProposalEvidence、vault markdown 都保留 source / locator / vault path | 可写，适合 RAG / 知识库项目 |
| 需要检索增强问答 | Ask 前先 `select_for_ask`，Compile 前 `select_for_compile`，答案返回 citations | 可写，表述为应用层 RAG / 检索增强 |
| 需要处理低置信、知识缺口、外部补料 | `vault_plus_web`、knowledge gaps、web assist、writeback package | 可写，但不要写成 autonomous agent |
| 需要 claim 健康治理 | dashboard health 聚合 unsupported/stale/conflicting claim | 可写，适合工程治理和面试深挖 |
| 需要本地可运行与回归验证 | pytest、node:test、Vitest、Playwright、fullstack e2e | 可写，体现工程完整性 |

### 2.3 仍不确定的背景

- 不确定是否有真实线上用户、SLA、请求量、延迟指标或成本指标。
- 不确定是否经过生产级压测，不能写 QPS、延迟下降、召回率提升等数字。
- 不确定是否有多租户实际使用，当前代码更像单 owner workspace。
- 未发现真实 MQ、异步任务队列、死信、补偿或调度系统。
- 未发现模型推理框架、GPU、量化、算子、通信优化、Profiler / Benchmark。
- MinIO 出现在 docker-compose 和预检脚本，但主路径未发现对象存储 SDK 接入。

## 3. 代码事实总览

### 3.1 入口与 API

- FastAPI 入口：[server/inkdesk_server/main.py](../../server/inkdesk_server/main.py)，`create_app()` 注册健康检查、认证、raw、ingest、wiki、ask、writeback API。
- 关键接口：`/api/raw`、`/api/raw/web`、`/api/raw/pdf`、`/api/ingest/{id}/accept`、`/api/wiki/{id}`、`/api/ask`、`/api/ask/{id}/writeback`。
- 统一异常：`ApiError`、`ResourceNotFoundError`、`InvalidCredentialsError` 映射成 JSON 错误。

### 3.2 领域与数据模型

- `Source`：原始材料，包含类型、状态、标题、locator、正文、vault path、hash。
- `ReviewItem`：AI 生成的可审阅提案，包含目标 topic、proposal payload、状态和 hash。
- `Topic` / `TopicClaim`：wiki 页面与关键论点，包含证据状态、使用次数、最近验证。
- `RetrievalChunk`：检索 chunk，包含 entity、ordinal、text、hash、embedding JSON。
- `AskTurn`：问答快照，包含引用 wiki/source/chunk、知识缺口、web source、writeback package。

### 3.3 AI / RAG 链路

- Ask graph：`load_request_context -> retrieve_vault_context -> compose_answer -> assess_evidence -> optional_web_assist -> compose_answer_with_web -> build_writeback_package`。证据：[server/inkdesk_server/agents.py](../../server/inkdesk_server/agents.py)。
- Compile graph：`prepare_prompt -> generate_proposal`，把 raw 和检索上下文编译成 `TOPIC_CREATE` 或 `TOPIC_PATCH`。
- 检索：先同步 topic/source 到 chunk，再按 lexical score + embedding cosine score 排序；topic scoped ask 会优先当前 topic chunk。
- embedding：OpenAI-compatible embedding 可用时走 provider，不可用时使用 deterministic embedding fallback。
- 外部补料：`vault_plus_web` 且证据不足时触发 `WebRawImportService.assist_from_query`，但 writeback 仍要先生成 ingest 提案。

### 3.4 文件持久化与 provenance

- `VaultService` 初始化 `raw/`、`wiki/` 和 `AGENTS.md`。
- raw 导入写 `raw/*.md`，wiki 接受后写 `wiki/*.md`。
- 路径有根目录逃逸保护，写文件使用临时文件替换。
- markdown frontmatter 保存 source/topic metadata，wiki claim 链接回 raw source。

### 3.5 前端工作台

- `/app` 和 `/app/ask` 是 ask-first 工作区，支持问题、topic scope、vault/vault_plus_web 模式、继续追问和 writeback。
- `/app/raw` 支持网页、文本、PDF 导入。
- `/app/ingest` 展示 AI 编译提案并通过 server action 接受或忽略。
- `/app/wiki/[id]` 展示 Current Understanding、Open Questions、Sources、Key Claims、Research Thread。
- `web/lib/research.ts` 对后端 API 做封装，并在无 API base URL 时回退本地 fixture，利于前端开发和测试。

### 3.6 测试与工程化

- 后端 pytest 覆盖认证、健康检查、schema upgrade、agent runtime、research API、vault service、pgvector health。
- 前端 node:test / Vitest 覆盖 owner session、API helper、页面渲染、组件和 fullstack preflight。
- Playwright e2e 覆盖登录、ingest accept、wiki、ask follow-up、writeback、raw 页面和退出保护。
- README 提供本地启动、Docker infra、后端 pytest、前端 test/typecheck/lint/build 命令。

## 4. TOP 15 项目亮点

| # | 亮点 | 级别 | 状态 | 证据 | 简历建议 |
| --- | --- | --- | --- | --- | --- |
| 1 | 设计并实现 raw -> ingest -> wiki -> ask 的 AI 知识沉淀闭环 | S | 已实现 | README、main.py、research.py | 主打 |
| 2 | 使用 LangGraph 编排 Ask / Compile 两条 LLM 工作流 | S | 已实现 | agents.py | 主打 AI 应用 |
| 3 | 实现带引用的 RAG 检索增强问答，支持 topic scoped 和 global ask | S | 已实现 | retrieval.py、research.py | 主打 RAG |
| 4 | 引入人工审阅闸门，AI 只生成提案，接受后才写 wiki | S | 已实现 | review_items、accept_review、ingest page | 主打可信 AI |
| 5 | 建立 Source / Topic / Claim / AskTurn 的领域模型和 provenance 链路 | S | 已实现 | models.py、database-schema.md | 主打平台建模 |
| 6 | Vault-first Markdown 持久化，数据库只做索引与状态层 | A | 已实现 | vault.py、README | 主打工程设计 |
| 7 | Ask writeback 将高价值回答转成 ingest 提案而非直接改写知识库 | A | 已实现 | create_ask_writeback_proposal、tests | 主打闭环 |
| 8 | Claim 治理：unsupported / stale / conflicting claim 识别和重审提案 | A | 已实现 | build_dashboard_health、ensure_claim_review、ensure_conflict_review | 面试深挖 |
| 9 | embedding provider 可配置，支持 hybrid 和 lexical fallback | A | 已实现 | embeddings.py、config.py | 谨慎写 |
| 10 | Web/PDF/Text 多来源导入，网页抓取和 PDF 文本抽取接入 raw | A | 已实现 | importers.py、raw page | 可写 |
| 11 | 私有 owner 登录与 session 签名校验，保护 `/app` 私有路由 | A | 已实现 | security.py、proxy.ts | 可写 |
| 12 | 前端 ask-first 工作台整合 briefing、问题、引用、追问、writeback | A | 已实现 | ask-workspace.tsx | 可写全栈 |
| 13 | schema upgrade 与迁移 SQL 并存，支持旧表升级到当前 ask/claim 模型 | B+ | 已实现 | db.py、migration SQL | 面试延展 |
| 14 | fullstack e2e 覆盖从登录到 ingest/wiki/ask/writeback 的主流程 | B+ | 已实现 | local-fullstack.spec.ts | 可写工程实践 |
| 15 | Docker Compose 提供 pgvector PostgreSQL、MinIO、server 基础设施 | B | 部分主路径 | docker-compose.yml | 谨慎写，只写本地基础设施 |

## 5. 最适合写进简历的 8 条

1. 参与实现 vault-first 私有研究记忆系统，围绕 `raw -> ingest -> wiki -> ask` 搭建原始材料导入、AI 提案审阅、知识页沉淀和带引用问答的核心闭环。
2. 基于 FastAPI + SQLAlchemy 设计 Source、ReviewItem、Topic、TopicClaim、AskTurn、RetrievalChunk 等核心模型，支撑来源追溯、提案状态流转、知识页索引和问答上下文记录。
3. 参与实现 LangGraph 驱动的 Ask / Compile 工作流，将检索上下文、结构化 LLM 输出、知识缺口判断和 writeback package 串联成可审阅的 AI 应用链路。
4. 实现应用层 RAG 检索链路，对 wiki/topic 与 raw/source 生成 chunk 索引，结合 lexical fallback 与 embedding 相似度为 Ask 和 Compile 提供引用上下文。
5. 设计 AI 写入安全边界：LLM 只能生成 `TOPIC_CREATE` / `TOPIC_PATCH` 提案，必须经过 ingest 人工接受后才会更新 wiki Markdown 和数据库索引。
6. 实现 vault Markdown 持久化机制，将 raw 与 wiki 分别写入文件，并保存 `vault_path`、`content_hash` 和 source backlink，保证数据库索引之外仍可恢复知识内容。
7. 构建 claim 级知识治理能力，记录 claim 的证据数量、provenance 状态、使用次数和最近验证时间，并对缺证、过期、冲突 claim 生成健康信号或重审提案。
8. 补齐前后端回归验证，使用 pytest、node:test、Vitest 和 Playwright 覆盖认证、导入、审阅、问答、writeback 和私有路由保护等主流程。

## 6. 最适合面试展开的 8 条

1. 为什么要让 AI 先进入 ingest，而不是直接写 wiki？
2. Ask 链路如何选择 topic / source / chunk 作为上下文？
3. embedding provider 不可用时，为什么要做 lexical / deterministic fallback？
4. Ask writeback 如何避免把模型答案直接污染长期知识库？
5. Vault Markdown 与数据库索引分别承担什么职责？一致性怎么处理？
6. claim 的 unsupported / stale / conflicting 是怎么识别并转成工作台信号的？
7. 前端如何把 Server Action、revalidatePath 和后端 API 串成审阅体验？
8. 当前系统如果要做生产化，需要补哪些观测、异步、评测和权限能力？

## 7. 定向 6 条核心亮点

### 7.1 校招生 / 初级程序员通用版

1. 完成私有研究知识库的核心业务闭环，实现 raw 导入、AI 提案、人工审阅、wiki 沉淀、Ask 问答和 writeback。
2. 基于 FastAPI / Next.js 实现前后端分层，封装后端 API helper 与页面 Server Action，覆盖主要页面和接口。
3. 使用 SQLAlchemy 建模核心数据对象，并通过迁移 SQL / schema upgrade 维护数据结构演进。
4. 实现文件持久化、路径安全和内容 hash，理解数据库索引层与文件真相层的取舍。
5. 补充端到端测试和单元测试，验证登录、导入、审阅、问答、wiki 和退出保护流程。
6. 对 AI 输出设置人工审阅边界，体现基础工程风险意识。

### 7.2 AI 应用开发初级版

1. 使用 LangGraph 编排 Ask 和 Compile 工作流，实现检索上下文加载、LLM 结构化输出、证据判断和 writeback package。
2. 实现 vault-only / vault-plus-web 两种问答模式，证据不足时可显式联网补料，但外部证据仍通过 raw / ingest 审阅沉淀。
3. 设计 Compile 提案结构，将模型输出归一化为 topic decision、summary changes、claims、conflicts、open questions 和 evidence。
4. 支持 OpenAI-compatible / DeepSeek profile、结构化输出模式、超时配置和 deterministic fallback。
5. 记录 AskTurn 的引用、知识缺口、follow-up、web source 和上下文链，便于追问和审计。
6. 通过 pytest 覆盖模型调用失败 fallback、结构化输出归一化、web assist 和 writeback 行为。

### 7.3 Agent / RAG / Workflow 应用开发初级版

1. 实现 Ask LangGraph 节点和条件路由，支持证据评估后决定直接回答或触发 web assist。
2. 实现 Compile 工作流，把 raw source 与检索上下文编译成 create / patch 提案。
3. 构建 chunk 级检索索引，支持 Ask 和 Compile 复用同一套上下文选择服务。
4. 支持 topic scoped ask、global ask、follow-up lineage，并阻止跨 topic 上下文串用。
5. 通过 citations、usedChunkIds、usedSourceIds 让回答可追溯。
6. 通过 writeback 将问答结果转回可审阅 workflow，而不是自动执行长期知识修改。

### 7.4 平台开发初级版

1. 搭建私有研究工作台，包含 raw、ingest、wiki、ask 四个核心页面和统一 app shell。
2. 通过 ReviewItem 状态机式字段管理提案的 pending / accepted / rejected 流转。
3. 设计 dashboard health 聚合 raw backlog、review backlog、open questions、claim 风险和 writeback candidate。
4. 在前端封装 API client 和 fallback fixture，提高本地开发可用性。
5. 使用 owner session cookie 和 Next proxy 保护 `/app` 私有路由。
6. 提供 Docker Compose、本地预检、fullstack e2e 等交付辅助。

### 7.5 分布式 / 存储开发初级版

只能保守表达：

1. 参与数据存储与检索索引设计，使用 PostgreSQL 保存工作流状态和检索 chunk。
2. 实现 vault Markdown 文件持久化与数据库索引联动，保存 `vault_path` 和 `content_hash`。
3. 对 Source / Topic / Claim 设计索引和外键关系，支持来源追溯和知识页关联。
4. 接入 pgvector 镜像和 vector 扩展健康检查，但当前向量计算主要在应用层完成。
5. 未发现分片、副本、一致性协议或对象存储主链路，不建议写成分布式存储系统。
6. 如投存储方向，应把项目定位为“存储/检索基础实践”，不是“大规模存储架构”。

### 7.6 AI 应用性能 / 工程优化初级版

当前只能写应用层优化，不能写模型底层性能优化：

1. LLM 调用设置连接 / 读取超时，provider 失败时 fallback 到确定性逻辑。
2. embedding provider 失败时 fallback 到 deterministic embedding，避免检索链路完全不可用。
3. retrieval chunk 使用 content hash 做增量同步，重复 ask 不重复创建 chunk。
4. 前端 API 使用 `cache: no-store`，避免研究问答和审阅状态被错误缓存。
5. 未发现 batching、KV cache、量化、CUDA、Profiler、Benchmark，不建议主打 AI 性能优化岗位。
6. 可作为后续补齐方向：RAG Eval、检索缓存、LLM 调用观测、成本统计和压测。

## 8. 核心亮点专项文档

### 亮点 1：Vault-first AI 知识沉淀闭环

**代码事实**

- README 明确主循环为 `raw -> ingest -> wiki -> ask`。
- FastAPI 提供 raw、ingest、wiki、ask、writeback 接口。
- `ResearchWorkspaceService.create_imported_source()` 导入 raw 后调用 `ensure_review_for_source()` 生成提案。
- `accept_review()` 接受提案后创建或更新 Topic，并写入 wiki。
- `create_ask_writeback_proposal()` 将 AskTurn 转成新的 ReviewItem。

**解决的问题**

普通 RAG 问答容易只停留在“查资料并回答”。这个项目多了一层知识沉淀闭环：原始资料不直接变成长期知识，AI 只生成建议，人审后才进入 wiki，问答结果也可以再次回流审阅。

**可写表述**

- 克制专业版：参与实现私有研究记忆系统核心闭环，围绕 raw 导入、AI ingest 提案、人审 wiki 写入和 ask 问答构建可追溯的知识沉淀流程。
- 技术实现版：基于 FastAPI / SQLAlchemy 实现 Source、ReviewItem、Topic、AskTurn 的状态流转，串联 raw 导入、提案生成、人工接受、wiki 持久化和 Ask writeback。
- AI 应用版：参与构建 LLM 辅助知识编译链路，限制模型只能输出可审阅提案，避免直接污染长期知识库。

**三层追问**

- 你做了什么：实现 raw、ingest、wiki、ask 之间的数据流和接口，确保材料、提案、知识页、问答记录互相可追溯。
- 为什么这么设计：因为研究知识库需要可信沉淀，AI 输出不一定稳定，必须有人工确认闸门。
- 扩大后怎么处理：需要引入异步任务队列、提案状态机、审计日志、冲突处理和批量导入任务。

**风险边界**

- 不能说：主导全链路 AI 平台架构、支撑大规模用户。
- 可以说：参与核心链路实现、模块设计与落地。
- 需要补充后才能说：线上稳定性、性能指标、多用户协作。

### 亮点 2：LangGraph Ask / Compile 工作流

**代码事实**

- `AgentRuntime._build_ask_graph()` 构建 Ask graph。
- `AgentRuntime._build_compile_graph()` 构建 Compile graph。
- `with_structured_output()` 使用 Pydantic schema 约束 LLM 输出。
- provider 不可用时回退 `_deterministic_ask()` / `_deterministic_compile()`。

**解决的问题**

把 LLM 调用从单次 prompt 调用升级成可解释的应用工作流：先加载上下文，再检索 vault，再生成答案，再判断是否需要 web assist，最后生成 writeback package。

**可写表述**

- 参与实现基于 LangGraph 的 Ask / Compile 工作流，支持结构化 LLM 输出、证据判断、显式联网补料和降级 fallback。

**三层追问**

- 做了什么：定义 AskState / CompileState，拆分节点和条件路由。
- 为什么这么设计：节点化后更容易测试、fallback 和扩展。
- 扩大后怎么处理：需要节点级日志、超时、重试、trace、成本统计和 eval。

**风险边界**

- 不能说：多智能体协同、自治 Agent 执行平台。
- 可以说：LangGraph 工作流编排、Tool/Web assist 的受控分支。

### 亮点 3：应用层 RAG 检索增强

**代码事实**

- `RetrievalService.select_for_ask()` 和 `select_for_compile()` 选择上下文。
- `_sync_chunks()` 根据 content hash 增量维护 chunk。
- `_rank_chunks()` 结合 lexical score、embedding cosine 和 topic boost 排序。
- `EmbeddingService.retrieval_mode` 在 hybrid 与 lexical_fallback 之间切换。

**解决的问题**

Ask 和 Compile 都不能只靠模型记忆，需要从当前 vault 中找到相关 topic/source 作为证据，并把 citation 返给用户。

**可写表述**

- 实现 wiki/source 的 chunk 级检索索引，结合关键词匹配和 embedding 相似度为问答和提案生成提供引用上下文。

**三层追问**

- 做了什么：同步 topic/source 文本为 chunk，提问时构建 query，排序后返回 citations。
- 为什么这么设计：chunk 化便于局部引用，fallback 保证无 embedding key 时仍可运行。
- 扩大后怎么处理：需要 pgvector 字段、ANN 索引、rerank、召回评测、缓存和离线建索引。

**风险边界**

- 不能说：向量数据库性能优化、生产级 RAG 召回率提升。
- 可以说：应用层 RAG、hybrid retrieval 雏形、fallback 设计。

### 亮点 4：AI 写入安全与人工审阅

**代码事实**

- `ReviewItem` 保存 proposal payload。
- `accept_review()` / `reject_review()` 控制是否写入 wiki。
- `VaultMarkdownService.render_wiki_topic()` 只在接受后生成 wiki markdown。
- 前端 `/app/ingest` 明确接受写入 / 忽略提案。

**解决的问题**

AI 编译结果可能不准确，系统通过 ingest 队列让 owner 决策，保证长期知识不是模型自动改写。

**可写表述**

- 设计 AI 输出的人审闸门，将模型生成的创建 / 补丁建议统一落到 ReviewItem，接受后才更新 Topic 和 wiki 文件。

**三层追问**

- 做了什么：ReviewItem 存储建议，accept 改 Topic，reject 只变状态。
- 为什么这么设计：把生成和写入解耦，降低幻觉污染长期知识的风险。
- 扩大后怎么处理：需要审批人、审计、diff 展示、版本回滚、批量处理。

### 亮点 5：Claim 级知识治理

**代码事实**

- `TopicClaim` 包含 `evidence_count`、`provenance_status`、`usage_count`、`last_verified_at`。
- `build_dashboard_health()` 生成 unsupported/stale/conflicting 信号。
- `ensure_claim_review_for_topic()` 和 `ensure_conflict_review_for_topic()` 生成重审提案。
- 测试覆盖缺证、过期、冲突 claim 的展示和 materialize。

**解决的问题**

知识库会老化，也会出现证据不足或互相冲突的判断。claim 级治理让系统能提示哪些知识需要复核。

**可写表述**

- 实现 claim 级知识健康治理，记录证据状态和使用情况，对缺证、过期、冲突 claim 生成工作台健康信号和重审提案。

**三层追问**

- 做了什么：统计 claim 状态，聚合到 dashboard 和 briefing。
- 为什么这么设计：RAG 的问题不只是能不能检索，还包括检索到的知识是否可信、是否过期。
- 扩大后怎么处理：需要更严格的证据打分、来源时效、人工标注、eval 数据集。

## 9. 系统优化专项文档

### 9.1 优化点总览

| 优化方向 | 当前状态 | 证据强度 | 简历可写性 | 面试价值 | 推荐级别 |
| --- | --- | --- | --- | --- | --- |
| LLM 超时配置 | 已实现 | 强 | 可写应用层稳定性 | 中 | A |
| LLM / embedding fallback | 已实现 | 强 | 可写 | 高 | A |
| chunk content hash 增量同步 | 已实现 | 强 | 可写 | 高 | A |
| 人审闸门防污染 | 已实现 | 强 | 可写 | 高 | S |
| claim 健康治理 | 已实现 | 强 | 可写 | 高 | A |
| 路径逃逸保护和临时文件替换 | 已实现 | 强 | 可写 | 中 | A |
| RAG Eval | 未实现 | 无 | 不写，作为补齐 | 高 | S |
| 检索缓存 / 请求折叠 | 未实现 | 无 | 不写 | 中 | A |
| 异步导入 / embedding job | 未实现 | 无 | 不写 | 高 | A |
| LLM 调用成本统计 | 未实现 | 无 | 不写 | 中 | A |
| MQ / 死信 / 补偿 | 未实现 | 无 | 不写 | 中 | B |
| 模型底层推理优化 | 未实现 | 无 | 禁止写 | 低 | 不推荐 |

### 9.2 已实现优化点

**LLM 调用超时与 fallback**

- 证据：`Settings.agent_connect_timeout_seconds`、`agent_read_timeout_seconds`；`AgentRuntime` 传给 `ChatOpenAI`；provider invoke 失败时 fallback 到 deterministic answer / compile / briefing。
- 简历表述：围绕 LLM 调用稳定性，增加超时配置和降级 fallback，保证无模型凭证或 provider 异常时主流程仍可演示和测试。
- 风险：不能说熔断、限流、成本治理已完成。

**检索 chunk 增量同步**

- 证据：`RetrievalService._sync_chunks()` 通过 content hash 判断 chunk 是否变化，删除多余 stale chunk。
- 简历表述：为 wiki/source 构建 chunk 级索引，并通过内容 hash 避免重复创建检索块，保障重复问答时索引稳定。
- 风险：不能写 ANN 索引优化或 pgvector 向量检索性能优化。

**文件写入安全**

- 证据：`VaultService.resolve()` 校验路径不能逃出 vault root；`write_vault_file()` 先写临时文件再 replace。
- 简历表述：实现 vault 文件读写封装，加入相对路径校验、hash 记录和临时文件替换，降低文件持久化风险。

### 9.3 当前有迹象但只能克制表达

**pgvector 基础设施**

- 证据：docker-compose 使用 `pgvector/pgvector:pg16`；`db.py` 创建 vector extension；`test_pgvector_integration.py` 覆盖 health。
- 克制表达：接入 pgvector PostgreSQL 镜像和健康检查，为后续向量检索迁移预留基础。
- 禁止表达：完成 pgvector ANN 检索优化、向量数据库性能治理。

**MinIO 基础设施**

- 证据：docker-compose 和 preflight 检查 MinIO。
- 克制表达：本地基础设施预留 MinIO，用于后续对象存储接入。
- 禁止表达：已实现对象存储上传、生命周期管理、大文件存储优化。

### 9.4 当前未实现，仅作为后续优化方案

1. RAG Eval 评测体系：为 Ask / Compile 建立问题集、期望 citation、答案质量标注和回归测试。
2. Prompt 模板版本管理：把 Ask / Compile / Briefing prompt 拆成版本化模板，记录每次 AskTurn 使用的 prompt 版本。
3. Tool / Web Assist 权限审计：记录外部搜索 query、URL、抓取耗时、失败原因和是否进入 raw。
4. Workflow 节点级状态与恢复：持久化 LangGraph 节点输入输出，支持失败重试和排查。
5. LLM 调用观测：记录模型、token、耗时、错误码、fallback 原因和成本估算。
6. 检索缓存与请求折叠：对相同 query/topic 的短时间重复检索做缓存或 singleflight。
7. 文档解析 / embedding 异步化：把网页/PDF 解析、chunk、embedding 从同步请求改为后台 job。
8. 多租户与权限隔离：当前是单 owner，应增加 workspace 级权限校验和审计。
9. 性能 benchmark：补充导入、检索、Ask、Compile 的本地压测脚本。
10. pgvector 真实向量检索：将 `embedding_json` 迁移为 vector 字段，建立 ANN 索引和召回评测。

## 10. JD 匹配分析

### 10.1 AI 应用开发工程师

- 已匹配：LLM 应用链路、LangGraph 编排、结构化输出、RAG 检索、web assist、人工审阅、fallback。
- 部分匹配：Eval、Prompt 版本、成本控制、可观测性有基础但不完整。
- 未发现证据：生产级监控、模型效果指标、线上 A/B、token 成本统计。
- 建议主打：AI 应用后端 + RAG + 可信知识沉淀。
- 面试风险：不要把调用 OpenAI-compatible API 说成模型训练或推理优化。

### 10.2 Agent / RAG / Workflow

- 已匹配：LangGraph 节点编排、条件路由、RAG citations、Ask follow-up、writeback workflow。
- 部分匹配：web assist 可算受控工具调用，但不是复杂多工具 Agent。
- 未发现证据：多智能体协作、长期自治任务、工具权限系统、节点级恢复。
- 建议主打：受控 Agentic Workflow，而不是 autonomous agent。

### 10.3 平台开发工程师

- 已匹配：私有工作台、核心页面、API helper、server actions、状态聚合、review queue。
- 部分匹配：本地部署和 fullstack e2e 有基础。
- 未发现证据：多团队配置平台、复杂权限、灰度、审计后台。
- 建议主打：AI 研究工作台 / 知识库平台。

### 10.4 分布式 / 存储开发工程师

- 已匹配：PostgreSQL 建模、索引、vault 文件持久化、检索 chunk、content hash。
- 部分匹配：pgvector 基础设施、MinIO 本地服务。
- 未发现证据：分片、副本、一致性协议、对象存储主链路、存储生命周期、缓存层。
- 是否建议主打：不建议作为主方向；可作为“存储与检索基础实践”辅助项目。

### 10.5 AI 应用性能 / 工程优化工程师

- 已匹配：应用层超时、fallback、chunk 增量同步。
- 部分匹配：未配置真实指标，只能讲设计意识。
- 未发现证据：量化、稀疏化、CUDA、Triton、RDMA、batching、KV cache、Profiler、Benchmark。
- 是否建议主打：不建议。当前项目不建议主打 AI 性能优化校招 / 初级开发岗位。

## 11. 简历风险审查

### 11.1 高风险表述

| 高风险表述 | 风险原因 | 推荐替代表述 |
| --- | --- | --- |
| 主导大模型知识库平台架构 | 无团队和主导证据 | 参与核心模块设计与实现 |
| 实现高性能 RAG 引擎 | 无召回率、延迟、吞吐指标 | 实现应用层 RAG 检索链路 |
| 基于 pgvector 完成向量数据库优化 | 当前 embedding 存 JSON，排序在应用层 | 接入 pgvector 基础设施和检索健康检查 |
| 实现 AI 推理优化 | 只是 API 调用和应用层 fallback | 实现 LLM 调用链路稳定性处理 |
| 支撑高并发问答 | 无压测和线上规模 | 支持本地全链路问答和回归测试 |
| 对象存储系统 | MinIO 未进入主路径 | 预留 MinIO 本地基础设施 |
| 多智能体协作平台 | 未发现多个 agent 的协作协议 | LangGraph 驱动的受控 AI 工作流 |
| 从 0 到 1 搭建完整平台 | 主导度不明 | 参与搭建核心业务闭环 |

### 11.2 容易被追问露馅的点

| 技术点 | 面试官会怎么问 | 容易暴露的问题 | 防守方式 |
| --- | --- | --- | --- |
| RAG | embedding 存在哪里？怎么检索？ | 误说 pgvector ANN | 如实说当前 `embedding_json` + 应用层排序，pgvector 是基础设施预留 |
| LangGraph | 有哪些节点？条件路由是什么？ | 只会说用了 LangGraph | 讲 Ask graph 和 web assist 分支 |
| AI 写入 | 如何防止模型直接改 wiki？ | 说不清 ReviewItem | 讲 ingest accept/reject 和 vault 写入时机 |
| Claim 治理 | stale/conflict 怎么判断？ | 说不清规则 | 讲 usage_count、last_verified_at、provenance_status 和简单否定冲突规则 |
| 存储 | DB 和 Markdown 谁是真相？ | 混淆职责 | 讲 vault 是长期真相，DB 是索引和状态 |
| 性能 | 有没有指标？ | 编造数据 | 说没有压测数据，只能讲已做的 fallback 和增量同步 |

### 11.3 主导度边界

| 亮点 | 推荐主导度 | 禁止表述 |
| --- | --- | --- |
| raw/ingest/wiki/ask | 参与核心链路实现 | 主导全局架构 |
| LangGraph | 参与工作流编排与节点实现 | 主导多智能体平台 |
| RAG | 实现应用层检索增强 | 研发高性能向量检索引擎 |
| Vault | 实现文件持久化封装 | 设计分布式存储系统 |
| 测试 | 补充主流程回归测试 | 建立完整 CI/CD 质量平台 |

## 12. 1 分钟项目介绍

### 12.1 克制专业版

Inkdesk 是一个单人私有的研究记忆系统，核心流程是 raw -> ingest -> wiki -> ask。用户可以把网页、PDF 或旧笔记导入 raw，系统通过检索和 LLM 生成可审阅的 ingest 提案，人工接受后才会写入 wiki。Ask 问答优先基于已沉淀的 wiki 和 raw 生成带引用回答，稳定结论也可以再转成 writeback 提案。我主要围绕后端领域模型、AI 工作流、检索链路、vault 文件持久化和前端工作台做实现与测试。

### 12.2 技术实现版

这个项目用 Next.js + FastAPI + PostgreSQL + LangGraph 实现。后端建模了 Source、ReviewItem、Topic、TopicClaim、AskTurn 和 RetrievalChunk，支持 raw 导入、AI compile 提案、人审写入 wiki 和 Ask 检索增强问答。AI 链路用 LangGraph 拆成 Ask 和 Compile 两条 workflow，并用结构化输出、fallback 和 citations 保证结果可控。前端提供 Ask、raw、ingest、wiki 页面，并用 pytest、node:test、Vitest、Playwright 覆盖主流程。

### 12.3 业务结果版

这个项目解决的是个人研究资料容易散、AI 回答难沉淀、知识来源不可追溯的问题。系统把原始材料先保存到 raw，再让 AI 生成可审阅提案，只有人工确认后才进入长期 wiki。之后 Ask 可以基于这些可信知识回答，并保留引用、知识缺口和后续问题。这样既利用了 LLM 的整理能力，又避免模型直接改写长期知识。

### 12.4 AI 应用开发初级版

我参与实现了一个 LLM 驱动的私有研究知识库。核心是 LangGraph 编排的 Ask / Compile 工作流：Compile 把 raw 材料和检索上下文转成 topic 创建或补丁提案，Ask 基于 wiki/raw 检索结果生成带引用回答；证据不足时可以显式联网补料，但最终仍要经过 ingest 审阅才能写回 wiki。项目重点体现 RAG、结构化输出、fallback、writeback 和 AI 写入边界。

### 12.5 平台 / 分布式开发初级版

Inkdesk 是一个私有研究工作台，前端有 raw、ingest、wiki、ask 四个工作区，后端用 PostgreSQL 管理工作流状态和检索索引，用 vault Markdown 保存长期知识。系统设计了来源、提案、知识页、claim 和问答快照等模型，并通过文件 hash、路径校验、索引表和 e2e 测试保证主流程可运行。它更适合作为平台工程和数据检索基础项目来讲。

当前项目不适合用 1 分钟介绍主打 AI 性能优化。

## 13. 5 分钟深挖版本

项目背景上，Inkdesk 不是普通笔记应用，而是一个私有研究记忆系统。它希望解决三个问题：原始材料需要可追溯，AI 整理结果不能直接污染长期知识，问答后的稳定结论要能沉淀回知识库。

系统定位是 vault-first。长期真相在 `raw/` 和 `wiki/` Markdown 里，数据库负责索引、提案队列、检索 chunk 和问答快照。主链路是：用户导入网页、PDF 或文本，后端生成 Source 并写 raw 文件；系统基于检索上下文和 LLM 生成 ReviewItem；用户在 ingest 页面接受后，后端创建或更新 Topic、TopicClaim、TopicThreadEntry，并写 wiki Markdown；Ask 再基于 wiki 和 raw 检索结果生成带引用回答。

我参与的模块主要包括后端领域模型、ResearchWorkspaceService 主流程、LangGraph AgentRuntime、RetrievalService、VaultService，以及前端 Ask/raw/ingest/wiki 页面和测试。技术难点有三个：第一是 AI 写入边界，模型输出必须先落 ReviewItem；第二是 RAG 上下文选择，需要同步 topic/source chunk 并保留 citation；第三是知识健康治理，需要识别 unsupported、stale 和 conflicting claim，避免长期知识变旧或互相矛盾。

设计取舍上，项目当前选择应用层 chunk 和 fallback 检索，而不是直接上复杂向量数据库优化，原因是项目处于私有单 owner 阶段，优先保证可运行、可测试和无模型 key 时可演示。另一个取舍是 vault Markdown 作为长期真相，数据库只做索引和状态，这样牺牲了一些一致性复杂度，但换来了知识内容可迁移、可恢复和可人工阅读。

如果继续演进，我会优先补 RAG Eval、Prompt 版本管理、LLM 调用观测、检索缓存、异步 embedding job 和多租户权限。对于 AI 性能优化或分布式存储方向，目前代码证据不足，只能作为后续扩展，不会在简历里写成已完成。

## 14. 当前最值得补齐的 10 条

1. RAG Eval：在 `server/tests` 增加固定问题、期望 citation、答案结构断言；补完可写“建立 RAG 回归评测”。
2. Prompt 版本管理：在 `agents.py` 拆出模板版本，AskTurn 保存 prompt version；补完可写“Prompt 版本与回溯”。
3. LLM 调用观测：记录 provider、model、耗时、错误、fallback 原因；补完可写“LLM 调用治理”。
4. 检索缓存：对同 topic / query 的短期重复检索缓存；补完可写“降低重复检索开销”。
5. 异步导入和 embedding：将 PDF / web 解析、chunk、embedding 改为 job；补完可写“导入链路异步化”。
6. pgvector 真正落地：新增 vector 字段和 ANN 查询；补完可写“向量检索链路优化”，但仍需评测数据。
7. Tool/Web Assist 审计：记录外部搜索和抓取日志；补完可写“外部工具调用治理”。
8. Review diff 与版本回滚：wiki 更新前展示差异，保存历史版本；补完可写“知识库变更治理”。
9. Workspace 权限隔离：当前单 owner，补 workspace 检查和审计；补完可写“数据权限隔离”。
10. 性能 benchmark：覆盖 import、ask、compile、retrieval；补完后才能写任何延迟或吞吐数据。

## 15. 最终推荐

最值得打的 3 张牌：

1. AI 可信知识沉淀闭环：raw -> ingest -> wiki -> ask -> writeback。
2. LangGraph + RAG 的应用层实现：结构化输出、citations、fallback、web assist。
3. Claim / provenance 治理：证据状态、使用记录、过期和冲突重审。

最不该硬吹的 3 个点：

1. 模型底层推理性能优化。
2. 大规模分布式存储或对象存储平台。
3. 生产级高并发、高可用或明确性能收益。

如果只能选 3 条写进简历：

1. 参与实现 vault-first AI 研究记忆系统，完成 raw 导入、ingest 人审提案、wiki 知识沉淀和 Ask 带引用问答闭环。
2. 基于 LangGraph + FastAPI 实现 Ask / Compile 工作流，结合检索上下文、结构化 LLM 输出、web assist 和 fallback 机制，保证 AI 链路可控可追溯。
3. 设计 Source / Topic / Claim / AskTurn 等领域模型和 vault Markdown 持久化，支持 provenance 追踪、claim 健康治理和问答 writeback。

如果只能选 1 条作为项目主讲点：

- 讲“AI 不直接写长期知识，而是通过 raw -> ingest -> wiki -> ask 的人审闭环沉淀可信知识”。这个点最能体现业务理解、AI 应用架构、RAG、工程边界和风险意识。
