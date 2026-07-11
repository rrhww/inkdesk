# Inkdesk 团队 AI 研发能力平台设计

> 日期：2026-07-11
> 状态：已确认
> 方法论来源：`docs/references/AI研发自动化：Wiki知识库+技能包.md`
> 设计约束：本文从产品终局反推能力与边界，不受当前仓库实现约束。

## 1. 执行摘要

Inkdesk 是一个 **personal-first、team-native 的 AI 研发能力持续编译与运行平台**。

它将分散在代码、文档、成员经验、历史任务、测试、日志和线上结果中的隐性研发能力，持续编译为团队共享、可版本化、可评测、可治理的：

- LLM-Wiki：团队当前认可的长期知识与决策。
- Schema：Agent 维护知识和执行任务时必须遵守的规则。
- Skills：可复用的研发动作协议。
- Evaluations：证明知识、Skill、模型和工作流是否真正有效的任务集与门禁。
- Policies：权限、安全、治理和自治边界。
- Harness：根据任务、能力、证据和风险编排 Agent 与工具的运行时。

Inkdesk 的核心产品承诺不是“自动执行更多步骤”，而是：

> 第二次处理同类任务时，比第一次更快、更可靠、需要更少人工干预，并且能够解释改进来自哪条知识、哪个 Skill、哪项 Policy 或哪次 Evaluation。

团队级北极星是：

> 同类任务交给不同成员、不同 Agent、不同时间执行，仍能得到稳定、可验证、符合团队标准并产生真实结果的交付。

Inkdesk 的旗舰差异化能力是 **团队能力时光机（Capability Replay & Relay）**：把真实研发经历封装为可重放的证据单元，在能力变更前执行受控对照，并通过独立成员或 Agent 的无隐藏上下文接力，证明能力已经从一次成功转化为团队可迁移资产。

## 2. 与文章思想的对应

文章的主链路是：

```text
Sources -> LLM-Wiki -> Schema -> Skills -> Evaluation -> Harness
```

Inkdesk 保留这条主链路，并补充真实研发系统不可缺少的外部校准：

```text
Sources
  -> Knowledge Compiler
  -> Wiki / Schema / Skills / Policies
  -> Evaluation
  -> Harness
  -> Delivery
  -> Outcome Observation
  -> Knowledge / Capability Feedback
```

文章中的三个知识操作保持为一等能力：

- `Ingest`：在写入时完成融合、证据绑定、冲突判断和关联更新。
- `Query`：基于已编译知识为当前任务生成有界 Context Pack。
- `Lint`：持续检查结构、冲突、时效、来源、孤岛和知识缺口。

Inkdesk 不照搬文章中的具体企业工具，但必须保持其核心原则：团队共享、多 Agent 可用、Git 可版本化、Skill 有边界、Evaluation 驱动改进、Harness 管理门禁与回滚。

Capability Replay & Relay 将文章中的“评测驱动 Skill 优化”进一步产品化：真实 Run 先形成可审阅的经验候选，再转换为可重放评测，并通过独立执行者验证团队迁移，避免仅凭同一模型生成、评分和自我修改形成封闭反馈。

## 3. 产品目标与边界

### 3.1 产品目标

用户输入真实研发目标，例如 PRD、Bug、重构、事故或技术问题。Inkdesk 负责：

```text
理解目标
-> 编译相关上下文
-> 选择并编排能力
-> 调用 Agent 和工具执行
-> 收集产物与证据
-> 验证交付
-> 观察真实结果
-> 沉淀知识与能力反馈
```

用户主要承担两类高价值责任：

1. 提供真实目标、约束和结果预期。
2. 在高风险、证据不足、冲突或不可逆节点作出判断。

### 3.2 完成语义

每个 Run 最终必须成为：

- 有证据的交付；或
- 有证据的阻塞。

禁止把“模型声称完成”“工具执行结束”“测试部分通过”或“LLM Judge 高分”直接等同于任务完成。

### 3.3 明确不做

Inkdesk 不做：

- 普通聊天工具或通用 RAG。
- 笔记软件或 Obsidian 替代品。
- Jira、Slack、GitHub、CI 或完整 IDE 的替代品。
- 自建与 Claude Code、Codex 同类的通用编码 Agent。
- 无证据、无评测、无回滚路径的自治黑盒。
- 让 AI 静默修改 Canonical Wiki 或 Active Capability。
- 把页面数、Skill 数、Token 数或调用次数当作核心价值指标。

## 4. 四条复利闭环

### 4.1 Knowledge Loop

```text
Sources -> Ingest -> Review -> Canonical Wiki -> Query -> Deposit -> Ingest
```

将原始事实编译为团队当前认可、可追溯、可更新的长期理解。

### 4.2 Capability Loop

```text
真实 Run -> 失败与修正 -> Skill / Policy / Eval Candidate
-> Isolated Evaluation -> Promotion -> Active Capability
```

将重复动作和真实经验编译为团队能力。

### 4.3 Execution Loop

