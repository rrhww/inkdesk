# Inkdesk MVP 产品需求文档

## 1. 产品背景

Inkdesk 当前不是一个公开发布平台，也不是一个带完整计划系统的超级工作台。

它已经从“私有 LLM Wiki”继续收敛成一个更明确的产品：

- 单人私有
- vault-first
- Ask-first
- 每个回答都能一键沉淀
- 可作为外部 Agent 的通用知识底座

当前最重要的问题不是“展示给访客看什么”，也不是“让用户手工维护复杂知识库”，而是：

**如何让用户只管提问和沉淀，把后续知识整理交给后台 Agent。**

## 2. 产品定位

Inkdesk 当前 MVP 的正式定位是：

- 一个以 `Ask -> 沉淀` 为用户主路径、以 `raw -> ingest -> wiki -> ask` 为内部闭环的 Agent Knowledge Runtime

它的核心不是“直接让 AI 写最终答案”，而是：

1. 用户围绕已有资料和知识发起 Ask
2. 系统给出带引用的回答
3. 用户点击“沉淀这次回答”
4. 主 Agent 触发专项子 Agent 完成提取、证据绑定、topic 路由、冲突检查和 wiki patch
5. 长期知识继续服务后续 Ask 和外部 Agent

## 3. 目标用户

### 主要用户

- owner，也就是你自己
- 使用目标：把网页、PDF、旧笔记、研究问答和外部 Agent 产出的高价值回答沉淀进一个长期可追溯的私人知识系统

### 扩展使用者

- Claude Code、Codex、Cursor 等外部 Agent
- 使用目标：在任务前获取 Inkdesk 的长期知识上下文，在任务后把值得保留的结论交给 Inkdesk 沉淀

### 当前非目标用户

- 公开访客
- 协作者
- 团队成员

当前产品没有公开阅读面，也没有多人协作角色。

## 4. MVP 目标

MVP 需要跑通两条链路。

### 链路一：私有研究闭环

1. owner 通过 `/login` 登录
2. 原始材料进入 `raw/`
3. 系统生成 `ingest` 审阅提案
4. owner 接受后沉淀到 `wiki/`
5. owner 在 `ask` 上基于已有 wiki 和 raw 继续研究

### 链路二：回答沉淀闭环

1. owner 在 Ask 中得到回答
2. 每个回答都提供“沉淀这次回答”入口
3. 沉淀动作触发后台专项子 Agent
4. 系统自动生成新 topic、patch 旧 topic、open question 或轻量冲突裁决
5. 通过质量门控的内容进入长期 wiki

第一条链路已经基本成立；第二条链路是下一阶段 MVP 的主目标。

## 5. 核心价值

- 对 owner：把“资料收集、知识沉淀、研究追问”放进同一条闭环
- 对系统：让 AI 参与研究，但不允许它静默污染长期知识
- 对用户体验：把复杂的 claim / ingest / health 逻辑藏到后台，用户只做“沉淀 / 不沉淀”判断
- 对外部 Agent：提供统一的长期上下文与沉淀接口

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
- `deposit`：回答沉淀入口，当前先复用 Ask writeback，后续升级为专项子 Agent 流水线

### 支撑能力

- Vault Markdown 持久化
- PostgreSQL 索引与队列
- owner session
- 本地全栈验收与自动化测试
- MCP / CLI 接入设计文档

## 7. MVP 范围外

- 公开文章与公开首页
- plans 主路径
- search 主路径
- settings 主路径
- 多人协作
- 自治 Agent 执行系统
- 面向公众的营销站
- 让用户手动管理完整 claim 生命周期
- 在第一阶段实现完整 MCP server 生产化

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
4. 如答案值得沉淀，owner 点击“沉淀这次回答”

### 流程五：后台沉淀

1. 主 Agent 接收当前问题、回答、引用、上下文和用户沉淀意图
2. Insight Extractor 提取可沉淀判断
3. Evidence Binder 绑定 raw / wiki / web source 证据
4. Topic Router 决定新建 topic、patch 旧 topic 或生成 open question
5. Conflict Checker 检查和旧 claim 的冲突
6. Patch Writer 生成 vault/wiki patch
7. Quality Gate 判断是否自动写入，或生成轻量用户裁决卡片

### 流程六：外部 Agent 接入

1. Claude Code、Codex 或 Cursor 通过 MCP / CLI 请求 Inkdesk context pack
2. 外部 Agent 使用相关长期知识完成任务
3. 用户要求沉淀时，外部 Agent 调用 Inkdesk deposit
4. Inkdesk 复用后台沉淀流水线，不要求外部 Agent 理解内部知识协议

## 9. 产品原则

- Vault 为底：长期真相必须能回到 Markdown 文件
- 审阅优先：AI 只能提议，不能静默写正式知识
- 私有优先：先把 owner 的闭环做稳，再考虑对外表达
- 沉淀优先：Ask 的关键不是聊天体验，而是回答是否能进入长期知识
- 低打扰优先：用户只看到“沉淀”和必要冲突裁决，后台治理不暴露成日常负担
- 低复杂度优先：MVP 只做当前主路径，不恢复旧模块叙事

## 10. 成功标准

满足以下条件即可认为 MVP 可用：

- `/login` 可登录
- `/app/raw` 可导入并读取来源
- `/app/ingest` 可接受 / 拒绝提案
- `/app/wiki` 与 `/app/wiki/[id]` 可稳定展示知识页和来源
- `/app/ask` 可返回带引用的回答
- Ask writeback 只生成提案，不会直接改写 wiki
- 每个回答都能触发沉淀动作
- 沉淀动作能生成可审阅的 topic create / topic patch / open question
- 外部 Agent 接入方案在文档中明确，后续可落地为 MCP / CLI

## 11. 阶段边界

### 当前阶段进度

- 本地全栈闭环已成立
- owner 登录、raw、ingest、wiki、ask 已有实现
- Ask writeback 已有后端和前端入口雏形
- claim 证据状态、使用次数、过期和冲突信号已有实现
- 本地 Docker 栈、后端 pytest、前端 typecheck 已验证
- 旧 public / plans / note editor 方向已退出主规范

### 下一阶段优先项

- 回答卡片上的“沉淀这次回答”成为主操作
- 后台专项子 Agent 沉淀流水线
- MCP / CLI 接入外部 Agent
- 更稳定的 retrieval 与证据链
- 更清晰的 source/topic/claim 演化流程
