# 数据库结构

## 目标

这份文档用于说明 Inkdesk MVP 的数据库建模方向，包括表职责、关键字段建议、关系约束和索引方向。当前以实现指导为目标，不追求完整 SQL。

## 建模原则

- 目录树和正文分离
- 当前正文和快照分离
- 发布信息独立建模
- 标签使用关联表
- 图片资源不落数据库二进制字段

## 表清单

- `users`
- `workspaces`
- `content_nodes`
- `note_documents`
- `note_revisions`
- `tags`
- `note_tags`
- `assets`
- `publications`

## 逐表说明

### `users`

用途：
保存拥有者账号信息。

关键字段建议：

- `id`
- `username`
- `password_hash`
- `status`
- `created_at`
- `updated_at`

索引方向：

- `username` 唯一索引

### `workspaces`

用途：
保存主系统空间信息，作为未来扩展位。

关键字段建议：

- `id`
- `owner_user_id`
- `name`
- `slug`
- `created_at`
- `updated_at`

索引方向：

- `owner_user_id`
- `slug` 唯一索引

### `content_nodes`

用途：
统一保存目录节点和笔记节点。

关键字段建议：

- `id`
- `workspace_id`
- `parent_id`
- `type`
- `title`
- `sort_order`
- `status`
- `created_at`
- `updated_at`

说明：

- `type` 区分 `folder` 和 `note`
- `parent_id` 支撑树结构
- `sort_order` 支撑目录排序

索引方向：

- `workspace_id`
- `parent_id`
- `(workspace_id, parent_id, sort_order)`

### `note_documents`

用途：
保存当前版本的 Markdown 正文。

关键字段建议：

- `id`
- `note_id`
- `markdown_content`
- `excerpt`
- `word_count`
- `updated_at`

说明：

- 与 `content_nodes` 解耦，避免树结构表承载大字段正文
- `excerpt` 可用于列表摘要和公开首页展示

索引方向：

- `note_id` 唯一索引
- 正文搜索索引，结合 PostgreSQL 全文检索或 `pg_trgm`

### `note_revisions`

用途：
保存手动快照。

关键字段建议：

- `id`
- `note_id`
- `markdown_snapshot`
- `summary`
- `created_by`
- `created_at`

说明：

- 不记录每次自动保存
- 只记录用户显式创建的快照

索引方向：

- `note_id`
- `(note_id, created_at desc)`

### `tags`

用途：
保存标签定义。

关键字段建议：

- `id`
- `workspace_id`
- `name`
- `slug`
- `created_at`

索引方向：

- `(workspace_id, name)` 唯一索引
- `(workspace_id, slug)` 唯一索引

### `note_tags`

用途：
维护笔记与标签的多对多关系。

关键字段建议：

- `note_id`
- `tag_id`

索引方向：

- `(note_id, tag_id)` 唯一索引
- `tag_id`

### `assets`

用途：
保存图片资源元信息。

关键字段建议：

- `id`
- `workspace_id`
- `storage_key`
- `public_url`
- `mime_type`
- `size`
- `created_at`

说明：

- 不保存二进制内容
- `storage_key` 对应 COS 或 MinIO 中的对象路径

索引方向：

- `workspace_id`
- `storage_key` 唯一索引

### `publications`

用途：
管理公开发布状态。

关键字段建议：

- `id`
- `note_id`
- `slug`
- `status`
- `published_at`
- `updated_at`

说明：

- 一篇笔记最多对应一个有效发布记录
- `slug` 用于公开访问路径

索引方向：

- `note_id` 唯一索引
- `slug` 唯一索引
- `status`

## 关系约束

- `workspaces.owner_user_id -> users.id`
- `content_nodes.workspace_id -> workspaces.id`
- `content_nodes.parent_id -> content_nodes.id`
- `note_documents.note_id -> content_nodes.id`
- `note_revisions.note_id -> content_nodes.id`
- `tags.workspace_id -> workspaces.id`
- `note_tags.note_id -> content_nodes.id`
- `note_tags.tag_id -> tags.id`
- `assets.workspace_id -> workspaces.id`
- `publications.note_id -> content_nodes.id`

## 搜索策略说明

MVP 阶段优先使用 PostgreSQL 搜索能力：

- 标题搜索
- 正文搜索
- 标签命中

暂不引入独立搜索引擎，原因是：

- 维护成本更低
- 数据量小阶段完全够用
- 更适合单人学生项目

## 为什么当前不拆更复杂模型

- 当前没有多人协作，不需要权限关系表
- 当前没有深度 Agent 功能，不需要 chunk 和 embedding 表
- 当前没有自动化编排，不需要任务编排表
- 当前没有附件系统，不需要复杂文件权限和下载审计

## 后续衔接点

- 业务实体说明见 `architecture/domain-model.md`
- 搜索和技术路线见 `architecture/tech-decisions.md`