```text
Task -> Goal Contract -> Capability Resolution -> Harness
-> Agents / Tools -> Artifacts + Evidence -> Verification -> Delivery
```

将团队当前能力用于真实研发。

### 4.4 Outcome Loop

```text
Delivery -> Deploy / Release -> Observation Window
-> Technical / User / Business Outcome
-> Validated / Regressed -> Capability Feedback
```

真实结果是其他三个闭环的外部校准器，防止系统陷入 AI 生成、AI 评分、AI 自我强化的封闭循环。

Capability Replay & Relay 不是第五条闭环，而是贯穿四条闭环的验证层：Replay 检查能力变更会改善或破坏哪些历史任务，Relay 检查公开能力能否脱离原作者和原会话被他人复现。

## 5. Capability Space 与团队作用域

Inkdesk 围绕 `CapabilitySpace` 建模，而不是围绕单一用户 Workspace 建模。

```text
Organization Space
├── Shared Engineering Space
├── Domain Space
│   ├── Project Space
│   │   └── Personal Working Overlay
│   └── Project Space
└── Domain Space
```

### 5.1 四级作用域

- Personal：个人探索、草稿和实验性能力。
- Project：单个代码仓库的架构、约束、方案和测试能力。
- Domain：跨项目共享的业务知识、领域规则和诊断经验。
- Organization：全团队通用的工程、安全和治理能力。

### 5.2 所有能力对象的公共属性

每条知识、Skill、Evaluation 和 Policy 都必须包含：

- `scope`：作用域。
- `owner`：维护责任人。
- `authority`：reference、recommended 或 mandatory。
- `status`：按对象类型使用明确生命周期；Skill、Policy 和 Executor Profile 使用 draft、candidate、shadow、active、deprecated 或 rolled-back，知识对象使用 proposed、accepted、outdated、superseded 或 rejected。
- `version`：明确版本。
- `visibility`：读取范围。
- `permissions`：运行、修改、审阅和晋级权限。

### 5.3 有效上下文解析

Agent 执行任务时解析：

```text
组织强制策略
+ 领域知识与能力
+ 项目架构、代码和历史
+ 当前任务材料
+ 个人临时上下文
= Effective Capability Context
```

解析规则：

- 组织 mandatory Policy 不允许下层绕过。
- 最新代码与运行证据可以使旧 Wiki 进入 outdated，但不能静默删除历史判断。
- 领域知识提供业务语义，项目知识提供具体实现。
- 个人草稿不能覆盖团队正式知识。
- 冲突必须保留双方、时间、作用域和证据，不能简单覆盖。

## 6. 核心领域边界

| 领域 | 核心对象 | 职责 |
| --- | --- | --- |
| 身份与空间 | Organization、Member、CapabilitySpace、Role | 身份、作用域、继承和权限 |
| 知识编译 | Source、Claim、Decision、Constraint、Incident、OpenQuestion、WikiPage | 原始材料到团队当前理解 |
| 能力管理 | Schema、Skill、Policy、CapabilityVersion、ExecutorProfile | 版本化研发能力 |
| 任务运行 | Task、GoalContract、Run、PlanGraph、Invocation、Attempt、Artifact、Evidence | 动态执行与证据记录 |
| 评测晋级 | EvalCase、EvalSuite、EvalRun、Judgment、Comparison、Promotion | 能力准入与回归控制 |
| 结果观察 | ChangeSet、Deployment、ObservationWindow、OutcomeMetric、UserFeedback、Rollback | 真实效果与影响 |
| 治理审计 | Proposal、Review、Approval、AuditEvent | 变更、裁决和合规 |

### 6.1 知识单位

Wiki Page 是人类阅读投影。知识语义至少包括：

- `Claim`：可被证实或反驳的事实判断。
- `Decision`：选择、备选方案和理由。
- `Constraint`：业务、架构、安全或合规限制。
- `Procedure`：尚未形成正式 Skill 的可复用方法。
- `Incident`：现象、证据、根因、修复和预防措施。
- `OpenQuestion`：当前证据不足、尚不能确定的问题。

每个知识单元必须拥有来源、作用域、负责人、版本、有效时间和置信状态。

### 6.2 每个 Run 的四类产物

1. 交付产物：方案、代码、测试、诊断或发布结果。
2. 验证证据：diff、命令、日志、引用、工具记录和人工决定。
3. 知识增量：新增、修正、冲突或失效的知识候选。
4. 能力反馈：Skill 缺陷、Policy 调整或 Golden Task 候选。

每个 Run 都必须明确判断是否存在值得沉淀的增量；允许结论为“无长期增量”。

## 7. Knowledge Compiler

Knowledge Compiler 负责：

```text
Source Registration
-> Insight Extraction
-> Evidence Binding
-> Topic / Entity Routing
-> Conflict & Freshness Check
-> Change Proposal
-> Review
-> Canonical Write
-> Index / Link / Log Update
```

核心不变量：

