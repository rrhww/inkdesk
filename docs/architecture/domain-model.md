# 领域模型

## 目标

统一当前 vault-first 私有 LLM Wiki 的业务语言，避免再混用旧的 `notes / plans / publish / public` 术语。

## 核心角色

### Owner

当前唯一主要用户。

职责：

- 登录私有工作区
- 导入原始材料到 `raw/`
- 审阅 AI 提案
- 维护 `wiki/` 长期记忆
- 发起 Ask、追问、决定是否 writeback

## 核心实体

### Workspace

单 owner 工作区。

职责：

- 承载 owner 的所有研究数据
- 作为 source、topic、review、ask 的逻辑归属边界

### Source

原始材料，也就是 `raw/` 中的来源对象。

典型来源：

- 网页
- PDF
- 手动文本
- 从 legacy note 迁移出的历史内容

关键语义：

- 先进入 `raw`
- 可以被编译进一个或多个 topic
- 必须保留可回溯定位信息

### ReviewItem

由 AI 生成、等待人工决策的提案。

关键语义：

- 是 `ingest` 页面上的主对象
- 可以创建新 topic，也可以 patch 现有 topic
- 未接受前不能直接改写 wiki

### Topic

已沉淀的知识页，也就是 `wiki/` 中的核心对象。

关键语义：

- 有 summary、current understanding、open questions
- 通过 claims 和 sources 保留证据链
- 最终内容可以从 vault Markdown 恢复

### TopicClaim

知识页中的关键论点。

关键语义：

- 对应一句可引用的稳定判断
- 应尽量能追溯到 source

### TopicThreadEntry

知识页的研究过程片段。

关键语义：

- 保存提炼过程、补充说明和研究痕迹
- 帮助 owner 理解当前知识页是如何形成的

### AskTurn

一次研究问答与其上下文快照。

关键语义：

- 支持 topic scoped 和 global ask
- 支持追问链
- 记录引用、知识缺口、follow-up questions 与 writeback 包

### RetrievalChunk

为 Ask 和检索准备的 chunk 级索引对象。

关键语义：

- 是内部检索基础设施，不直接面向 UI
- 可支持 lexical fallback 与 embedding/hybrid retrieval

### LegacyNoteBridge

由 `content_nodes` 和 `note_documents` 组成的迁移兼容层，不是新主产品对象。

关键语义：

- 用于接住旧内容
- 用于初始化 demo 数据和过渡期研究编译

## 派生视图

以下内容目前主要作为服务层或前端聚合视图存在：

- Today Vault Panel
- suggestedQuestions
- Ask thread view
- ingest queue summary

## 边界说明

- 当前没有访客角色，也没有公开阅读面
- 当前没有 plans / publish / settings 主路径
- Ask 是研究入口，不等于自治 Agent 执行系统
- Vault Markdown 是长期真相，数据库和 UI 都要围绕它对齐
