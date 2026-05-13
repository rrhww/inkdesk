# Inkvault MVP 产品需求文档

## 1. 产品背景

Inkvault 被重新定义为一个面向 AI 时代的个人知识健康系统。

它的出发点不是“让 AI 基于资料回答”，而是解决一个更深的问题：

- AI 回答越来越多，但很少进入长期知识
- 回答看起来像知识，却缺少证据边界
- 个人知识库会过时、重复、冲突，但工具很少主动暴露
- 用户有专业资料，却不知道这些资料是否真正被消化成可靠理解

因此，Inkvault 的 MVP 不能只证明 `raw -> ingest -> wiki -> ask` 闭环可用，还要证明：

**每一次 Ask 都能反过来产生知识健康信号。**

## 2. 产品定位

Inkvault 的当前官方定位是：

- 一个单人私有、vault-first、以知识健康为核心的 AI 研究系统

它以 llm-wiki 的材料、提案、wiki、问答闭环为基础，但产品创新点前移到知识治理：

- 哪些 raw 没有被编译
- 哪些回答值得沉淀
- 哪些 claim 缺少证据
- 哪些 wiki 仍有开放问题
- 哪些 Ask 暴露了旧知识不足

## 3. 目标用户

### 主要用户

- 有持续专业材料和长期判断需求的单人研究者

主要目标：

- 让 AI 基于自己的专业资料回答
- 把高价值回答沉淀为正式理解
- 看清每条理解的来源和证据边界
- 知道自己的知识系统哪里还不健康
- 在持续使用中让知识越来越可信

### 非目标用户

- 泛笔记用户
- 公开访客
- 团队协作者
- 只需要临时聊天的用户

## 4. MVP 目标

MVP 要跑通一条新的最小闭环：

```text
raw -> ingest -> wiki -> ask -> health -> ingest
```

具体目标：

1. 主人能导入 raw 材料
2. 系统能生成 ingest 提案
3. 主人能接受提案进入 wiki
4. Ask 能基于 wiki / raw 回答
5. Ask 能产出用于判断的 knowledge gaps 与 health signals
6. 高价值 Ask 能生成新的 ingest 提案
7. 用户能在 `/app` 的 Ask-first 首屏看懂当前缺口与下一步动作

如果只做到第 4 步，产品仍然只是 llm-wiki 闭环。MVP 必须做到第 5 到第 7 步，才能体现 Inkvault 自己的产品命题。

## 5. 核心价值

- 对用户来说：不是多一个聊天工具，而是知道自己的知识系统是否可靠
- 对知识层来说：正式知识不只是可追溯，还要有健康状态
- 对 Ask 来说：问答不只是消费知识，而是测试知识
- 对 AI 协作来说：AI 不是作者，而是诊断者和提案生成器

## 6. MVP 范围内

### 主人入口与私有工作区

- 不公开的 `/login`
- 单主人登录
- `/app` Ask-first 私有研究工作区入口
- `/app/ask` 兼容问答别名，复用同一工作区页面
- 根路由根据登录态跳转 `/login` 或 `/app`

### 核心研究模块

- `问答 / Ask`
- `资料 / Raw`
- `审阅 / Ingest`
- `知识库 / Wiki`
- `判断摘要 / Briefing` 与最小 `Health` 信号展示

### 核心系统能力

- 导入网页、PDF、文本材料到 raw
- 为 raw 生成 AI 编译提案
- 人工 accept / reject 提案
- 将已接受提案写入 wiki
- 围绕 wiki/raw 发起 Ask
- 在 `/app` 首屏和问后阶段生成 briefing summary、knowledge gaps、next actions、suggested questions
- Ask 输出 knowledge gaps、writeback candidates、source coverage 等健康信号
- 将高价值 Ask 生成可审阅 ingest 提案

## 7. 最小知识健康信号

MVP 不做复杂评分系统，但必须有可见的健康信号。

