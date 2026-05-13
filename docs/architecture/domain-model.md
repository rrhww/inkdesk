# 领域模型

## 目标

定义当前 MVP 需要稳定下来的核心实体，为个人知识健康系统提供统一语言。

## 核心角色

### Owner

系统主人，也是唯一使用者。

职责：

- 登录隐藏入口
- 导入研究材料
- 审阅 AI 提案
- 维护正式 wiki
- 基于现有知识继续 Ask
- 处理知识健康信号

## 核心实体

### RawSource

进入系统的原始材料。

字段关注点：

- 标题
- 来源类型
- locator / URL
- 摘录
- vault 路径
- 导入状态

### IngestReview

AI 基于 raw 材料或 Ask 诊断生成的认知变更提案。

字段关注点：

- 提案类型
- 目标 topic 决策
- explanation
- claims
- evidence
- open questions
- health signal 来源
- 审阅状态

补充说明：

- proposal claim 需要暴露 `supportingChunkIds`、`evidenceCount`、`provenanceStatus`
- 这样 owner 在 ingest 就能先看清“这条判断有没有直接证据”

### WikiPage

已经被接受并进入正式知识层的当前理解页面。

字段关注点：

- 标题
- current understanding
- claims
- open questions
- 关联来源
- vault 路径
- 健康摘要

### AskTurn

一次研究问答及其诊断快照。

字段关注点：

- question
- answer
- mode
- context ask turn ids
- used wiki ids
- used source ids
- used web sources
- knowledge gaps
- writeback package
- health signals

补充说明：

- AskTurn 还会绑定 ask-scoped judgment payload
- 这个 payload 负责保存“当前缺什么证据、下一步该做什么”的结构化判断结果

### HealthSignal

一次 Ask、ingest、wiki 或 raw 状态暴露出来的知识健康信号。

字段关注点：

- signal type
- severity
- related raw source
- related wiki page
- related claim
- related ask turn
- summary
- suggested action
- status

当前重点信号包括：

- `RAW_BACKLOG`
- `REVIEW_BACKLOG`
- `OPEN_QUESTIONS`
- `KNOWLEDGE_GAP`
- `UNSUPPORTED_CLAIM`
- `WRITEBACK_CANDIDATE`

### Claim

wiki 页面中的最小知识断言。

字段关注点：

- statement
- source links
- evidence strength
- last verified at
- usage count
- health status

当前治理语义：

- `supported`：已有直接证据链
- `partial`：已绑定来源，但缺少直接证据链
- `unsupported`：没有足够直接证据，不应被当作稳定结论

### WorkspaceSetting

系统级工作区配置。

字段关注点：

- owner 级基础配置
- vault 根目录
- Agent profile
- 与研究工作流相关的运行设置

## 派生视图

以下内容可以作为前端或服务层派生视图，不要求一开始独立建模为复杂实体：

- Research dashboard snapshot
- Ask 推荐问题
- 待审阅数量摘要
- 主题聚焦上下文
- Knowledge health summary

## 边界说明

- RawSource 是所有正式知识的 provenance 起点
- IngestReview 是认知变更的人工确认闸门
- WikiPage 是正式当前理解层，不允许 AI 静默改写
- Claim 是知识健康治理的核心原子
- AskTurn 是研究诊断快照，不是通用聊天系统会话模型
- HealthSignal 是 Inkvault 区别于普通 llm-wiki 闭环的产品核心
