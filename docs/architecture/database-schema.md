# 数据库结构

## 目标

这份文档描述当前仓库已经落地的数据库模型，而不是历史设想。

当前数据库主要承担三类职责：

- owner / workspace / 会话相关索引
- `raw -> ingest -> wiki -> ask` 工作流状态
- retrieval 索引与兼容性迁移支撑

长期真相仍然是 vault 中的 Markdown；数据库负责索引、队列、缓存与追踪。

## 建模原则

- Vault 文件优先，数据库不是唯一真相
- AI 写入必须先经过 `review_items`
- `topics` 与 `sources` 是当前主产品对象
- 旧 `content_nodes` / `note_documents` 仅作为 legacy note 迁移桥接层保留
- schema 以 `server/src/main/resources/db/migration/*.sql` 和 `server/inkvault_server/models.py` 为准

## 当前表清单

### 核心身份与空间

- `users`
- `workspaces`

### 迁移兼容层

- `content_nodes`
- `note_documents`

### 研究主路径

- `sources`
- `topics`
- `topic_sources`
- `topic_claims`
- `topic_thread_entries`
- `review_items`
- `ask_turns`
- `retrieval_chunks`

## 逐表说明

### `users`

用途：owner 账号。

关键字段：

- `username`
- `email`
- `password_hash`
- `status`

### `workspaces`

用途：单 owner 工作区容器。

关键字段：

- `owner_user_id`
- `name`
- `slug`

### `content_nodes`

用途：保留旧 note tree 结构，用于 legacy note 迁移与兼容种子数据。

说明：

- 不是当前主产品里的“知识库页面”来源
- 当前前端不再直接围绕 `notes` 工作流开发

### `note_documents`

用途：为 `content_nodes` 提供旧 Markdown 正文。

说明：

- 主要用于迁移期把 legacy note 编译成 `raw` 来源

### `sources`

用途：`raw/` 中的原始材料索引。

关键字段：

- `legacy_note_id`
- `kind`
- `status`
- `title`
- `locator`
- `excerpt`
- `body`
- `vault_path`
- `content_hash`

说明：

- `kind` 当前覆盖 `TEXT`、`WEB`、`PDF` 等来源类型
- `status` 用来区分待编译、已关联、已忽略等状态
- `vault_path` 指向 `raw/` 下的真实文件

### `topics`

用途：`wiki/` 知识页索引。

关键字段：

- `title`
- `slug`
- `summary`
- `current_understanding`
- `open_questions`
- `vault_path`
- `content_hash`

说明：

- 当前一个 topic 对应一篇已沉淀的 wiki 页面
- 长期真相仍然落在 `wiki/*.md`

### `topic_sources`

用途：topic 与 source 的多对多关联表。

说明：

- 用于溯源，说明某个知识页由哪些原始材料支撑

### `topic_claims`

用途：保存知识页中的关键论点及其引用标签。

关键字段：

- `statement`
- `citation_label`
- `sort_order`
- `source_id`

### `topic_thread_entries`

用途：保存知识页的研究过程线程。

关键字段：

- `role`
- `content`
- `sort_order`
- `source_id`

### `review_items`

用途：`ingest/` 审阅队列。

关键字段：

- `source_id`
- `target_topic_id`
- `kind`
- `proposal_kind`
- `status`
- `title`
- `summary`
- `proposed_*`
- `proposal_payload_json`
- `content_hash`

说明：

- 所有 AI 提案都必须先进入这里
- 接受后才允许写入或更新 wiki

### `ask_turns`

用途：保存 Ask 历史、引用和 writeback 包。

关键字段：

- `topic_id`
- `parent_ask_turn_id`
- `thread_root_ask_turn_id`
- `mode`
- `question`
- `answer`
- `confidence`
- `retrieval_mode`
- `used_wiki_ids`
- `used_source_ids`
- `used_chunk_ids`
- `used_web_sources_json`
- `knowledge_gaps_json`
- `follow_up_questions_json`
- `can_writeback`
- `writeback_package_json`
- `citation_source_ids`

说明：

- 除迁移 SQL 外，应用启动时也会执行 schema upgrade，补齐新列

### `retrieval_chunks`

用途：保存用于检索的 chunk 级索引。

关键字段：

- `entity_type`
- `entity_id`
- `chunk_ordinal`
- `text`
- `content_hash`
- `embedding_json`

说明：

- 当前兼容 lexical fallback 与 embedding/hybrid retrieval
- PostgreSQL 会确保 `vector` 扩展存在，但当前模型仍把 embedding 以 JSON 形式保存

## 主要关系

- `workspaces.owner_user_id -> users.id`
- `content_nodes.workspace_id -> workspaces.id`
- `note_documents.note_id -> content_nodes.id`
- `sources.workspace_id -> workspaces.id`
- `sources.legacy_note_id -> content_nodes.id`
- `topics.workspace_id -> workspaces.id`
- `topic_sources.topic_id -> topics.id`
- `topic_sources.source_id -> sources.id`
- `topic_claims.topic_id -> topics.id`
- `topic_claims.source_id -> sources.id`
- `topic_thread_entries.topic_id -> topics.id`
- `topic_thread_entries.source_id -> sources.id`
- `review_items.workspace_id -> workspaces.id`
- `review_items.source_id -> sources.id`
- `review_items.target_topic_id -> topics.id`
- `ask_turns.workspace_id -> workspaces.id`
- `ask_turns.topic_id -> topics.id`

## 已淘汰表

以下旧产品阶段的表已在迁移中退出主路径：

- `plans`
- `plan_notes`
- `tags`
- `note_tags`
- `publications`
- `workspace_settings`

它们不应再出现在当前产品设计和接口说明里。

## 后续衔接点

- 业务语言见 `architecture/domain-model.md`
- 接口边界见 `architecture/api-draft.md`
- 运行边界见 `architecture/tech-decisions.md`
