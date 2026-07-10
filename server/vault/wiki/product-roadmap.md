---
type: concept
created: 2026-07-10
updated: 2026-07-10
tags: [产品规划, 路线图, 阶段, 门禁]
related: [ai-rd-automation-llm-wiki, system-architecture]
source_file: docs/product/产品路线图.md
status: stable
---

# 产品路线图与阶段规划

## 主开发顺序（固定）

`Sources -> LLM-Wiki -> Schema -> Skills -> Agent Runtime -> Evaluation -> Harness`

## 用户主路径（极简）

`PRD/bug/改造任务 -> Dev Run -> 阶段输出 -> Review/Deposit`

## 六大阶段

### 阶段一：Sources 与 LLM-Wiki 对齐
做稳 `raw -> ingest -> wiki -> ask` 主路径，Ask 回答回流为可审阅 wiki 提案，加入第一批 Wiki Health 检查。
**门禁**：闭环本地跑通、AI 不能静默改写 wiki、vault 文件可被普通 Markdown 工具理解。

### 阶段二：Schema 层
在 vault 中加入 agent-facing schema 文件（vault-layout、wiki-page-template、source-citation-rules、ingest-proposal-rules、ask-answer-rules、wiki-health-rules），让多 Agent 共享同一维护协议。
**门禁**：schema 初始化幂等。

### 阶段三：Skills 与 Skill Workbench
把重复工作沉淀为显式 skill 文件，从知识管理类扩展到研发流程类（Tech Solution/Review/Coding/Test Prep/Fix/Problem Solve/Skill Router）。
**门禁**：skill 不能直接静默写 wiki。

### 阶段四：Agent Runtime Runs
为 skill 执行建立可追踪 run 记录，支持 LangGraph/外部 runtime。
**门禁**：runtime 失败不污染 wiki。

### 阶段五：Evaluation
引入 golden tasks 与 rubrics，建立 promotion gate，阻止 blind prompt drift。
**门禁**：失败评测不能改 accepted wiki。

### 阶段六：Harness 与外部 Agent 接入
多步骤 harness 编排，接入 Claude Code/Codex/Cursor，将 PRD->方案->评审->coding->test->fix->deposit 串成受控 Dev Run。
**门禁**：高自治度必须 opt-in 并有 evaluation history 支撑。

## 当前进度（2026-07-10）

- 阶段一~四：已完成
- 阶段五（Evaluation）：待启动
- 阶段六（Harness）：待启动
- Skill-driven stage actions：已完成，stage action 执行前检查 hard gate，prompt 注入 SKILL.md + wiki 检索
- 交互式 coding SSE：已完成，Claude Agent SDK 替代 CLI subprocess
