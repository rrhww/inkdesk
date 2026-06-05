# API 草图

## 目标

固定当前 vault-first Agent Knowledge Runtime 的后端接口边界。

当前接口只服务以下主路径：

- owner 登录与会话校验
- `raw` 原始材料导入与读取
- `ingest` 提案审阅
- `wiki` 知识页读取
- `ask` 研究问答与 deposit / writeback 提案

用户主路径是 `Ask -> 沉淀`。当前实现里沉淀先复用 Ask writeback；后续会抽象成独立 deposit API，并接入 MCP / CLI。

## 一、健康检查

### `GET /health`

- 目标：基础存活探针

### `GET /actuator/health`

- 目标：暴露服务状态与 retrieval 健康信息

## 二、认证接口

### `POST /api/auth/login`

- 目标：owner 登录
- 用途：`/login`

### `POST /api/auth/logout`

- 目标：owner 退出
- 用途：私有工作区顶部退出按钮

### `GET /api/auth/me`

- 目标：返回当前 owner 与 workspace 信息
- 用途：前端会话校验、受保护页面初始化

## 三、首页聚合接口

### `GET /api/admin/home`

- 目标：返回 `/app` 首页所需的 Today Vault Panel 聚合数据
- 返回重点：
  - summary
  - focusTopic
  - recentSources
  - pendingReviews
  - suggestedQuestions

## 四、Raw 接口

### `GET /api/raw`

- 目标：读取 raw vault 中已索引的来源列表

### `POST /api/raw`

- 目标：直接创建一条文本来源
- 当前用途：手动粘贴文本、迁移材料补录

### `POST /api/raw/web`

- 目标：从网页 URL 导入来源

### `POST /api/raw/pdf`

- 目标：上传 PDF 并导入来源

## 五、Ingest 接口

### `GET /api/ingest`

- 目标：读取待审阅提案列表

### `GET /api/ingest/{review_id}`

- 目标：读取单条提案详情

### `POST /api/ingest/{review_id}/accept`

- 目标：接受提案并把变更写入 wiki

### `POST /api/ingest/{review_id}/reject`

- 目标：拒绝提案并保留审阅记录

## 六、Wiki 接口

### `GET /api/wiki`

- 目标：读取知识页列表

### `GET /api/wiki/{topic_id}`

- 目标：读取单个知识页详情
- 返回重点：
  - summary
  - currentUnderstanding
  - keyClaims
  - openQuestions
  - sources
  - researchThread

## 七、Ask 接口

### `POST /api/ask`

- 目标：基于 wiki first、raw second 执行研究问答
- 支持模式：
  - `vault`
  - `vault_plus_web`

### `GET /api/ask/{ask_turn_id}`

- 目标：读取单轮 Ask 结果

### `GET /api/ask/{ask_turn_id}/thread`

- 目标：读取当前 Ask 所在追问链

### `POST /api/ask/{ask_turn_id}/writeback`

- 目标：把当前 Ask 结果转成一条新的 ingest 提案

## 八、Deposit 接口规划

### `POST /api/deposit/answer`

- 目标：沉淀一段完整回答
- 输入重点：
  - question
  - answer
  - citations
  - source context
  - optional repo/task metadata
- 当前状态：规划中，第一阶段由 `POST /api/ask/{ask_turn_id}/writeback` 承接

### `POST /api/deposit/selection`

- 目标：沉淀用户选中的片段
- 输入重点：
  - selected text
  - reason
  - source context
  - optional repo/task metadata
- 当前状态：规划中

### `GET /api/context-pack`

- 目标：给外部 Agent 返回当前任务相关的短上下文包
- 典型调用方：Claude Code、Codex、Cursor 的 MCP / CLI connector
- 当前状态：规划中

## 当前不提供

- `plans` 接口
- `search` 接口
- `settings` 接口
- 公开文章 / 公开访客接口
- 旧 `notes` / `publish` 工作流接口

## 关键边界

- 会话 Cookie 固定为 `inkdesk_owner_session`
- AI 不能直接改写 wiki，只能先生成可审阅提案
- 外部 Agent 不能直接写 vault，只能调用 context / deposit 协议
- 未配置 API 基地址时，前端允许回退到本地 fixtures，但后端契约仍以本文件为准
