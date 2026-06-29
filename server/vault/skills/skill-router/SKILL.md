---
name: skill-router
description: Inkdesk 唯一宽入口——根据用户意图路由到正确的领域 Skill。当用户描述了研发意图或任务目标时触发。不应在用户已经指定了具体 Skill 名称的显式调用场景下拦截。
---

# skill-router

## 核心目标与边界

接收宽泛的用户意图，判断属于知识管理还是研发自动化领域，路由到最匹配的领域 Skill：

- **做**：解析意图、判断领域、选择最窄匹配的 Skill、传递上下文
- **不做**：执行任何领域 Skill 的实际工作；替代领域 Skill 做决策

## Hard Gates

- `required_input`（user_intent）：用户意图不得为空
- `vault_initialized`：KB 未初始化时返回 blocked

## 主流程

1. **意图解析** — 从用户输入中提取：目标动作（查询/修改/创建/修复/评审）、领域对象（wiki/代码/方案/测试）
2. **领域判断** — 知识管理领域（涉及 wiki 查询/摄入/健康/提取）vs 研发自动化领域（涉及方案/代码/测试/排查）
3. **候选匹配** — 在目标领域内筛选匹配的 Skill，按范围最窄优先
4. **前置条件检查** — 确认候选 Skill 的 Hard Gates 可满足（如 vault 已初始化、必需输入存在）
5. **路由决策** — 唯一匹配时直接路由；多候选时列出差异请用户选择
6. **上下文传递** — 将用户意图、当前 Dev Run 状态和相关上下文打包传给目标 Skill

## 关键决策点

- 用户意图跨两个领域时：选主导领域（如"修完 bug 沉淀经验"→ 研发为主，末尾衔接知识管理）
- 所有候选 Skill 前置条件都不满足时：报告阻塞原因，推荐先解决哪个
- 用户明确指定 Skill 名称时不拦截，直接放行

## 路由优先级

1. 用户当前明确指令
2. 项目 AGENTS.md / Schema / 安全约束
3. Dev Run 当前状态与已批准门禁
4. skill-router 的类型与链路选择
5. 当前领域 Skill
6. 默认风格偏好

## 需要读取的资源

- `references/`：路由决策树（routing-tree），领域 Skill 摘要（domain-skills-summary）

## 输出规格与验证

- 输出：路由决策（目标 Skill + 理由 + 传递的上下文包）
- 验证：路由理由必须可追溯到用户意图中的具体关键词或信号

## 下游衔接

- → 知识管理链：ingest-source / answer-from-wiki / deposit-answer / patch-wiki-page / run-wiki-health / extract-insight
- → 研发自动化链：tech-solution / tech-review / coding / test-prep / test-fix / problem-solve
