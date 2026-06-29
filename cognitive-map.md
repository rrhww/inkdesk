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

### 4.1.4 验收

- valid fixtures: minimal-producer + minimal-reviewer + comprehensive-router
- invalid fixtures: 10 个，每种 lint 规则至少一个
- 4 份 schema 资产注册在 skill_assets.py，contract JSON Schema 由 Pydantic 动态生成，drift test 确认一致

### 4.2.1 首批 Skill

- 13 个 Skill 全部 scaffold 并填充完整 SKILL.md + contract.json + agents/openai.yaml
- 知识管理链：ingest-source → patch-wiki-page, answer-from-wiki → deposit-answer → patch-wiki-page, run-wiki-health → patch-wiki-page, extract-insight → patch-wiki-page
- 研发自动化链：tech-solution → tech-review → coding → test-prep → test-fix → (problem-solve | deposit-answer)
- skill-router 是唯一 router（category=routing），nextSkills 包含所有 12 个 domain skill
- 编写 Skill 的三原则：producer 原则驱动，reviewer 结构化清单 + evidence，diagnostic 从真实信号开始禁止猜测
- SAFETY_BYPASS_CLAIM 的否定语境（「不做：直接写 wiki」）现在正确识别——`_NEGATION_PREFIX` 匹配 `**不做**：` 前缀，`_IMMEDIATE_NEGATION` 匹配紧邻的「不」字

## 模糊区

- behavioral contract cases 的实际执行 — 格式已定，contents 待 Skill 实战后产生

## 黑盒区（完全不懂）

- 外部 Agent 加载 Skill package 后的实际执行行为 — 当前只保证 package 可校验，执行语义未定义
