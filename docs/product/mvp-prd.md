# Inkvault MVP 产品需求文档

## 1. 产品背景

Inkvault 当前不是一个公开发布平台，也不是一个带完整计划系统的超级工作台。

它已经收敛成一个更聚焦的产品：

- 单人私有
- vault-first
- 围绕研究记忆组织工作的 LLM Wiki

当前最重要的问题不是“展示给访客看什么”，而是“如何把原始材料稳定沉淀成可持续追问的长期知识”。

## 2. 产品定位

Inkvault 当前 MVP 的正式定位是：

- 一个以 `raw -> ingest -> wiki -> ask` 为主路径的私有研究记忆系统

它的核心不是“直接让 AI 写最终答案”，而是：

1. 收集原始材料
2. 让 AI 先提出可审阅提案
3. 由 owner 决定哪些知识进入 wiki
4. 再围绕已沉淀的知识持续追问

## 3. 目标用户

### 主要用户

- owner，也就是你自己
- 使用目标：把网页、PDF、旧笔记和研究问答整理进一个长期可追溯的私人知识系统

### 当前非目标用户

- 公开访客
- 协作者
- 团队成员

当前产品没有公开阅读面，也没有多人协作角色。

## 4. MVP 目标

MVP 只需要跑通一条主链路：

1. owner 通过 `/login` 登录
2. 原始材料进入 `raw/`
3. 系统生成 `ingest` 审阅提案
4. owner 接受后沉淀到 `wiki/`
5. owner 在 `ask` 上基于已有 wiki 和 raw 继续研究

如果这条链路可稳定运行，MVP 就成立。

## 5. 核心价值

- 对 owner：把“资料收集、知识沉淀、研究追问”放进同一条闭环
- 对系统：让 AI 参与研究，但不允许它静默改写长期知识
- 对未来：保留 Ask 深化、自动化和更强检索能力的扩展空间

## 6. MVP 范围内

### 私有入口

- `/login`
- 单 owner 登录
- `/app` 私有首页
- `/` 根据登录态重定向到 `/login` 或 `/app`

### 研究主路径

- `raw`：原始材料导入与索引
- `ingest`：AI 提案审阅
- `wiki`：知识页列表与详情
- `ask`：研究问答、追问、writeback 提案

### 支撑能力

- Vault Markdown 持久化
- PostgreSQL 索引与队列
- owner session
- 本地全栈验收与自动化测试

## 7. MVP 范围外

- 公开文章与公开首页
- plans 主路径
- search 主路径
- settings 主路径
- 多人协作
- 自治 Agent 执行系统
- 面向公众的营销站

## 8. 核心流程

### 流程一：导入原始材料

1. owner 在 `/app/raw` 提交网页、PDF 或文本
2. 后端写入 `raw/` vault 文件并建立索引
3. 材料进入待编译状态

### 流程二：审阅 AI 提案

1. owner 打开 `/app/ingest`
2. 查看 AI 对 source 的编译结果或补丁建议
3. 决定接受或拒绝

### 流程三：沉淀到 wiki

1. 被接受的提案写入或更新 `wiki/`
2. 页面保留 current understanding、claims、questions、sources
3. 数据可从 vault 恢复，不依赖数据库独占保存

### 流程四：继续追问

1. owner 在 `/app/ask` 发起研究问题
2. 系统优先读取 wiki，再补充 raw
3. 如 owner 显式允许，可短暂联网补料
4. 如答案值得沉淀，owner 可把 Ask 结果转成新的 ingest 提案

## 9. 产品原则

- Vault 为底：长期真相必须能回到 Markdown 文件
- 审阅优先：AI 只能提议，不能静默写正式知识
- 私有优先：先把 owner 的闭环做稳，再考虑对外表达
- 研究优先：Ask 服务于知识深化，不服务于花哨聊天
- 低复杂度优先：MVP 只做当前主路径，不恢复旧模块叙事

## 10. 成功标准

满足以下条件即可认为 MVP 可用：

- `/login` 可登录
- `/app/raw` 可导入并读取来源
- `/app/ingest` 可接受 / 拒绝提案
- `/app/wiki` 与 `/app/wiki/[id]` 可稳定展示知识页和来源
- `/app/ask` 可返回带引用的回答
- Ask writeback 只生成提案，不会直接改写 wiki

## 11. 阶段边界

### 当前阶段完成标准

- 本地全栈闭环成立
- 文档与代码对齐
- 旧 public / plans / note editor 方向退出主规范

### 下一阶段优先项

- Ask-first 工作区体验
- 更稳定的 retrieval 与证据链
- 更清晰的 source/topic 演化流程