- Sources 只读、可定位、可版本化。
- Canonical Wiki 只能通过 Proposal 与 Review 改变。
- 新来源不仅新建页面，还要更新所有受影响的概念、实体、决策、索引和失效信号。
- Query 的高价值结果必须能够回到 Deposit 和 Ingest。
- Lint 不只检查 Markdown 结构，还要检查证据、冲突、时效、作用域和孤立知识。

知识真相最终采用“Markdown 为 Canonical，Claim/Evidence 为派生索引”还是“结构化 Claim/Evidence 为 Canonical，Markdown 为投影”，属于待实验架构决策，不能在缺少真实摄入和冲突案例时提前锁定。

## 8. Dynamic Harness 与 Skill Contract

### 8.1 Harness 职责

Harness 是确定性导演，负责：

- 固定 Goal Contract。
- 解析 Effective Capability Context。
- 生成或选择 Plan Graph。
- 执行 Policy Preflight。
- 调度 Skill 和 Executor。
- 维护状态、预算、重试、人工节点和回滚。
- 根据 Evidence 执行 Verification Gate。

Harness 不负责生成技术方案、编写代码或判断业务事实。

### 8.2 参考生命周期

```text
Task
-> Goal Contract
-> Capability Resolution
-> Plan Graph
-> Policy Preflight
-> Skill / Executor
-> Artifacts + Evidence
-> Verification Gate
-> Next / Retry / Human Decision / Blocked
-> Delivery + Deposit
```

是否需要通用动态 DAG，还是先采用有限 Playbook，是待实验决策。第一阶段优先使用明确 Playbook，再从真实 Run 中提炼通用 Harness。

### 8.3 Skill Contract

每个 Skill 至少声明：

- Identity：ID、版本、Owner、Scope 和 Status。
- Purpose：解决什么问题、何时触发、何时不适用。
- Inputs：输入结构、来源和可信要求。
- Context：需要哪些知识、代码、历史 Run 和 Policy。
- Outputs：Artifact Schema、位置和审阅要求。
- Hard Gates：必须停止的前置条件。
- Capabilities：允许读取、写入、执行和联网的能力。
- Verification：如何证明结果正确。
- Failure Policy：重试、降级、切换执行器和阻塞语义。
- Transitions：后续 Skill 条件。
- Evaluation：晋级所需任务集和阈值。

Markdown 表达原则和判断框架；结构化 Contract 驱动执行、权限与验证。

### 8.4 Skill 类型

- Router：理解意图并选择能力。
- Producer：生成方案、代码、测试或知识候选。
- Reviewer：独立审查 Producer 产物。
- Executor：调用代码、测试、部署或数据工具。
- Diagnostic：从真实失败信号出发定位根因。
- Governor：运行健康检查、Evaluation 和 Promotion。

高风险产物必须由独立 Reviewer 验证，不能由同一生成上下文自我批准。

## 9. Executor、权限与失败语义

### 9.1 Executor Adapter

Claude Code、Codex、模型 API、CI、数据库和部署平台统一实现 Executor 协议。

输入：

```text
Pinned Context
+ Capability Manifest
+ Goal Contract
+ Permission Grant
+ Budget
```

输出：

```text
Artifacts
+ Evidence
+ Structured Events
+ Cost / Duration / Tool Calls
+ Final Status
```

每次执行必须固定代码、Wiki、Schema、Skill、Policy、模型、Provider、工具、预算和隔离环境版本。执行器不得继承未知全局配置或隐式权限。

### 9.2 能力权限

| 风险级别 | 示例 | 默认策略 |
| --- | --- | --- |
| R0 | 读取 Wiki、代码和日志 | 自动允许并记录 |
| R1 | 生成方案、报告和候选补丁 | 隔离空间自动执行 |
| R2 | 修改工作树、运行测试、创建分支 | 受 Policy 控制，可预授权 |
| R3 | 修改数据库、部署、发送外部消息 | 明确批准或组织级授权 |
| R4 | 删除生产数据、修改权限、读取密钥 | 默认拒绝，进入专门流程 |

授权必须携带作用域、对象、执行器、有效期和批准人。

### 9.3 失败状态

```text
missing_input
evidence_insufficient
conflict_detected
policy_denied
executor_failed
verification_failed
budget_exhausted
timed_out
cancelled
regression_detected
completed
```

规则：

- `policy_denied` 不允许自动重试。
- `verification_failed` 可以进入诊断或修复 Skill。
- `executor_failed` 可以切换执行器，但不能伪装成任务失败。
- `evidence_insufficient` 应生成 OpenQuestion 或请求补充材料。
- `regression_detected` 必须阻止 Capability Promotion。

### 9.4 重试与回滚

- 只有幂等操作或新的隔离 Attempt 才能自动重试。
- 每次重试保留原始失败证据。
- 代码通过丢弃工作树、反向提交或恢复基线回滚。
- Wiki 变更在 Proposal 阶段拒绝，不直接回滚 Canonical Wiki。
- 数据与部署操作必须事先声明补偿或回滚方案。
- 回滚不删除历史，只改变当前有效版本。

