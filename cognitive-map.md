# 认知地图

> 不记录「有什么功能」，记录「你对代码的理解深度」。诚实比完整重要——写「我不知道为什么这样写」比留空有用。

## 已理解（能给别人讲清楚）

### inkdesk_skill_sdk 包结构

- `contracts.py` 是 Skill 协议的单一真相源 — Pydantic 模型直接驱动 JSON Schema 生成和 CLI choices
- validation 分三层：structural（文件/目录是否齐全）→ semantic（跨文件 name/id/display_name 一致性 + SemVer + frontmatter 格式）→ safety（writePolicy + 绝对路径扫描 + bypass 检测）
- scaffolder 生成的 `openai.yaml` 根据 kind=router 自动决定 `allow_implicit_invocation: true`
- Registry 只读不执行 — `resolve()` 返回 `SkillMetadata`（含 validation result），`discover()` 递归找有 SKILL.md+contract.json 的目录
- Graph 从 registry 构建节点和边，DFS 检测 cycle，检查单一 router 约束

### Skill Package 约束

- 目录名 = contract.id = SKILL.md frontmatter name — 三者必须一致
- `display_name` 允许人类可读形式，通过 slugify 验证与 contract.id 的对应关系
- canonicalWiki 只有 denied/proposal-only，`"direct"` 直接报 SAFETY_WRITE_POLICY
- 绝对路径扫描覆盖 Windows(`C:\...`)、Unix(`/home/...`)、环境变量(`%APPDATA%`)

## 模糊区（大概知道，讲不清楚）

- behavioral contract cases 的具体执行方式 — 格式已定（`evals/skills/<id>/contract-cases.json`），但 4.1.4 不包含实际执行，runtime 由 4.2.1 的 Harness 决定

## 已理解（4.1.4 验收后更新）

### Fixture 覆盖

- valid fixtures: minimal-producer + minimal-reviewer + comprehensive-router，覆盖 3 种 kind
- invalid fixtures: 10 个，每种 lint 规则至少一个

### Schema 资产

- 4 份 schema 资产注册在 skill_assets.py，其中 contract JSON Schema 由 Pydantic 动态生成，drift test 确认与存储一致

## 黑盒区（完全不懂）

- 外部 Agent 加载 Skill package 后的实际执行行为 — 当前只保证 package 可校验，执行语义未定义
- behavioral contract cases 实际执行 — 格式已定，runtime 由 4.2.1 Harness 决定
