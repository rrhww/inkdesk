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

## 模糊区

- behavioral contract cases 的实际执行 — 格式已定，contents 待 Skill 实战后产生
- gate severity（block vs warn）区分 — 当前 contract 的 hardGates 是 flat list，ingest-source 的 schema_gate_passed 是 block，run-wiki-health 的同名 gate 是 warn，contract 不区分；需改 SDK 建模
- human_confirmation gate 未在 SDK 注册为认可的 gate-kind

## 黑盒区（完全不懂）

- 外部 Agent 加载 Skill package 后的实际执行行为 — 当前只保证 package 可校验，执行语义未定义