## 10. Evaluation 与 Promotion

Evaluation 是能力准入系统，不是后期报表。

### 10.1 评测对象

- Wiki / Context：准确性、完整性、新鲜度和任务提升。
- Skill：职责完成、边界、权限和稳定性。
- Executor：模型、Agent 和工具的质量、成本与可靠性。
- Harness Workflow：端到端交付、失败阻塞和恢复能力。

### 10.2 核心对象

- `EvalCase`：真实任务、输入、环境快照、期望证据和禁止行为。
- `EvalSuite`：覆盖正常、边界、失败和安全场景的一组任务。
- `EvalRun`：固定版本、隔离执行的评测。
- `Submission`：匿名化候选产物。
- `Judgment`：规则、测试、LLM Judge 和人工复核判断。
- `Comparison`：候选、Active 和裸模型基线的差异。
- `PromotionDecision`：作用域内的晋级结论。

`ExperienceCapsule` 是包含真实运行证据的上游对象，不自动等同于 `EvalCase`。它只有在完成脱敏、输入冻结、环境可重建性检查、期望证据和 Rubric 补充后，才能进入 Evaluation Suite，防止把偶然结果或污染数据直接固化为评测真相。

### 10.3 六层门禁

```text
1. 结构与安全
2. 行为正确性
3. 任务实用性
4. Replay 回归与统计可信度
5. Relay 可迁移性
6. Shadow / Canary 与真实 Outcome 观察
```

安全、正确性和数据完整性关键维度不能被综合平均分掩盖。

前五层决定候选是否有资格进入 Shadow；Shadow / Canary 决定是否可以成为 Active。真实 Outcome 不阻塞首次 Active，但决定能力能否获得或保持 `production-proven`，并可在回归时触发降级与回滚。

### 10.4 Golden Tasks 来源

- 真实 Run 的失败和阻塞。
- 用户纠正过的方案、代码或判断。
- 重复任务。
- 生产事故和回归。
- 新成员高频误解。
- 安全边界与编造案例。
- 能力升级可能影响的历史场景。

真实 Run 只生成候选。进入 Suite 前必须脱敏、固定输入、补充期望证据并明确 Rubric。

### 10.5 评分原则

```text
确定性验证 -> 规则与测试 -> LLM Judge -> 人工复核
```

LLM Judge 必须满足生成与评分隔离、版本匿名、重复评分、分歧复核、校准集监控和隐藏任务防过拟合。

候选版本同时与裸模型和当前 Active 版本比较。系统通过重复运行测量噪声基线 `sigma0`，只有超过可信阈值的变化才视为真实提升或回归。

### 10.6 晋级

```text
Draft -> Candidate -> Isolated Evaluation -> Shadow -> Active
                                      \-> Revise / Reject
Active -> Monitored -> Deprecated / Rolled Back
```

- Personal Draft 可在个人隔离环境试用。
- Project Active 需要项目 Suite 与 Owner 审批。
- Domain Active 需要跨项目评测与领域审批。
- Organization Active 需要安全评测、跨领域验证和组织治理审批。

自治资格绑定：

```text
Capability Version + Scope + Risk Level + Evaluation History + Executor
```

这里的 draft、candidate、shadow、active 是版本发布生命周期；后文的 lab-evaluated、team-validated、production-proven 是证据成熟度。两者相互关联，但不能合并为同一个状态字段。

## 11. Outcome & Impact

真实世界结果是最终真相。

### 11.1 Goal Contract

任务开始时必须定义：

- 为什么要做。
- 谁受到影响。
- 预期行为变化。
- 技术成功指标。
- 用户或业务成功指标。
- 允许的副作用。
- 观察时间。
- 失败和回滚条件。

对于文档、重构、内部工具和基础设施等没有直接业务指标的任务，必须声明代理指标或人工验收标准，并将 Outcome 标记为 proxy，避免把代理指标伪装成最终业务结果。

### 11.2 结果状态

```text
executed
-> technically_verified
-> delivered
-> observing
-> outcome_validated / regressed
```

### 11.3 结果对象

- `ChangeSet`：真实变更。
- `Deployment`：进入的环境与时间。
- `ObservationWindow`：观察期限。
- `ExpectedOutcome`：预期结果。
- `OutcomeMetric`：技术、用户和业务指标。
- `UserFeedback`：真实使用反馈。
- `Incident`：异常、影响和根因。
- `Rollback`：回退动作与结果。
- `ImpactAssessment`：收益、代价和副作用。

### 11.4 反馈动作

真实回归可以：

- 降低 Skill 自治等级。
- 标记相关 Claim 需要重审。
- 生成 Golden Task 候选。
- 回滚 Capability Version。
- 创建 Incident Knowledge。
- 重新评估技术决策。

能力成熟度区分：

```text
lab-evaluated -> team-validated -> production-proven
```

## 12. 团队能力时光机（Capability Replay & Relay）

