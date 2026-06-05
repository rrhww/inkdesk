# 页面清单

## 目标

逐页说明当前私有研究工作区需要承载的页面目标和状态。

## 页面清单

| 页面 | 路由 | 主要目标 | 关键模块 | 关键状态 | 优先级 |
| --- | --- | --- | --- | --- | --- |
| 根路由分流 | `/` | 按登录态重定向 | session 检查、重定向 | 未登录、已登录 | P0 |
| 登录页 | `/login` | 进入私有工作区 | 登录表单、错误提示 | 默认、失败 | P0 |
| 首页 | `/app` | 展示 Today Vault Panel 与研究入口 | summary、focus topic、recent sources、pending reviews、suggested questions | 默认 | P0 |
| Ask 页 | `/app/ask` | 发起研究问答与追问 | 提问表单、回答、知识缺口、follow-up、writeback | 空状态、有回答、联网补料、追问中 | P0 |
| Raw 页 | `/app/raw` | 管理原始材料 | 来源列表、网页导入、文本导入、PDF 导入 | 空状态、有来源、导入中 | P0 |
| Ingest 页 | `/app/ingest` | 审阅 AI 提案 | 提案列表、来源、topic 归属、接受/拒绝 | 有提案、提案已处理 | P0 |
| Wiki 列表页 | `/app/wiki` | 浏览知识页 | topic 列表、摘要、来源数 | 空状态、有结果 | P0 |
| Wiki 详情页 | `/app/wiki/[id]` | 阅读单个知识页 | current understanding、key claims、open questions、sources、research thread | 正常、主题不存在 | P0 |

## 兼容页面

以下页面不再作为独立产品面，只保留跳转：

- `/app/inbox`
- `/app/review`
- `/app/topics`
- `/app/sources`

## 页面状态要求

- 登录页覆盖默认和失败状态
- 首页至少覆盖有聚合数据的默认状态
- Raw 页覆盖导入表单与已有来源列表
- Ingest 页覆盖待审阅和已处理反馈
- Wiki 详情页覆盖 understanding / claims / questions / sources
- Ask 页覆盖空状态、有答案、continueFromAskTurnId、`vault_plus_web`

## 实现说明

- 当前没有公开首页和公开文章页
- 当前没有 `plans`、`search`、`publish`、`settings` 页面
- 页面文案应统一使用 `raw / ingest / wiki / ask` 语言
