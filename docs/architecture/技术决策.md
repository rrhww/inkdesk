# 技术决策

## 1. 仓库结构

- 继续使用单仓库
- `web/` 承担私有前端工作区
- `server/` 承担 FastAPI 主后端
- `infra/` 承担本地基础设施模板

原因：当前产品是单人私有部署模型，没必要拆成多仓或多服务前台。

## 2. 前端框架

- 使用 `Next.js App Router`

原因：

- 私有路由守卫与服务端渲染协作简单
- 方便在 server component 中转发 owner cookie
- 与当前测试和构建链路已经对齐

## 3. 路由模型

- 私有工作区固定在 `/app`
- `/` 只做登录态分流
- 未登录访问 `/` 重定向到 `/login`
- 已登录访问 `/` 重定向到 `/app`

原因：当前没有公开阅读面，根路由不再承担 public site 职责。

## 4. 认证模型

- 单 owner 登录
- 会话 Cookie 固定为 `inkdesk_owner_session`
- 登录标识固定为邮箱

原因：先把私有闭环做稳，不扩展多角色和复杂权限。

## 5. 产品主语言

- 当前主产品语言固定为 `raw / ingest / wiki / ask`
- `notes / plans / publish / public` 只允许出现在迁移或历史上下文中

原因：统一产品语言能减少设计、实现和文档漂移。

## 6. 数据真相边界

- `raw/` 和 `wiki/` 的 Markdown 文件是长期真相
- PostgreSQL 存索引、关系、队列和问答记录
- 数据库缺失时，允许从 vault frontmatter 回补部分关联

原因：保证长期可迁移性，避免知识被 DB 结构锁死。

## 7. 写入策略

- AI 不能直接写 wiki
- 所有编译和 writeback 结果都先进入 `review_items`
- 只有 owner 接受后才落入 `wiki/`

原因：把“AI 提议”和“正式知识”明确拆开。

## 8. Ask 策略

- Ask 默认 `wiki first, raw second`
- `vault_plus_web` 只在 owner 显式选择时启用
- 外部网页证据不会自动进 vault，必须通过 writeback 流程保存

原因：控制联网边界，保持知识沉淀可审计。

## 9. 迁移兼容策略

- 保留 `content_nodes` 和 `note_documents`
- legacy note 继续作为 `raw` 的迁移来源
- 兼容路由 `inbox/review/topics/sources` 暂时保留重定向

原因：避免一次性清空历史内容，同时不让旧模型继续主导产品。

## 10. 前端数据策略

- 已配置 API 基地址时，前端读真实后端
- 未配置时，前端允许回退到本地 research fixtures

原因：既保证全栈联调能力，也保留纯前端演示和开发效率。

## 11. Schema 演进策略

- 主迁移来源仍是 `server/src/main/resources/db/migration/*.sql`
- Python 主后端启动时会执行轻量 schema upgrade，补齐新增列

原因：当前仓库处于 Java 迁移到 Python 之后的收口阶段，需要兼顾旧库平滑升级。

## 12. 当前明确不做

- 公开文章 / 公开访客系统
- plans 主路径
- search 主路径
- settings 主路径
- 多租户或多人协作

原因：这些内容都已退出当前 MVP 主线。