团队能力时光机回答两个不同问题：

- `Replay`：如果今天使用候选能力重新处理过去的真实任务，会改善、回归还是无法判断？
- `Relay`：如果移除原作者、原 Agent 和原会话的隐性上下文，其他成员或 Agent 能否仅依赖团队发布的能力稳定完成任务？

它提供可审计的受控对照证据，不宣称仅靠离线回放就能证明现实世界因果。真实 Outcome 始终拥有最终裁决权。

### 12.1 Experience Capsule

满足条件的真实 Run 可以被封装为不可变的 `ExperienceCapsule`：

- `TaskSnapshot`：Goal Contract、需求、约束和验收标准。
- `SourceSnapshot`：代码提交、文档、配置和外部数据版本。
- `EnvironmentSnapshot`：Executor、工具、依赖、沙箱和预算。
- `CapabilityManifest`：Wiki、Claim、Schema、Skill、Policy、Harness 和 Executor 的精确版本。
- `ContextManifest`：进入与被舍弃的上下文、证据来源和 Token Budget。
- `ExecutionEvidence`：可观察的决策摘要、工具调用、产物、验证和人工干预。
- `OutcomeReference`：交付、部署、观察窗口和结果引用。
- `SecurityEnvelope`：数据分级、访问条件、脱敏和保留期限。

Capsule 不保存模型隐藏推理，也不复制原始密钥和不必要的敏感数据。系统保存可验证的输入、外部行为、决策摘要和证据引用；大对象优先使用内容哈希与受控引用。

```text
draft -> sealed -> replayable -> retired
```

`sealed` 后内容不可静默修改；发现缺失或错误时创建新版本并保留旧证据。只有依赖可获得、输入已冻结且副作用可隔离的 Capsule 才能标记为 `replayable`。

### 12.2 Counterfactual Replay

```text
Capability Diff
-> 依赖与影响分析
-> 选择相关 Experience Capsules
-> Active / Candidate / Baseline 隔离执行
-> 确定性验证 + 匿名评审
-> Replay Comparison
```

- 相同 Capsule 使用相同输入、环境约束、权限和预算。
- 外部非确定依赖使用固定夹具、录制回放或明确标记为不可比较。
- 生产写操作不得在 Replay 中直接执行，必须虚拟化、替换为沙箱连接器或阻塞。
- Candidate 同时对比当前 Active 与裸模型或最小 Prompt Baseline。
- 输出必须区分 `improved`、`regressed`、`inconclusive` 和 `not-comparable`。
- Comparison 展示受影响任务、关键差异、证据、成本、时延、安全风险、人工修正量和置信度。

系统可以根据 Claim、Skill、Policy、Harness 和工具依赖关系建议影响集合，但自动归因只作为假设。最终晋级依据来自对照结果、人工审阅和后续真实 Outcome。

### 12.3 Relay Verification

Relay 使用 Clean Room 方式验证团队迁移：

- 执行者必须不同于原作者；按风险选择不同成员、不同 Executor 或不同项目。
- 只允许访问任务声明、授权 Sources、Canonical Wiki 和待验证 Capability。
- 不允许访问原始聊天、个人笔记、未沉淀提示或原作者的临场补充。
- 必须记录额外求助、隐藏上下文请求、人工修正和失败原因。

核心指标包括：

- 任务正确性与证据完整性。
- 无提示完成率和人工干预次数。
- 跨成员、跨 Agent 和跨项目结果方差。
- 完成时间、运行成本和安全违规。
- 隐性上下文依赖率。

这些指标聚合为 `CapabilityTransferScore`，但它只能作为摘要视图，不能用综合分掩盖安全、正确性和数据完整性失败。Transfer Score 用于评估能力资产，不用于成员绩效排名或个人监控。

### 12.4 与 Promotion 的关系

采用风险分级门禁：

- Personal Draft：Replay 与 Relay 可选，用于个人试验。
- Project Active：必须执行相关 Capsule Replay，并在代表性任务上完成至少一次独立 Relay。
- Domain Active：必须覆盖多个项目或多个 Executor Profile 的 Relay。
- Organization Active：必须额外通过安全隔离、跨领域验证、Shadow / Canary 和 Outcome 观察。

关键回归必须阻塞晋级；确需例外时，由有权限的 Owner 提供书面风险接受、限定作用域和失效时间。生产 Outcome 回归可以反向撤销 Transfer 结论、降低自治等级并触发版本回滚。

### 12.5 产品表面

- Capsule View：查看一次真实 Run 被封装的输入、能力、证据和可重放性缺口。
- Replay Lab：选择 Capability Diff，运行 Active / Candidate / Baseline 对照。
- Impact View：展示能力变更可能影响的历史任务、项目和证据。
- Relay Challenge：为独立成员或 Agent 创建受控接力任务。
- Transfer Map：展示能力在成员、Agent、项目和作用域之间的可迁移性，不展示个人排行榜。

### 12.6 完成语义

一项能力只有同时满足以下条件，才能标记为 `team-validated`：