第一代判断中枢只做两件事：暴露当前知识缺口、给出下一步动作。当前这些内容优先通过 Ask-first briefing 展示，而不是单独做一个 dashboard 首页。

第一批 health signals：

- `raw backlog`：已有 raw 但尚未进入有效提案或 wiki
- `review backlog`：待审阅提案数量与最近提案
- `open questions`：wiki 中仍未解决的问题
- `knowledge gaps`：Ask 暴露的证据缺口
- `writeback candidates`：Ask 回答中值得沉淀的候选内容

后续可以再扩展：

- unsupported claims
- stale claims
- duplicate topics
- conflicting claims

## 8. MVP 范围外

- 公开阅读产品线
- 发布模块
- plans / 任务执行系统
- 多人协作
- 通用第二大脑
- all-in-one AI 工具箱
- 完整知识健康评分
- 自动修改 wiki
- 真正长时自治的 agent 执行 loop

## 9. 核心流程

### 流程一：导入并形成候选知识

1. 主人进入 `资料`
2. 导入网页、PDF 或文本
3. 系统把材料保存为 raw markdown
4. 系统生成或等待生成 ingest 提案
5. health 显示 raw backlog 状态

### 流程二：审阅认知变更

1. 主人进入 `审阅`
2. 查看 AI 基于 raw 或 Ask 生成的提案
3. 判断这是新知识、补丁、开放问题还是低证据推测
4. 接受后写入 wiki，拒绝后不进入正式知识

### 流程三：Ask 作为知识体检

1. 主人进入 `/app` 或 `/app/ask`
2. 先看到当前缺什么证据，再围绕 wiki / raw 提问
3. 系统回答问题，并刷新问后判断，展示引用来源和知识缺口
4. 如果答案值得沉淀，系统提示 writeback candidate
5. 用户决定是否生成 ingest 提案

### 流程四：通过 Ask-first 工作区查看知识健康

1. 主人进入 `/app`
2. 在首屏 briefing 或问后判断面板里看到 raw backlog、review backlog、open questions、knowledge gaps
3. 从知识缺口和下一步动作跳转到对应页面或继续追问
4. 通过审阅或继续提问修正知识系统

## 10. 产品原则

- health first：MVP 必须体现知识健康，而不是只跑通问答
- claim first：正式知识应围绕 claims、sources、questions 组织
- review before write：AI 只能提案，不能静默写 wiki
- ask as diagnostic：Ask 同时给用户答案和给系统诊断
- vault first：长期真相始终落在 vault markdown
- single-owner simplicity：先把单人知识健康闭环做扎实

## 11. 成功标准

MVP 达成以下条件即可视为成功：

- 主人能通过 `/login` 进入系统
- `raw` 能稳定接收网页、PDF 和文本材料
- `ingest` 能稳定展示并处理 AI 提案
- `wiki` 能保存已确认的当前理解、claims、questions 和 sources
- `ask` 能围绕 wiki/raw 给出带来源的回答
- `/app` 首屏能展示 briefing summary、suggested questions、knowledge gaps 和 next actions
- Ask 能明确输出 knowledge gaps
- Ask 能标记或生成 writeback candidate
- 提问后判断面板会刷新为本轮 Ask 的判断结果
- 用户能看到至少三类知识健康信号
- 高价值 Ask 能进入 ingest，而不是停留在聊天记录里

## 12. 阶段边界

### MVP 完成标准

- 完成 `raw -> ingest -> wiki -> ask -> health -> ingest` 闭环
- 完成私有登录与研究工作区主路径
- 完成最小知识健康信号展示
- 完成 Ask 到 ingest 的可审阅回写

### MVP 之后的演进

- 第一优先：unsupported claims 与 claim-level provenance
- 第二优先：stale claims 与知识重审
- 第三优先：duplicate / conflicting topic 发现
- 第四优先：更强 retrieval、evidence ranking 与自动化导入
