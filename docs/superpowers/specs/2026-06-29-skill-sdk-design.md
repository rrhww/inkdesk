# Inkdesk Skill SDK 设计

> 4.1.4 阶段：Skill 开发准备 — 固定 portable Skill package 格式、双层契约、校验器、脚手架、路由图和 promotion 门禁。

## 架构定位

Inkdesk 的 Skill 不是 Web 应用的功能模块，而是一等产品对象。产品架构核心链路：

```
Sources → LLM-Wiki → Schema → Skills → Agent Runtime → Evaluation → Harness
```

Skills 是可检查、可版本化、可导出、外部 Agent 可消费的研发动作协议。4.1.4 产出 Skill SDK，4.2.1 使用它生产首批 13 个正式 Skill。

## 与 omni-superdev 的关系

omni-superdev（`~/.codex/skills/omni-superdev/`）是 Inkdesk `skill-router` 的参考原型。采用的模式：

- 单一入口路由（skill-router 是唯一宽入口）
- discipline/domain 分层（TDD、debug、verification 属纪律；tech-solution 等属领域）
- 渐进式加载（`references/prompts/templates/scripts/assets` 按需）
- 冲突优先级（用户 > 项目 > 安全 > router > 领域 > 风格）
- lint + behavioral fixture 双门禁
- 完成须引用验证证据

## 关键决策

| 决策 | 结论 |
|------|------|
| `agents/openai.yaml` | 必需，含 `interface` + `policy` 两层，scaffolder 生成，validator 检查三方一致 |
| `implicitInvocation` | 不在 contract 中显式声明，由 routing graph 从 `category=routing` 自动推断 |
| `hardGates` 粒度 | 参数化声明式：`id/kind/params/on_failure`，无 warn 级别 |
| `prompts/` 目录 | 保留但留白，格式约束等到 4.2.1 自然长出 |
| 实现包 | `inkdesk_skill_sdk` 独立包，pip/uv 安装，仅依赖 pydantic+pyyaml |
| Fixture 范围 | 每种 lint 规则至少一个非法 fixture + 接近真实 skill-router 的合法性 fixture |

## Skill Package 格式

```
skills/<skill-name>/
  SKILL.md              # 必需 — Agent 可读的核心流程
  contract.json          # 必需 — Inkdesk 机器契约
  agents/
    openai.yaml          # 必需 — 外部 Agent 元数据
  references/            # 可选 — 按需加载的领域规则
  prompts/               # 可选 — 角色或阶段提示模板（留白）
  templates/             # 可选 — 输出文档模板
  scripts/               # 可选 — 确定性辅助脚本
  assets/                # 可选 — 输出所需静态资源
```

约束：
- 目录名仅允许小写字母、数字、连字符，长度 1–63
- `SKILL.md` + `contract.json` + `agents/openai.yaml` 三项必须存在
- 资源目录按需创建
- 内部引用全部使用相对 Skill root 的路径

### SKILL.md

Frontmatter 仅包含 `name` 和 `description`。description 须明确触发/非触发边界。

正文保留 Agent 执行所需：核心目标与边界、Hard Gates、主流程、关键决策点、需加载的 bundled resources、输出后的验证与衔接。

### contract.json

```json
{
  "schemaVersion": "1.0",
  "id": "tech-solution",
  "version": "0.1.0",
  "status": "draft",
  "category": "engineering",
  "kind": "producer",
  "summary": "从需求和知识上下文生成可评审技术方案",
  "inputs": [],
  "contextRequirements": [],
  "outputs": [],
  "hardGates": [],
  "capabilities": [],
  "writePolicy": {
    "canonicalWiki": "proposal-only",
    "runArtifacts": "allowed",
    "codeRepository": "delegated"
  },
  "verification": [],
  "nextSkills": [],
  "supportedRuntimes": ["inkdesk", "codex", "claude-code"]
}
```

category: `knowledge | engineering | routing | discipline`
kind: `producer | reviewer | router | diagnostic`
writePolicy: canonicalWiki 仅 `denied | proposal-only`，不存在 `direct`
hardGates: 参数化，每组 `{id, kind, params, on_failure}`

