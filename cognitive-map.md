# 认知地图

> 不记录「有什么功能」，记录「你对代码的理解深度」。诚实比完整重要——写「我不知道为什么这样写」比留空有用。

## 已理解（能给别人讲清楚）

### Dev Run Console 阶段执行引擎

- 6 阶段状态机：`context → solution → review → coding → testing → deposit`，通过 `/api/runs/{run_id}/advance` 推进
- 每个阶段都有对应的 stage action API：
  - `POST /api/runs/{run_id}/context-pack` → `context_pack_generated`
  - `POST /api/runs/{run_id}/solution` → `solution_draft_generated`
  - `POST /api/runs/{run_id}/review` → `review_checklist_generated`
  - `POST /api/runs/{run_id}/coding/execute` → `coding_briefing_prepared` + `coding_result_submitted`
  - `GET  /api/runs/{run_id}/coding/status` → 轮询执行状态
  - `POST /api/runs/{run_id}/testing` → `testing_checklist_generated`
  - `POST /api/runs/{run_id}/deposit` → `deposit_created`
- `StageActionService` 统一封装所有阶段逻辑，LLM 阶段遵循 agents.py 模式：`agent_runtime == "deterministic"` 或无 API key 时走模板 fallback
- coding 阶段通过 `asyncio.create_subprocess_exec("claude", "-p", briefing, "--output-format", "text", cwd=repoContext)` 调用 Claude Code CLI，超时 300s
- 浏览器验收驱动出一个产品调整：coding 阶段必须支持「跳过，手动批准」，否则未安装/不想调用 CLI 的用户会卡死在该阶段；实现为 `CodingStagePanel` 写入 `stage_output`（`skipped: true`），让阶段进入 `awaiting_review`
- 前端每个阶段对应一个 `*-stage-panel.tsx` 组件，详情页根据 `run.currentStage` 条件渲染

### inkdesk_skill_sdk 包结构

- `contracts.py` 是 Skill 协议的单一真相源 — Pydantic 模型直接驱动 JSON Schema 生成和 CLI choices
- validation 分三层：structural（文件/目录是否齐全）→ semantic（跨文件 name/id/display_name 一致性 + SemVer + frontmatter 格式）→ safety（writePolicy + 绝对路径扫描 + bypass 检测）
- scaffolder 生成的 `openai.yaml` 根据 kind=router 自动决定 `allow_implicit_invocation: true`
- Registry 只读不执行 — `resolve()` 返回 `SkillMetadata`（含 validation result），`discover()` 递归找有 SKILL.md+contract.json 的目录
- Graph 从 registry 构建节点和边，DFS 检测 cycle，检查单一 router 约束

### Skill Package 约束

- 目录名 = contract.id = SKILL.md frontmatter name — 三者必须一致
- `display_name` 允许人类可读形式，通过 slugify 验证与 contract.id 的对应关系
- canonicalWiki 只有 denied/proposal-only，`"direct"` 直接报 SAFETY_WRITE_POLICY
- 绝对路径扫描覆盖 Windows(`C:\...`)、Unix(`/home/...`)、环境变量(`%APPDATA%`)

### 4.1.4 验收

- valid fixtures: minimal-producer + minimal-reviewer + comprehensive-router
- invalid fixtures: 10 个，每种 lint 规则至少一个
- 4 份 schema 资产注册在 skill_assets.py，contract JSON Schema 由 Pydantic 动态生成，drift test 确认一致

### 4.2.1 首批 Skill

- 13 个 Skill 全部 scaffold 并填充完整 SKILL.md + contract.json + agents/openai.yaml
- 知识管理链：ingest-source → patch-wiki-page, answer-from-wiki → deposit-answer → patch-wiki-page, run-wiki-health → patch-wiki-page, extract-insight → patch-wiki-page
- 研发自动化链：tech-solution → tech-review → coding → test-prep → test-fix → (problem-solve | deposit-answer)
- skill-router 是唯一 router（category=routing），nextSkills 包含所有 12 个 domain skill
- 编写 Skill 的三原则：producer 原则驱动，reviewer 结构化清单 + evidence，diagnostic 从真实信号开始禁止猜测
- SAFETY_BYPASS_CLAIM 的否定语境（「不做：直接写 wiki」）现在正确识别——`_NEGATION_PREFIX` 匹配 `**不做**：` 前缀，`_IMMEDIATE_NEGATION` 匹配紧邻的「不」字

