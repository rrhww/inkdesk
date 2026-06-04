# Inkdesk 产品愿景

## 当前定论

Inkdesk 的核心不是问答，也不是 wiki，而是一个面向 AI Agent 的个人知识底座。

用户在 AI 对话中只需要负责两件事：

1. 提问。
2. 判断某个回答是否值得沉淀。

一旦用户按下“沉淀这次回答”，后续的知识提取、证据绑定、topic 路由、冲突检测、wiki patch、质量门控，都由主 Agent 触发专项子 Agent 在后台完成。

这意味着 Inkdesk 的产品主形态不是：

```text
raw -> ingest -> wiki -> ask -> health -> ingest
```

而是用户可感知的：

```text
Ask -> 沉淀 -> 知识变得更干净
```

内部仍然保留 `raw / ingest / wiki / ask / health` 的工程闭环，但它们是系统协议，不是用户每天必须理解的产品路径。

## 一句话定义

Inkdesk 是一个 Agent Knowledge Runtime：把 AI 回答和外部 Agent 工作过程里的高价值判断，沉淀成可追溯、可审阅、可修正、可复用的长期知识。

它既可以作为独立私有研究工作台使用，也可以作为 Claude Code、Codex、Cursor 等外部 Agent 的通用知识底座。

## 核心洞察

AI 时代最大的知识问题，不是没有答案，而是答案太多、太像知识、太容易污染长期判断。

传统知识工具解决的是：

- 资料在哪里
- 笔记怎么写
- 内容怎么搜索

AI 时代的新问题是：

- 哪些回答值得沉淀
- 哪些结论证据不足
- 哪些理解已经过时
- 哪些主题重复或冲突
- 哪些材料从未被真正消化
- 哪些知识被频繁使用但没有正式确认

所以，Inkdesk 不应该只做“基于资料回答”，而应该做：

**回答之后的知识沉淀。**

用户体验必须足够轻：不要让用户每天处理 claim、health、lint、ingest 队列。用户只负责判断“这次回答值得留下吗”。系统负责处理“留下什么、放到哪里、是否冲突、如何补证、如何更新长期知识”。

## 新产品命题

每一次 AI 回答，都应该给用户一个沉淀入口：

- 用户认为有价值，就点击“沉淀这次回答”。
- 主 Agent 接管当前问题、回答、引用、上下文和用户选择。
- 专项子 Agent 提取可沉淀 insight，绑定证据，判断新建 topic 或 patch 旧 topic。
- 质量门控通过后写入长期知识；不通过时只生成轻量确认卡片。
- 只有冲突、低证据、高风险覆盖旧判断时才打断用户。

这意味着 Ask 不是一个聊天功能，而是沉淀入口。用户不需要管理知识系统，知识系统应该在用户确认后自己完成整理。

## 外部 Agent 底座

Inkdesk 的长期产品目标，是成为外部 Agent 的知识底座。

Claude Code、Codex、Cursor 等 Agent 可以通过 MCP、CLI 或项目级 Skill 接入 Inkdesk：

- 任务开始前：调用 Inkdesk 获取相关长期知识和历史判断。
- 任务进行中：查询某个 topic、decision、open question 或 source。
- 任务结束后：把回答、方案、复盘或用户选中的片段提交给 Inkdesk 沉淀。

外部 Agent 不需要理解 Inkdesk 内部的 claim、review、health、vault patch。它们只需要两类能力：

```text
context_pack(task) -> 返回短上下文包
deposit(answer/context) -> 后台沉淀长期知识
```

这让 Inkdesk 从“自己的知识 App”升级为“所有 Agent 都能调用的长期记忆层”。

## 新范式

### 1. 用户动作不是整理，而是沉淀

用户不应该被迫理解复杂的知识治理流程。

主路径必须保持：

```text
问 -> 得到答案 -> 沉淀
```

`raw / ingest / wiki / claim / health / lint` 都是后台协议。只有当系统无法安全自动处理时，才用一张轻量确认卡片请用户裁决。

### 2. 知识不是笔记，而是有状态的 claim

文档仍然重要，但文档不是最小知识单位。

Inkdesk 真正关心的是 claim：

- 它说了什么
- 它来自哪里
- 它被哪些 Ask 调用过
- 它有多新
- 它有没有冲突
- 它是否仍然值得相信

wiki 页面只是 claim 的阅读界面，不是知识系统的终点。

### 3. Ask 不是回答器，而是沉淀运行时

一次 Ask 应该输出两种结果：

- 给用户看的回答
- 给沉淀系统看的上下文包

上下文包至少包括：

- 本次回答依赖了哪些 wiki / raw
- 证据是否足够
- 新增了哪些候选 claim
- 触发了哪些 knowledge gap
- 是否建议生成 ingest 提案
- 是否发现旧理解需要重审