### agents/openai.yaml

```yaml
interface:
  display_name: "Tech Solution"
  short_description: "从需求和知识上下文生成可评审技术方案"
  default_prompt: "Use $tech-solution to ..."

policy:
  allow_implicit_invocation: false
```

validator 检查 `display_name` 与 SKILL frontmatter `name`、contract `id` 一致性。

## 校验模型

### Structural Lint
- 目录名、必需文件、允许目录
- SKILL frontmatter 可解析且仅含 `name/description`
- contract JSON 可解析并通过 schemaVersion 1.0
- SemVer、枚举、字段长度约束

### Semantic Lint
- 目录名、frontmatter name、contract id、openai.yaml display_name 一致
- description 与 name/summary 不简单重复
- required input 在 hardGates 中有对应约束
- output、writePolicy、review 要求一致
- nextSkills 均存在、无非法环
- openai.yaml 与 SKILL 不冲突

### Safety Lint
- canonicalWiki 仅 `denied` 或 `proposal-only`
- 无硬编码绝对路径、秘密样例
- 引用不逃逸 package root
- Skill 不声称可绕过 review/schema gate/用户确认

## CLI

```powershell
cd server
python -m inkdesk_skill_sdk init <name> --description <text> --category <category> --kind <kind>
python -m inkdesk_skill_sdk validate [<name>]
python -m inkdesk_skill_sdk graph
python -m inkdesk_skill_sdk check <name>
```

## 包结构

```
server/
  inkdesk_skill_sdk/
    __init__.py
    contracts.py         # Pydantic models + JSON Schema
    validation.py         # structural/semantic/safety lint
    registry.py           # discovery, resolution, metadata
    scaffolder.py         # init draft package
    graph.py              # routing graph + conflict detection
    cli.py                # init/validate/graph/check
    pyproject.toml        # pydantic>=2.8, pyyaml
  inkdesk_server/
    skill_vault.py        # skill/ dir safe I/O
    skill_assets.py       # schema default assets
```

## Promotion 门禁

draft → active 须全部满足：
1. structural + semantic + safety lint PASSED
2. behavioral contract cases 全部通过
3. description 的触发/非触发边界已人工审核
4. hardGates + writePolicy 已人工审核
5. 存在 Golden Task/rubric 或经审核的延期理由
6. schema gate 通过
7. version 已更新

## 路由规则

- 单一 router（`category=routing`）是唯一宽入口
- 领域 Skill 的 description 须窄到可区分
- 冲突优先级：用户指令 > 项目约束 > 安全 > router > 领域 Skill > 风格
- 多个领域 Skill 同时匹配时选范围最窄且满足全部前置条件者
- Skill 链出现环时 validator 失败

## 测试 Fixture 目录

```
server/tests/skill_fixtures/
  valid/
    minimal-producer/          # 最小合法 producer
    comprehensive-router/      # 接近真实 skill-router 的复杂合法 fixture
  invalid/
    bad-id-mismatch/           # 目录名/name/id 不一致
    bad-write-policy/          # canonicalWiki: direct
    bad-absolute-path/         # 含 Windows/Unix 绝对路径
    bad-circular-next/         # nextSkills 环
    bad-missing-contract/      # 缺 contract.json
    bad-missing-openai/        # 缺 agents/openai.yaml
    bad-frontmatter-extra/     # SKILL.md frontmatter 含额外字段
    bad-semver/                # 非法 SemVer
    bad-category/              # 非法 category 枚举值
    bad-self-bypass/           # 声称可绕过 review
```

## 参考

- [4.1.4 Skill 开发准备实施计划](../../development/plans/4.1.4-Skill开发准备-实施计划.md)
- [开发计划总指南](../../development/plans/开发计划总指南.md)
- [产品愿景](../../product/产品愿景.md)
- [产品定位与形态](../../product/产品定位与形态.md)
- omni-superdev (`~/.codex/skills/omni-superdev/`) — SKILL.md, agents/openai.yaml, references/conflict-policy.md, references/workflow-map.md