1. 代表性 Capsule 能在受控环境中重放。
2. 候选能力相对 Active 没有关键回归，并产生超过噪声的可解释收益。
3. 至少一个独立执行者在无隐藏上下文条件下完成 Relay。
4. 新增运行和治理成本低于预期收益。

`team-validated` 仍不等于 `production-proven`；后者必须由真实交付和 Outcome Observation 证明。

## 13. 产品形态

产品原则：

> Agent-native、Web-governed、Git-portable。

### 13.1 四类入口

- Agent：Codex、Claude Code、Cursor 或 IDE 中的日常主入口。
- Web：运行观察、证据审阅、冲突裁决、Evaluation 和治理控制室。
- Git：Wiki、Schema、Skills、Evals 和 Policies 的可移植文件入口。
- Automation：CI、定时任务、代码变更、事故和文档更新触发器。

普通任务不要求成员手动选择知识库、Skill 或模型。系统自动解析作用域与能力，只在无法可靠判断时暴露选择。

### 13.2 Web 信息架构

```text
/operations      当前运行、阻塞、审批和风险
/runs            个人与团队任务及证据链
/knowledge       Sources、Wiki、Claims、Decisions、Conflicts
/capabilities    Schema、Skills、Policies、Executors 与版本
/reviews         知识、能力、权限和冲突裁决
/evaluations     Golden Suites、对比、Shadow 与回归
/replay          Experience Capsules、Replay、Relay 与迁移证据
/health          知识、能力、运行和结果健康
/governance      Spaces、成员、角色、权限、审计和连接器
```

首页必须回答：哪些任务需要关注、哪些决定需要处理、哪些能力正在回归、哪些知识已经过期、团队最近获得了什么新能力。

### 13.3 角色

- Member：运行任务、使用能力、提交候选。
- Project / Domain Owner：维护 Canonical Knowledge 和作用域边界。
- Skill Maintainer：维护 Skill，不独立批准自己的高风险版本。
- Evaluator：维护 Suite、Rubric 和 Judge 校准，与 Skill Maintainer 职责分离。
- Organization Admin：管理身份、权限、执行器和连接器，不默认裁决业务事实。

### 13.4 Evidence Review

审阅界面必须展示：

- 变更原因。
- 使用的来源和能力版本。
- 语义变化。
- 冲突与影响范围。
- 已执行验证。
- 风险和系统建议。
- 接受、修改、拒绝的后果。

## 14. 系统架构与存储边界

目标架构采用 **模块化单体 + 耐久任务 Worker + 可替换连接器**。个人和小团队不承担微服务成本，但组织隔离、领域边界和异步协议从第一天成立。

### 14.1 模块

- Identity & Capability Spaces。
- Knowledge Compiler。
- Capability Registry。
- Run & Harness。
- Evaluation & Promotion。
- Experience Replay & Transfer。
- Outcome & Impact。
- Governance & Audit。
- Connector Gateway。

模块通过应用命令、领域接口和事件通信，不能依赖其他模块的内部数据库表。

### 14.2 存储

| 存储 | 保存内容 | 真相属性 |
| --- | --- | --- |
| Git + Markdown/JSON | Wiki、Schema、Skills、Evals、Policies | 团队能力 Canonical Truth 候选方案 |
| 关系数据库 | 身份、Spaces、Runs、Reviews、Promotions、Replay、Relay、权限 | 运行与治理真相 |
| 对象存储 | 原始材料、Capsules、日志、测试报告和大产物 | 不可变证据 |
| 搜索/向量索引 | Wiki、Sources、Artifacts 的派生索引 | 可删除重建 |
| Secret Manager | 密钥、数据库和部署凭证 | 独立安全真相 |

Git 作为团队能力 Canonical Truth 是待验证架构选择。若并发、权限和一致性成本过高，可调整为结构化存储为真相、Git 为版本镜像与导出。

### 14.3 耐久执行

- Job、Attempt 和状态写入耐久存储。
- Worker 使用 lease 和 heartbeat。
- 服务重启后恢复或重新领取任务。
- 命令携带 idempotency key。
- 外部副作用使用 Outbox、补偿动作或明确不可回滚标记。
- 重试生成新 Attempt，不覆盖失败历史。

个人模式可将 Worker 与主进程部署在一起，但使用相同协议。

## 15. 安全模型

- 所有运行对象归属 Organization 与 Capability Space。
- 团队模式支持 SSO，个人模式使用本地身份。
- RBAC 管职责，Capability Policy 管对象级行为。
- Sources、Knowledge 和 Artifacts 标记 public、internal、confidential 或 restricted。
- Context Compiler 根据执行器与 Provider 过滤数据。
- 代码和不可信脚本在独立 worktree、容器或沙箱执行。
- 网络默认拒绝或使用 allowlist。
- 密钥按任务临时注入，不进入 Prompt、日志、Git 或普通字段。
- 权限决定、工具调用、能力晋级和生产副作用全部审计。
- Capsule 在封装和 Relay 前执行数据最小化、脱敏、访问复核和保留期限检查。
- Relay 只衡量能力迁移，不得被转换为隐蔽的个人绩效、排名或劳动监控系统。

