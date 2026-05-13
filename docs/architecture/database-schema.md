# 数据库结构

## 目标

这份文档用于说明 Inkvault 当前研究闭环的数据库建模方向，包括表职责、关键字段建议、关系约束和索引方向。

## 建模原则

- vault 文件是真相，数据库是索引与状态层
- raw、ingest、wiki、ask 分层清晰
- 提案与正式知识分离
- Ask 结果以研究状态快照持久化
- 尽量为重建与幂等保留结构

## 表清单

- `owners`
- `workspaces`
- `workspace_settings`
- `sources`
- `wiki_pages`
- `wiki_claims`
- `wiki_open_questions`
- `reviews`
- `ask_turns`

## 逐表说明

### `owners`

用途：
保存系统唯一拥有者账号信息。

关键字段建议：

- `id`
- `email`
- `password_hash`
- `status`
- `created_at`
- `updated_at`

索引方向：

- `email` 唯一索引

### `workspaces`

用途：
保存当前研究工作区信息。

关键字段建议：

- `id`
- `owner_id`
- `name`
- `created_at`
- `updated_at`

索引方向：

- `owner_id`

### `workspace_settings`

用途：
保存工作区运行设置。

关键字段建议：

- `workspace_id`
- `vault_root`
- `agent_provider_profile`
- `agent_runtime`
- `web_assist_enabled`
- `updated_at`

索引方向：

- `workspace_id` 唯一索引

### `sources`

用途：
保存 raw 材料索引。

关键字段建议：

- `id`
- `workspace_id`
- `kind`
- `title`
- `locator`
- `excerpt`
- `status`
- `vault_path`
- `content_hash`
- `created_at`
- `updated_at`

说明：

- 对应进入 `raw/` 的网页、PDF、文本或迁移材料
- `content_hash` 用于去重

索引方向：

- `workspace_id`
- `status`
- `locator`
- `content_hash`

### `wiki_pages`

用途：
保存正式 wiki 页面索引。

关键字段建议：

- `id`
- `workspace_id`
- `title`
- `summary`
- `understanding`
- `vault_path`
- `created_at`
- `updated_at`

索引方向：

- `workspace_id`
- `title`
- `vault_path`

### `wiki_claims`

用途：
保存 wiki 页面的关键结论及来源关联。

关键字段建议：

- `id`
- `wiki_page_id`
- `statement`
- `citation_label`
- `source_id`
- `evidence_count`
- `provenance_status`
- `last_verified_at`
- `updated_at`
- `sort_order`

说明：

- `evidence_count` 用于表示当前 claim 直接证据条数
- `provenance_status` 当前取值为 `supported | partial | unsupported`
- `last_verified_at` 用于记录这条 claim 最近一次被当前证据链验证的时间
- 这些字段直接支撑 wiki 页面、ingest 审阅卡片和 Ask-first 判断面板里的治理提示

索引方向：

- `wiki_page_id`
- `source_id`
- `provenance_status`

### `wiki_open_questions`

用途：
保存 wiki 页面的开放问题。

关键字段建议：

- `id`
- `wiki_page_id`
- `question`
- `sort_order`

索引方向：

- `wiki_page_id`

### `reviews`

用途：
保存 ingest 提案及其审阅状态。

关键字段建议：

- `id`
- `workspace_id`
- `source_id`
- `target_wiki_page_id`
- `kind`
- `title`
- `summary`
- `proposal_payload_json`
- `status`
- `created_at`
- `resolved_at`

说明：

- `proposal_payload_json` 保存 topic 决策、claims、evidence、open questions 等结构化提案内容

索引方向：

- `workspace_id`
- `status`
- `source_id`
- `target_wiki_page_id`

### `ask_turns`

用途：
保存 Ask 研究状态快照。

关键字段建议：

- `id`
- `workspace_id`
- `parent_ask_turn_id`
- `topic_id`
- `question`
- `answer`
- `mode`
- `confidence`
- `used_wiki_ids_json`
- `used_source_ids_json`
- `used_web_sources_json`
- `knowledge_gaps_json`
- `follow_up_questions_json`
- `writeback_package_json`
- `judgment_payload_json`
- `created_at`

说明：

- AskTurn 既是回答记录，也是追问上下文恢复与 writeback 幂等的基础
- `judgment_payload_json` 只保存与该轮 Ask 绑定的 ask-scoped briefing 结果
- 首屏 `workspace` briefing 不落库；旧 AskTurn 若没有 judgment payload，可按请求时现算返回

索引方向：

- `workspace_id`
- `parent_ask_turn_id`
- `topic_id`
- `created_at desc`

## 关系约束

- `workspaces.owner_id -> owners.id`
- `workspace_settings.workspace_id -> workspaces.id`
- `sources.workspace_id -> workspaces.id`
- `wiki_pages.workspace_id -> workspaces.id`
- `wiki_claims.wiki_page_id -> wiki_pages.id`
- `wiki_claims.source_id -> sources.id`
- `wiki_open_questions.wiki_page_id -> wiki_pages.id`
- `reviews.workspace_id -> workspaces.id`
- `reviews.source_id -> sources.id`
- `reviews.target_wiki_page_id -> wiki_pages.id`
- `ask_turns.workspace_id -> workspaces.id`
- `ask_turns.parent_ask_turn_id -> ask_turns.id`

## 搜索策略说明

当前阶段优先使用 PostgreSQL 与 vault 元数据完成：

- wiki 标题与理解检索
- raw 标题、摘录与 locator 检索
- 与 topic 相关的简单相关性召回

暂不把数据库设计成复杂向量平台，原因是：

- 当前数据规模较小
- 产品重点是闭环与可追溯，不是大规模检索基础设施
- 先保证行为清晰，再决定是否扩展更复杂索引

## 为什么当前不拆更复杂模型

- 当前没有多人协作，不需要权限体系
- 当前没有公开发布面，不需要 publication 模型
- 当前没有任务系统，不需要 plans 模型
- 当前没有长时自治 agent，不需要复杂调度模型

## 后续衔接点

- 业务实体说明见 `architecture/domain-model.md`
- Ask 研究路径见 `architecture/system-overview.md`
- 运行与 provider 配置见 `ops/env-vars.md`
