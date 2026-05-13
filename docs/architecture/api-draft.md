# API 草图

## 目标

为当前私有研究工作台固定一版接口边界，支持隐藏登录、raw / ingest / wiki / ask 主闭环。

## 一、认证接口

### `POST /api/auth/login`

- 目标：主人登录
- 用途：`/login`

### `POST /api/auth/logout`

- 目标：退出系统
- 用途：主系统退出操作

### `GET /api/auth/me`

- 目标：获取当前主人信息
- 用途：主系统初始化

## 二、研究工作区上下文接口

### `GET /api/admin/home`

- 目标：聚合工作区 shell 与判断事实输入，不直接决定 `/app` 主内容
- 返回：
  - summary / health
  - 焦点 topic
  - 待审阅数量
  - 最近来源
  - 推荐问题
- 其中 `health` 当前还包含：
  - `unsupportedClaimCount`
  - `signals[]`，并允许出现 `UNSUPPORTED_CLAIM`
- 用途：
  - 作为工作区计数和上下文摘要
  - 作为 briefing 的事实输入之一
  - 不再单独充当 dashboard-first 首页接口

## 三、Raw 接口

### `GET /api/raw`

- 目标：获取 raw 材料列表

### `POST /api/raw`

- 目标：导入网页、文本或 PDF 材料

## 四、Ingest 接口

### `GET /api/ingest`

- 目标：获取待审阅提案列表
- 返回中的 proposal claims 当前还会包含：
  - `supportingChunkIds[]`
  - `evidenceCount`
  - `provenanceStatus`

### `POST /api/ingest/{id}/accept`

- 目标：接受提案并写入 wiki

### `POST /api/ingest/{id}/reject`

- 目标：拒绝提案

## 五、Wiki 接口

### `GET /api/wiki`

- 目标：获取 wiki 页面列表

### `GET /api/wiki/{id}`

- 目标：获取单个 wiki 页面详情
- 返回中的 `keyClaims[]` 当前还会包含：
  - `evidenceCount`
  - `provenanceStatus`
  - `lastVerifiedAt`

## 六、Ask 接口

### `GET /api/ask/briefing`

- 目标：返回 Ask-first 工作区的当前判断摘要
- 查询参数：
  - 无参数：返回 `workspace` scope 的首屏判断
  - `topicId?`：返回 `topic` scope 的判断摘要
  - `askTurnId?`：返回 `ask_turn` scope 的问后判断
  - 若同时传 `askTurnId` 和 `topicId`：以前者为准
- 返回：
  - `scope`
  - `topicId?`
  - `topicTitle?`
  - `askTurnId?`
  - `summary`
  - `confidence`
  - `knowledgeGaps[]`
  - `nextActions[]`
  - `suggestedQuestions[]`
  - `supportingSignals[]`
  - `generatedAt`
- 语义：
  - 结构化输出固定锁定 schema
  - provider 不可用、无 key 或 schema 失败时，返回 deterministic briefing，而不是让 `/app` 失效
  - ask-turn scope 的判断结果可与 AskTurn 绑定保存；旧 AskTurn 若无 payload，则按请求时现算返回

### `POST /api/ask`

- 目标：围绕 wiki/raw 发起研究问答
- 请求：
  - `question`
  - `topicId?`
  - `mode: "vault" | "vault_plus_web"`
  - `continueFromAskTurnId?`
- 返回：
  - `id`
  - `topicId`
  - `parentAskTurnId`
  - `threadRootAskTurnId`
  - `lineageAskTurnIds`
  - `question`
  - `answer`
  - `confidence`
  - `retrievalMode`
  - `citations`
  - `knowledgeGaps`
  - `followUpQuestions`
  - `usedWikiIds`
  - `usedSourceIds`
  - `usedWebSources`
  - `contextAskTurnIds`
  - `canWriteback`
  - `createdAt`
- 语义：
  - `/api/ask` 只负责回答，不把 briefing 混入 Ask 响应
  - 前端应在拿到 answer 后，再串行拉取 `/api/ask/briefing?askTurnId=...` 刷新问后判断

### `POST /api/ask/{id}/writeback`

- 目标：把 Ask 回答生成新的 ingest proposal
- 语义：
  - 读取 AskTurn 中已有的 writeback package
  - 若本轮使用了外部网页，先写入 raw/source
  - 再生成 ingest proposal

## 备注

- 当前不做公开访客接口
- 当前不做 plans 接口
- 当前不做 publish 接口
- 当前不做复杂多 agent 调度接口
- 当前不做 settings 前台编辑接口