### 4.2.1 Dry-Run Review

- P0 contract 不一致已修复：tech-solution 补 schema_gate_passed，problem-solve 补 vault_initialized
- P1 资源文件已补齐：8 个 Skill 共 18 个空 references/templates 已填充实际内容（entity-extraction-rules、search-strategy、health-check-items、scoring-formula、routing-tree、domain-skills-summary、architecture-patterns、solution-template、review-checklist、coding-standards、architecture-constraints、test-plan-template、error-patterns、diagnostic-tree×2、confidence-rules、proposal-template、known-issues）
- P2 待决策：gate severity 区分、human_confirmation 注册、router 最小上下文契约

### F01 当前行为契约与恢复基线

- F01 不改产品行为；它在结构性迁移前固定当前 HTTP、关键状态机、浏览器流、PostgreSQL catalog 与合成代表性记录形状。
- `scripts/f01/capture-baseline.ps1 -Mode all` 是唯一可认证的入口。它先比较契约并执行测试，再停 `local-server` / `local-web` 形成 PostgreSQL + Vault 安静窗口，最后在 `inkdesk_f01_restore_*` 数据库和 `.local` 内隔离 Vault 执行恢复验证。
- manifest 将测试结果、契约/备份 SHA-256、数据库与 Vault 的组合源指纹、恢复报告和实际匹配的已知问题写到 `.local/f01-baseline/<runId>/`。部分模式只能诊断，不能报告通过。
- `verify_restored_read_paths.py` 使用隔离设置，关闭 seed、编译 worker 和 web assist，只验证恢复后读路径，不会向恢复库写入产品数据。

### F02 Alembic 数据库权威

- `server/alembic/versions/20260712_f02_0001_baseline.py` 是当前 16 张应用表和 PostgreSQL `vector` extension 的唯一 DDL baseline；它显式 `op.create_table`，不调用 ORM `create_all()`，downgrade 明确拒绝。
- `python -m inkdesk_server.db_migrations status|check|upgrade` 是唯一公开 migration 入口。未管理 PostgreSQL 只有在 F01 compatibility digest 精确匹配时才允许 stamp；unknown、partial、drift 和未知 revision 都 fail closed。
- `db.init_db()` 仍保留给 app factory 兼容调用，但它只检查 head revision 与 schema readiness，不创建表、加列或创建 extension。测试 fixture 与 Docker entrypoint 必须先显式 upgrade。
- PostgreSQL migration 在 preflight 到 postflight 持有 advisory lock；F02 verifier 使用 F01 dump 只恢复到 `inkdesk_f02_*` 临时目标，记录 schema/data 指纹和只读 API 结果后清理。
- `server/src/main/resources/db/migration/V1-V8` 是冻结的 Flyway 历史，不再是运行权威。后续 schema 变化只能新增 Alembic revision。

## 模糊区

- behavioral contract cases 的实际执行 — 格式已定，contents 待 Skill 实战后产生
- gate severity（block vs warn）区分 — HardGateChecker 当前用"返回 warn 字符串"表示不阻塞，用"返回失败原因"表示阻塞；schema_gate_passed 和 human_confirmation 是 warn，其余是 block；未改 SDK 建模
- human_confirmation gate 已在 HardGateChecker 注册但当前返回 warn（前端未配合确认 UI），TODO: 前端实现后改为强制
- F01 默认 Docker 恢复证据已在本机 run `20260711T113950Z` 认证为 `PASS`：10 个必需 suite、PostgreSQL + Vault 隔离恢复、恢复后 7 个只读路径和临时目标清理均通过。后续契约或运行时行为变更必须重新运行 `-Mode all`。

## 黑盒区（完全不懂）

- 外部 Agent 加载 Skill package 后的实际执行行为 — 当前只保证 package 可校验，执行语义未定义

## Skill-Driven Stage Actions（2026-07-10 新增）

### 已理解

