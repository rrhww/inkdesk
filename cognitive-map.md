# 认知地图

> 不记录「有什么功能」，记录「你对代码的理解深度」。诚实比完整重要——写「我不知道为什么这样写」比留空有用。

## 已理解（能给别人讲清楚）

### 统一后的运行架构（2026-08-13 仓库统一）

- 主线 = 纯文件图谱架构（origin/main 收敛结果）+ K1-K3 知识健康与任务工作流（原 codex 分支 50ca959 移植）+ K0 方向文档。PostgreSQL/CRUD/Dev Run Console 已不在运行链路。
- `main.py` 的 `create_app()` 组合五个运行时：
  - `GraphIndexRuntime`：扫描 Vault wiki + repo Markdown → `GraphSnapshot`（version/generatedAt/nodes/edges），快照落 `.inkdesk/graph/snapshot.json`；Watchdog + debounce refresh；事件经 `events.publish_runtime` 进 SSE
  - `KnowledgeService(graph_runtime)`：纯内存只读视图，叠在 snapshot 上，产出 topics/search/briefing/sources/document
  - `KnowledgeHealthRuntime(graph_runtime)`：claims/evidence/signals/reviews，**stdlib sqlite3 WAL 本地投影**（`INKDESK_DATABASE_PATH` 或 `server/.data/inkdesk.sqlite`）
  - `TaskRuntime(task_graph_snapshot, on_change)`：development_tasks 表（同样 sqlite3），创建后 `threading.Timer(0.05)` 异步装配上下文；`TaskEventBus` 桥接 asyncio loop（lifespan 首行 `attach_loop`）→ `/api/tasks/stream`
  - `EngineRuntime` + `TechSolutionRuntime` + `HarnessAuditRuntime`：内存 Kahn/BFS DAG、tech-solution skill 流、harness 审计（JSONL 事件、五维评分、权限决策、Claude 只读 executor）
- SSE 契约三条并存，事件名互不冲突：`graph.snapshot`/`graph.updated`（/api/graph/stream）、`knowledge.updated`（/api/knowledge/stream）、`tasks.updated`（/api/tasks/stream）；心跳统一 `graph_sse_heartbeat_seconds`
- `engine.py` 的 `WorkflowScheduler` 在 SSE 边界把 `stage.*/workflow.*` 改名为 `task.*/dag.*`——对外事件契约与旧版 KahnDagScheduler 一致，所以 K1-K3 移植时 engine 零改动
- `conftest.py` 必须注入 `INKDESK_DATABASE_PATH`：create_app 无条件构造两个 sqlite 运行时，不隔离会污染 `server/.data/`
- Web：`@xyflow/react` v12 全量替换 reactflow v11（仅 5 个组件/lib + 1 个测试 mock 涉及）；`server-api.ts` 统一走 `resolveApiBaseUrl()`（浏览器内 `/api` 同源，Next 代理 8080），K1-K3 的 `API_BASE` 8000 硬编码已消除
- 路由：`/app/wiki` 知识看板（主入口）→ `/app/wiki/[id]` 简报 → `/app/wiki/graph` 图谱（辅助）→ `/app/tasks` 任务收件箱 → `/app/health` 信号处置 → `/app/runs/[runId]` 只读检查器

### 移植接缝的教训（674db02 坏 merge）

- 坏 merge 把 27 个文件、261 处冲突标记直接提交并推送。根源：两侧是不同架构（DB 时代 vs 纯文件图谱），不是行级冲突。
- 正确做法不是「修 merge」，而是「以一侧为底做功能移植」：全新/独有文件 `git checkout <src> -- <path>` 整体搬入，接缝文件以底版为基础手工重接（路由注册、模型追加、配置不动），每步用测试守住。
- 移植判断的关键证据：`graph_index.py` 的公共 API（`refresh/current/scanner.read_document/version=="empty"`）两侧一致，才能让 knowledge.py 零修改依赖它；`WorkflowScheduler` 的兼容改名同理。

## 模糊区

- `knowledge.py` 的 topic 提取与简报生成算法细节（基于 snapshot 的哪些字段、置信度怎么算）——本次只验证了 API 契约，没逐行读实现
- `knowledge_health.py` / `tasks.py` 的 sqlite 表结构与并发语义（WAL + IF NOT EXISTS 已知，事务边界未细看）
- harness 的 Claude executor 实际运行路径（宿主机 safe mode + PreToolUse Policy）——只读过 README 描述，未跑过真实 executor
- e2e 全链路（`npm run e2e` 与 `e2e:fullstack`）在统一后尚未实跑（需要起本地服务）

## 黑盒区（完全不懂）

- `tech_solution.py` 与 harness 的 LLM provider 链路（deterministic 之外的模式）
- xyflow v12 的运行时差异（已做 import/泛型级迁移，但画布交互的深层行为未验证）

## 历史记录（不在主线，供追溯）

- DB 时代架构（Dev Run Console 六阶段状态机、Skill SDK 三层校验、F01-F04 迁移、Alembic 权威、模块化应用组合壳）的理解记录在 git 历史中的旧版认知地图与 `docs/architecture/`、F01-F05 文档里；相关代码保留在归档分支 `rrh/f01*`~`rrh/f05*`、`rrh/feature-dev` 等（2026-08-13 已推送归档或删除）
- 仓库统一行动（2026-08-13）：30 个 worktree 全部移除、40 个本地分支收敛为 main + 7 个归档分支、坏 merge 分支删除、根目录卫生、README/AGENTS/文档索引重写对齐 K0 方向
