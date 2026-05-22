# 产品路线图

## 目标

这份路线图描述 Inkvault 如何从当前私有 LLM Wiki MVP 继续演进。

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

## 阶段二：Ask-first 工作区

### 阶段目标

- 让 `/app` 更自然地成为研究问答入口
- 把对话历史、当前主题和工作路径组织得更顺
- 让 Ask 成为“发现知识缺口并触发沉淀”的主入口，而不只是更强的聊天界面

### 核心能力

- 对话历史侧栏
- 更清晰的 Ask 上下文延续
- 更顺手的 raw / ingest / wiki 跳转
- 渐进式加载研究上下文：先读 topic index / summary，再读 topic 详情，必要时再下钻 source 证据
- 在回答中显式暴露引用、知识缺口、可沉淀项与 writeback 入口

## 阶段三：检索与证据链增强

### 阶段目标

- 提升 Ask 的可追溯性与命中率
- 让检索从“拼接碎片”转向“候选过滤 + 整页精读 + 证据核验”

### 核心能力

- 更稳定的 retrieval chunks
- 更明确的知识缺口识别
- 更可靠的 source/topic 关联修复
- 更好的 web assist 边界控制
- 以 topic/page 为中心的分层读取顺序，而不是单纯扩大 chunk 注入
- 在 answer / writeback / ingest 之间保持 claim、source、conflict 的可回溯链路

## 阶段四：沉淀与自动化增强

### 阶段目标

- 让高价值研究结果更容易持续沉淀
- 为 Agent 补上可追踪、可评测、可门控的 operating layer，而不是直接走向自治

### 核心能力

- Ask 到 ingest 的更细粒度 writeback
- 周期性 re-index / 体检
- 更完整的 vault 运维与恢复工具
- 规则化的 lint / health-check：发现孤儿 topic、缺证据 claim、过时知识和待复核页面
- prompt / skill / workflow 级 trace，记录 Agent 在 ingest、ask、writeback 中的关键决策痕迹
- 基于 owner 接受 / 拒绝 / 修改后接受结果沉淀评测样本
- 对行为升级设置 promotion gate，只允许通过评测和门控的编译策略进入默认流程

## 长期方向

长期仍可以向更大的“个人主系统”扩展，但前提是：

- 当前私有研究闭环已经长期稳定
- 文档、数据边界和 AI 审阅机制没有继续漂移
- 知识层与行为层已经清晰分离：`raw/wiki` 承担长期真相，`ingest/ask/lint/writeback` 承担可审计的操作协议
- Agent 的能力增长建立在可控自进化上，而不是不可追踪的自治行为

在那之前，不恢复旧的 public / plans 产品叙事。