## 16. 部署形态

### 16.1 Local

- 单用户身份。
- 本地 Web、API 和 Worker。
- 本地或私有 Git Vault。
- 本地数据库和文件存储。

### 16.2 Team Self-hosted

- SSO。
- 共享 API 与 Worker Pool。
- PostgreSQL 与对象存储。
- GitHub / GitLab 集成。
- 共享 Capability Registry、Review 和 Evaluation。

### 16.3 Organization

- 高可用 Worker。
- 私有模型端点。
- KMS / Secret Manager。
- 审计导出、数据驻留和网络隔离。
- 跨领域 Capability Spaces。

三种形态使用同一领域模型，不形成三套产品代码。

## 17. 非功能要求与验证策略

### 17.1 非功能要求

- 可追溯：100% Run 具有 Capability Manifest。
- 可恢复：服务重启不能丢失 Run 或重复不可逆副作用。
- 可移植：能力文件不依赖特定模型或 Agent 平台。
- 可重建：搜索索引和派生视图可以恢复。
- 可隔离：不同 Space、Organization 和 Evaluation Sandbox 默认不能互读。
- 可解释：阻塞、失败、晋级和权限决定有机器原因码和人类说明。
- 可重放：Replay 必须说明冻结了什么、模拟了什么以及哪些部分不可比较。
- 可迁移验证：Relay 结果必须能区分能力缺失、执行器差异和隐藏上下文依赖。
- 可控成本：Run 和 Skill 支持 Token、时间、金额和工具预算。
- 上下文有界：Context Pack 满足 Token Budget，并说明舍弃信息。
- 可演进：能力契约和 API 版本化，不静默破坏 Active Workflow。

### 17.2 验证策略

- 领域单元测试：作用域、权限、状态机、结果状态和晋级规则。
- Contract Test：Executor、MCP 与连接器协议。
- 集成测试：Knowledge、Execution、Capability 和 Outcome 四条闭环。
- 安全测试：越权、密钥泄露、Prompt Injection、网络逃逸和危险工具。
- 恢复测试：Worker 中断、服务重启、重复消息和外部超时。
- Evaluation Regression：Active Capability 变更必须执行对应 Suite。
- Replay Test：固定 Capsule 重复执行，验证环境重建、非确定性标记和差异归因。
- Relay Test：验证 Clean Room、权限隔离、跨 Executor 可迁移性和反个人排名约束。
- 浏览器验收：审阅、冲突、权限和晋级真实可操作。

## 18. 关键假设台账

| 优先级 | 假设 | 最小验证 | 失败后的收缩方向 |
| --- | --- | --- | --- |
| P0 | Wiki 与 Skill 能提高真实任务质量 | Baseline / KB / KB+Skill 对照 | 收缩为上下文与证据服务 |
| P0 | 治理成本低于节省的研发成本 | 记录生成、审阅、修正和维护时间 | 减少自动 Proposal，只沉淀高价值结果 |
| P0 | Evaluation 能区分提升与随机波动 | 重复执行、双 Judge、人工盲评、噪声基线 | Evaluation 作为辅助，不自动晋级 |
| P0 | 存在明确高频入口 | 连续使用一个任务闭环 | 重新选择第一任务类型 |
| P0 | 真实结果可以被可靠关联到研发 Run | 绑定 Change、Deploy、指标和观察窗口 | Outcome 先保留人工确认 |
| P0 | 真实 Run 可以被充分封装并受控重放 | 将 10-20 个任务封装为 Capsule，重复执行并记录不可比较项 | 退化为证据快照和人工复现实验 |
| P0 | Relay 能衡量能力是否真正团队化 | 不同成员和 Agent 在 Clean Room 中执行代表性任务 | 仅作为诊断信号，不作为晋级硬门禁 |
| P1 | Markdown 可承担团队长期知识 | 新增、更新、冲突、失效和跨项目引用实验 | Claim/Evidence 为真相，Markdown 为投影 |
| P1 | Context Pack 比直接读仓库更有价值 | 比较定位时间、错误率和遗漏 | 只返回决策、约束和风险 |
| P1 | Skill 可跨成员和 Agent 稳定复用 | Replay + Relay 比较跨成员和 Executor 方差 | Skill 与 Executor Profile 绑定 |
| P1 | Git 与数据库边界可维护 | 并发修改、回滚、离线编辑和重建 | Git 作为镜像与导出 |
| P1 | 团队 Owner 模型能够运转 | 观察积压、审阅时间和无人维护比例 | 自动过期、按需审阅和轻量 Steward |
| P1 | 权限治理不会破坏体验 | 真实 Agent 最小权限实验 | 只自动执行只读和隔离操作 |
| P1 | 系统增强团队能力而不是只增强 Agent 产出 | 比较成员理解、独立判断、交接和责任归属 | 增加必要的人工推理、解释与交接节点 |
| P2 | Dynamic Harness 优于有限 Playbook | 与固定 Playbook 对照 | 保留有限 Playbook |
| P2 | 自我改进不会反馈污染 | 注入错误知识和过拟合 Skill | 只生成建议，不自动修改能力 |