- `SkillLoader`（skill_loader.py）从 `vault/skills/<stage>/` 加载 SKILL.md + contract.json + references/ + templates/，带进程级缓存
- stage → skill_id 映射：solution→tech-solution, review→tech-review, coding→coding, testing→test-prep；context/deposit 无 Skill
- `HardGateChecker`（hard_gate_checker.py）实现 9 种 GateKind 校验，返回 `GateResult(passed, failures, warnings)`
- 9 种 GateKind 实现状态：
  - `required_input` — 检查 run.goal（requirement/change_scope）或上游事件 payload（solution_doc/tech_review_report）
  - `vault_initialized` — VaultService.get_status().initialized
  - `schema_gate_passed` — warn 不阻塞（wiki schema 健康检查未完整实现）
  - `dev_run_exists` — run 已在 check() 开头加载，必然通过
  - `run_stage_is` — run.currentStage 匹配 params.stage
  - `review_approved` — currentStage > review 或有 stage_approved 事件
  - `artifact_exists` — runs/<run_id>/<artifact>.md 文件存在
  - `real_failure_signal` — warn 不阻塞（diagnostic skill 用，未实现）
  - `human_confirmation` — warn 不阻塞（前端未配合）
- `StageActionService` 4 个 stage action（solution/review/coding/testing）执行前调 `_check_hard_gates()`，失败抛 `ApiError(409, "HARD_GATE_FAILED")`
- 4 个 `_render_*_prompt`/`_assemble_briefing` 方法注入 SKILL.md + references + templates 内容（`_render_skill_context`）
- 4 个 prompt 方法同时注入 wiki 检索结果（`_search_wiki_for_context`）— 这是文章的 Query 操作
- `VaultSearchService.search()` 做分词匹配 + 命中计数排序（casefold），wiki 无命中时回退到 raw/ 目录
- `advance_run` 在 coding stage approve 时检查 `coding_result_submitted.success`，失败抛 `ApiError(409, "CODING_FAILED")` 阻塞推进

### 模糊区

- wiki 检索质量 — 当前是分词匹配 + 命中计数排序 + 200 字符 snippet，无语义检索；wiki 为空时回退 raw/，但 raw 也需要先 ingest 资料才有内容
- artifact_exists gate 的文件路径推断 — 硬编码 solution_doc→tech-solution.md 等映射，如果 contract output location 变化需要同步

### Dogfooding 发现（2026-07-10）

- 第一个真实 Dev Run（run-9513f4ea7a35）全 6 阶段跑通，验证 Skill-driven 改造在真实场景生效
- DeepSeek 模型工具调用能力不足：coding stage $2 预算耗尽未完成任务（已知问题，需 Claude API 才能解决）
- wiki 为空时 Query 操作返回空是正确行为——文章的"预编译知识"需要先通过 ingest-source skill 导入资料
- coding 失败阻塞推进已实现：approve 时返回 409 CODING_FAILED，用户可重新执行 coding/execute
- wiki 检索逻辑缺陷已修复：从整句子串匹配改为分词匹配 + 命中计数排序，4 个 wiki 概念页（ai-rd-automation-llm-wiki/product-roadmap/system-architecture/tech-decisions）已创建
- 第二个 Dev Run（run-58412e75e945）验证 wiki 检索生效：solution draft 中体现 SKILL.md 和 FastAPI/Next.js 技术栈上下文

### Skill Workbench UI（2026-07-10）

- 后端新增 `GET /api/skills` 和 `GET /api/skills/{name}` 端点，调用 `SkillRegistry.get_summary()` 和 `resolve()`，详情端点返回完整 SKILL.md + contract.json + references + templates + agents + validation findings
- 前端列表页 `skills/page.tsx` 展示 registry 概览（total/valid/invalid/byStatus）+ Skill 卡片网格，点击进入详情
- 前端详情页 `skills/[id]/page.tsx` 展示 contract 摘要（inputs/outputs/hardGates/writePolicy/capabilities/nextSkills）+ SKILL.md 全文 + contract.json 全文 + references/templates/agents 文件内容 + validation findings
- 顶部导航新增"技能"tab（app-shell.ts PRIMARY_SECTIONS + getAppRouteChrome）
- 浏览器 E2E 验收通过：13 个 Skill 全部渲染，列表页和详情页数据完整
- 修复 `.env.local.example` 端口配置（8080 → 8000），`.env.local` 被 .gitignore 忽略不进仓库
- 阶段三验收标准"skill 能在 UI 中看到"达成