### 4. Ingest 不是用户主路径，而是认知变更管理

Ingest 不应该成为用户每天必须处理的沉重队列。

它是沉淀按钮背后的后台管理层，负责判断：

- 这是不是新知识
- 这是不是旧知识补丁
- 这是不是冲突
- 这是不是低证据推测
- 这是不是重复 topic
- 这是不是应该暂存为 open question

### 5. Wiki 不是仓库，而是当前理解的可读投影

wiki 保存的是用户确认过的当前理解，但它必须暴露自己的状态。

一个 wiki 页面应该能回答：

- 当前我们相信什么
- 依据是什么
- 哪些地方不确定
- 最近一次被验证是什么时候
- 哪些 Ask 最近调用过它
- 哪些 claim 需要重审

### 6. Knowledge Health 应该后台运行，必要时轻量打断

知识健康不能消失，但也不能压到用户主路径上。

它应该后台运行，并在以下情况才打断用户：

- 新沉淀结论和旧判断冲突。
- 新沉淀内容证据不足但会影响核心判断。
- 系统需要用户在“覆盖旧判断 / 保留旧判断 / 合并表达”之间做选择。

## 产品定位

Inkdesk 不是：

- AI 聊天工具
- 普通 RAG 知识库
- Obsidian 替代品
- Notion 式工作台
- llm-wiki 的 UI 外壳
- 需要用户手工维护 claim 的知识治理后台

Inkdesk 是：

- 面向 AI Agent 的个人知识底座
- 一个“回答后沉淀”的产品形态
- 一个让外部 Agent 能取用和回写长期知识的 runtime
- 一个把复杂知识治理藏在后台、只把必要裁决交给用户的系统

## 核心闭环

用户感知闭环：

```text
Ask -> 沉淀 -> 知识变得更干净
```

内部工程闭环：

```text
raw -> ingest -> wiki -> ask -> health -> ingest
```

- `raw` 提供证据
- `ingest` 管理认知变更
- `wiki` 展示已确认理解
- `ask` 调用并测试知识
- `health` 暴露缺口、老化、冲突和未沉淀价值
- 新的 health 信号再进入 ingest

用户不需要直接操作这条内部闭环，但系统必须保留它，确保沉淀不是把聊天记录随手塞进笔记，而是进入可追溯、可审阅、可修正的长期知识体系。

## 创新重点

### Answer-level Deposit

每个回答都可以沉淀。沉淀按钮是产品主操作，不是隐藏在二级页面里的 writeback 功能。

### Specialized Sub-agent Pipeline

沉淀由主 Agent 编排专项子 Agent 完成：Insight Extractor、Evidence Binder、Topic Router、Conflict Checker、Patch Writer、Quality Gate。

用户不看这条流水线，但它决定沉淀质量。

### Claim-first Knowledge

知识原子从 page 下沉到 claim。系统关心每条 claim 的来源、状态、使用记录和健康度。

### Inkdesk as Agent Knowledge Runtime

Inkdesk 通过 MCP / CLI / Skill 接入外部 Agent，为 Claude Code、Codex、Cursor 等工具提供长期知识上下文和沉淀接口。

### Ingest as Cognitive Change Control

Ingest 是后台认知变更管理层，负责处理新增、补丁、冲突、弱证据和开放问题。

### Knowledge Health as Background Engine

知识健康不是复杂报表，而是后台质量引擎。它告诉系统哪些内容可以自动沉淀，哪些需要用户裁决。

## 第一批用户

第一批用户不是泛知识管理用户，而是有高频专业判断需求的人。

典型用户是：

- 正在学习和研究前沿技术的人
- 长期分析某个行业或产品方向的人
- 有一批专业资料，希望 AI 真正围绕它们工作的个人
- 高频使用 Claude Code、Codex、Cursor 等 Agent，希望 Agent 有长期上下文的人
- 想展示 agent 开发能力和 AI 产品理解的 builder

他们的共同点不是“爱记笔记”，而是：

**他们需要让自己的专业判断和 Agent 工作上下文越来越可靠。**

## 成功标准

Inkdesk 的成功不看“能不能问”，而看：

- 每个回答是否都能自然触发沉淀动作
- 用户是否能在不理解后台协议的情况下留下高价值判断
- 高价值回答是否能自动进入长期知识体系
- 外部 Agent 是否能获取相关知识并回写沉淀
- wiki 是否能暴露 claim、证据和未解问题
- 系统是否越用越清晰，而不是越用越脏

## 产品原则

- 先做回答沉淀，再做功能广度
- 先把用户主路径压到最短，再扩展后台治理
- 先把 claim 管好，再扩展页面和自动化
- AI 可以提出认知变更，但不能直接污染正式知识
- 外部 Agent 接入时只暴露简单协议：取上下文、沉淀结果
- llm-wiki 是底层机制，不是产品终点