## 19. 第一验证落点

首个闭环选择：

> PRD -> Context Pack -> 技术方案 -> 独立技术评审

原因：

- 高度依赖业务、架构和历史知识，能直接验证 Wiki 价值。
- 文章已有清晰 Skill 方法和评测维度。
- 产物容易匿名化、对照和人工判断。
- 可以验证团队共享、Skill 复用、证据引用和 Evaluation。
- 暂时避开代码执行、沙箱、权限和回滚的高复杂度。
- 通过后可自然扩展到 Coding 与 Testing。

### 19.1 最小实验

```text
一个真实项目
10-20 个历史或新增需求
2-3 个不同成员或 Agent
```

每个任务生成匿名结果：

- A：PRD + 代码仓库。
- B：PRD + 代码仓库 + Wiki。
- C：PRD + 代码仓库 + Wiki + Skills。

同时执行两类验证：

- Replay：将输入、代码版本、能力版本、预算和评测规则封装为 Capsule，重复运行代表性 A/B/C 任务。
- Relay：由非原作者成员或不同 Agent 在无原会话上下文条件下执行代表性 C 组任务。

统一评测：

- 需求覆盖度。
- 技术事实准确性。
- 代码与架构证据。
- 风险与回滚。
- 编造率。
- 审阅修正量。
- 生成和审阅总耗时。
- 不同成员和 Agent 的一致性。
- Capsule 封装成功率与可重放率。
- Replay 差异稳定性和不可比较比例。
- Capability Transfer Score 与隐性上下文依赖率。

只有 C 相比 A/B 获得稳定、可解释的提升，代表性任务能够重放并由独立执行者接力复现，而且新增治理成本可接受，才继续建设 Coding、Testing 和通用 Harness。

### 19.2 验证顺序

```text
1. 证明 Context + Skill 对技术方案有真实提升
2. 将首批真实任务封装为 Experience Capsules 并验证 Replay
3. 通过独立成员和 Agent 的 Relay 验证能力迁移
4. 证明团队审阅、封装和晋级成本可控
5. 固定 Knowledge / Skill / Evaluation / Replay 最小模型
6. 扩展到问题排查和测试修复
7. 接入受控 Coding Executor
8. 从真实重复流程中提炼 Harness
9. 接入 Outcome Observation
10. 最后扩展组织级部署与自治提升
```

Outcome 的目标和代理指标从第一个实验开始记录；第 9 步指自动连接部署、遥测、用户反馈和业务指标，而不是把结果思维推迟到后期。

## 20. 已确认与实验性决策

### 20.1 已确认

- 团队研发能力复利是产品终局。
- personal-first、team-native。
- 四级 Capability Space。
- Knowledge、Capability、Execution、Outcome 四条闭环。
- Canonical Knowledge 变更必须经过 Proposal 与 Review；团队默认的 Skill、Policy 和 Executor Profile 还必须经过 Evaluation 与 Promotion。
- Evaluation 是自治和团队默认能力的准入系统。
- Agent-native、Web-governed、Git-portable。
- 外部 Agent 是可替换 Executor。
- 真实结果是最终校准器。
- Capability Replay & Relay 是横跨四条闭环的旗舰验证机制，不是第五条闭环。
- 团队能力成立需要独立执行者的迁移证据，不能只依赖原作者或原 Agent 的成功运行。

### 20.2 实验性

- 通用 Dynamic Harness。
- Markdown 与 Claim Graph 的最终真相关系。
- Git 与数据库的最终职责边界。
- LLM Judge 的自动晋级权限。
- 完整组织角色分工。
- 多 Agent 统一执行协议。
- 自动 Outcome 归因。
- 外部系统和非确定环境的 Replay 保真度。
- Capability Transfer Score 的计算方式与晋级阈值。
- 能力变更与结果差异的自动因果归因。

实验性选择在验证前不得演化为不可逆基础设施承诺。

## 21. 最终成功标准

Inkdesk 成功时，应满足：

- 一个成员解决过的问题能够成为团队可复用能力。
- 不同成员和 Agent 使用相同能力时结果具有一致性。
- 新知识和 Skill 的收益可以通过真实任务证明。
- 任一重要能力变更都能说明影响了哪些历史任务、产生了什么收益或回归以及证据是否可信。
- 另一名成员或另一种 Agent 不依赖原会话和私有提示，也能复现代表性任务结果。
- 团队治理成本低于节省的研发成本。
- 失败和生产回归会反向修正知识、评测和自治等级。
- 系统能够说明每次交付用了什么、为什么放行、实际产生了什么结果。
- 系统越用越可靠，而不是只积累更多文档、Prompt 和运行记录。
