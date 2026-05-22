# 产品路线图

## 目标

这份路线图描述 Inkvault 如何从当前私有研究闭环，演进成一个“回答后沉淀”的 Agent Knowledge Runtime。

用户主路径保持极简：

```text
Ask -> 沉淀
```

系统内部继续维护：

```text
raw -> ingest -> wiki -> ask -> health -> ingest
```

外部 Agent 通过 MCP / CLI / Skill 接入同一知识底座：

```text
context_pack -> agent work -> deposit
```

## 阶段一：稳定当前研究闭环

### 阶段目标

- 把 `raw -> ingest -> wiki -> ask` 主路径做稳
- 清理旧产品残留
- 保证本地全栈与文档一致

### 核心能力

- owner 登录
- raw 导入
- ingest 审阅
- wiki 页面沉淀
- Ask 引用与 writeback

### 完成标志

- 闭环可本地跑通
- 代码、测试和文档不再混入旧 public / plans / note editor 语义

### 当前进度

截至 2026-05-22：

- [x] owner 登录、本地 `/app` 工作区、raw、ingest、wiki、ask
- [x] Ask writeback、claim 证据状态、usage、stale/conflict 信号
- [x] 本地 Docker 栈：Next.js、FastAPI、PostgreSQL + pgvector
- [x] 后端 `python -m pytest` 与前端 `npm run typecheck`
- [x] 阶段一主体成立，产品重点转向“回答沉淀”体验
- [ ] 每个回答固定提供“沉淀这次回答”
- [ ] 支持完整回答与选中片段两种沉淀入口
- [ ] 后台 deposit orchestration 与专项子 Agent 流水线
- [ ] MCP / CLI / Skill 接入外部 Agent

## 阶段二：回答沉淀主形态

### 阶段目标

- 让每个回答都提供“沉淀这次回答”的主操作
- 用户只决定是否沉淀，不负责后续知识整理逻辑
- 让 Ask 成为长期知识增长入口，而不只是更强的聊天界面

### 核心能力

- 对话历史侧栏
- 更清晰的 Ask 上下文延续
- 更顺手的 raw / ingest / wiki 跳转
- 渐进式加载研究上下文：先读 topic index / summary，再读 topic 详情，必要时再下钻 source 证据
- 每个回答卡片固定提供“沉淀这次回答”
- 支持“沉淀选中内容”
- 沉淀后给出轻量反馈：已沉淀、需要确认、暂不适合沉淀
- 冲突、低证据、高风险覆盖旧判断时才打断用户

### 完成标志

- 用户能从任意 Ask 回答触发沉淀。
- 沉淀动作能生成新 topic、topic patch、open question 或冲突裁决。
- 用户不需要进入复杂 ingest/health 页面也能完成主路径。

## 阶段三：专项子 Agent 沉淀流水线

### 阶段目标

- 把沉淀按钮背后的逻辑拆成可追踪、可测试、可替换的专项子 Agent
- 让系统自动完成“留下什么、放到哪里、是否冲突、怎么补证”

### 核心能力

- Deposit Orchestrator：接收沉淀请求并编排子 Agent
- Insight Extractor：从回答中提取可沉淀判断
- Evidence Binder：绑定 raw / wiki / web source 证据
- Topic Router：判断新建 topic、patch 旧 topic、open question
- Conflict Checker：检查和旧 claim 是否冲突
- Patch Writer：生成 vault/wiki patch
- Quality Gate：判断自动写入、进入审阅、还是要求用户裁决
- Trace：记录每一步输入输出，方便后续评测和修正

### 完成标志

- 同一个沉淀请求可以复现完整决策链。
- 质量门控能阻止无证据、重复、明显冲突的沉淀直接进入 wiki。
- 子 Agent 失败时不会污染正式知识。

## 阶段四：外部 Agent 知识底座

### 阶段目标

- 让 Claude Code、Codex、Cursor 等外部 Agent 接入 Inkvault
- 为外部 Agent 提供“任务前取上下文、任务后沉淀结果”的通用接口

### 核心能力

- `inkvault context` CLI：根据 task/repo/files 返回短上下文包
- `inkvault deposit` CLI：接收回答、片段、引用和上下文，触发后台沉淀
- `inkvault-mcp`：暴露 `context_pack`、`deposit_answer`、`search`、`open_questions` 等工具
- Codex Skill / AGENTS.md 接入说明
- Claude Code MCP / slash command 接入说明
- 外部 Agent 不直接写 wiki，只调用 Inkvault deposit

### 完成标志

- Claude Code 或 Codex 能在任务前调用 Inkvault 获取上下文。
- 外部 Agent 的一段回答可以被提交给 Inkvault 沉淀。
- 外部接入复用同一套后台沉淀流水线。

## 阶段五：评测、健康与自进化

### 阶段目标

- 让沉淀策略、检索策略、topic 路由策略可以被评测和升级
- 让知识库越用越干净，而不是越自动越脏

### 核心能力

- 周期性 re-index / 体检
- 规则化 lint / health-check：发现孤儿 topic、缺证据 claim、过时知识和待复核页面
- 基于 owner 接受 / 拒绝 / 修改后接受结果沉淀评测样本
- 对编译策略、沉淀策略和 MCP 输出设置 promotion gate
- prompt / skill / workflow 级 trace，记录 Agent 在 ask、deposit、writeback 中的关键决策痕迹

## 长期方向

长期仍可以向更大的“个人主系统”扩展，但前提是：

- 当前私有研究闭环已经长期稳定
- 回答沉淀主路径已经足够顺滑
- 外部 Agent 接入不破坏用户体验和知识边界
- 文档、数据边界和 AI 审阅机制没有继续漂移
- 知识层与行为层已经清晰分离：`raw/wiki` 承担长期真相，`ingest/ask/lint/writeback` 承担可审计的操作协议
- Agent 的能力增长建立在可控自进化上，而不是不可追踪的自治行为

在那之前，不恢复旧的 public / plans 产品叙事。
