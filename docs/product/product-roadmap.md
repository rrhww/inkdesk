# 产品路线图

## 目标

这份路线图说明 Inkvault 如何从当前 MVP 演进为长期可用的个人知识健康系统。

## 阶段一：知识健康 MVP

### 阶段目标

- 建立私有登录入口
- 建立 `raw -> ingest -> wiki -> ask -> health -> ingest` 主闭环
- 让 Ask 产生知识健康信号
- 让用户看到最小知识健康状态

### 核心能力

- 隐藏登录入口
- 原始材料导入
- AI 提案审阅
- wiki 当前理解沉淀
- 基于 wiki/raw 的 Ask
- Ask knowledge gaps
- Ask writeback candidates
- raw backlog / review backlog / open questions 最小展示

### 完成标志

- 用户能完成一轮从导入材料到知识沉淀再到继续追问的完整闭环
- Ask 不只返回答案，也能暴露知识缺口和沉淀机会
- 用户能看到系统当前有哪些知识健康问题

## 阶段二：Claim-first Knowledge

### 阶段目标

- 把 wiki 从页面级沉淀升级为 claim 级知识管理

### 核心能力

- claim-level source linkage
- unsupported claims
- claim confidence / evidence strength
- claim 使用记录
- Ask 回答引用到 claim 而不只是 wiki 页面

### 进入条件

- MVP 已经稳定生成 wiki、claims 和 Ask citations
- 用户能理解并使用最小 health signals

## 阶段三：知识重审与老化

### 阶段目标

- 让系统主动发现哪些知识需要被重新确认

### 核心能力

- stale claims
- stale wiki pages
- last verified at
- new raw material impact detection
- re-review proposals

## 阶段四：冲突、重复与主题治理

### 阶段目标

- 让系统能发现知识结构本身的问题

### 核心能力

- duplicate topics
- conflicting claims
- orphan raw sources
- unresolved long-running questions
- topic merge / split suggestions

## 阶段五：主动研究协作

### 阶段目标

- 让系统从被动问答升级为主动协助维护知识质量

### 核心能力

- 定期知识健康回顾
- 自动提醒待审阅项
- 针对 open questions 推荐补料方向
- 受控 web assist
- 研究回顾报告

### 推荐策略

- 优先自动发现问题，不自动修改正式知识
- 所有认知变更仍然进入审阅闸门

## 演进原则

- 先做知识健康，再做功能广度
- 先做 claim 级治理，再做复杂自动化
- 先让系统暴露问题，再让系统建议解决方案
- 所有增强能力都必须服从 vault-first 和 review-before-write

