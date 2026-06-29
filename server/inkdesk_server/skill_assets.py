"""
Vault default assets for Inkdesk Skill SDK.

Registers skill-related schema files so vault init creates them.
All content derives from the Skill SDK spec and design documents.
"""

from __future__ import annotations

from inkdesk_server.vault_assets import _register
from inkdesk_skill_sdk.contracts import generate_contract_json_schema

import json


def register_skill_schema_assets() -> None:
    """Register skill SDK schema assets into vault defaults.

    These are added to vault_assets.SHARED_FILES so that vault init
    creates them if they don't already exist.
    """
    # 1. Contract JSON Schema — machine-consumable, generated from Pydantic model
    contract_schema = generate_contract_json_schema()
    _register(
        "schema/skill-contract.schema.json",
        json.dumps(contract_schema, indent=2, ensure_ascii=False),
    )

    # 2. Skill package specification — human-readable
    _register(
        "schema/skill-package-spec.md",
        """# Skill Package 规范

## 目录结构

```
skills/<skill-name>/
  SKILL.md              # 必需 — Agent 可读的核心流程
  contract.json          # 必需 — Inkdesk 机器契约
  agents/
    openai.yaml          # 必需 — 外部 Agent 元数据
  references/            # 可选 — 按需加载的领域规则
  prompts/               # 可选 — 角色或阶段提示模板
  templates/             # 可选 — 输出文档模板
  scripts/               # 可选 — 确定性辅助脚本
  assets/                # 可选 — 输出所需静态资源
```

## 约束

- 目录名仅允许小写字母、数字、连字符，长度 1–63
- `SKILL.md` + `contract.json` + `agents/openai.yaml` 必须存在
- 资源目录按需创建，空目录不入 package
- 所有内部引用使用相对 Skill root 的路径

## SKILL.md

Frontmatter 仅含 `name` 和 `description`。description 须明确触发/非触发边界。

正文保留：核心目标与边界、Hard Gates、主流程、关键决策点、
需要读取的 bundled resources、输出后验证与衔接。

## contract.json

机器可读契约，由 Pydantic 模型定义，JSON Schema 见 `skill-contract.schema.json`。

关键字段：id / version / status / category / kind / inputs / outputs / hardGates /
writePolicy / nextSkills / supportedRuntimes

## agents/openai.yaml

```yaml
interface:
  display_name: "Human Readable Name"
  short_description: "One line description"
  default_prompt: "Use $skill-name to ..."

policy:
  allow_implicit_invocation: false  # true only for router
```

## 生命周期

draft → active → deprecated
""",
    )

    # 3. Safety rules
    _register(
        "schema/skill-safety-rules.md",
        """# Skill 安全规则

## Hard Gates

第一版允许的 gate kind：
- required_input
- vault_initialized
- schema_gate_passed
- dev_run_exists
- run_stage_is
- review_approved
- artifact_exists
- real_failure_signal_present
- human_confirmation

每个 gate 含 id / kind / params / on_failure。
Gate 失败时 Skill 必须停止或返回 blocked，不允许自行降级绕过。

## Write Policy

canonicalWiki 只能为 denied 或 proposal-only，不存在 direct。
runArtifacts: denied | allowed
codeRepository: denied | delegated

## 路径规则

- Vault 与代码仓路径从 KB-META.md、Dev Run 或明确输入解析
- Package 内路径相对 Skill root
- 禁止提交用户目录、盘符或主机绝对路径
- Validator 扫描 Windows 与 Unix 绝对路径模式

## 禁止行为

- 不得声称可绕过 review、schema gate 或用户确认
- scripts 不得读取未声明的环境变量
- scripts 不得包含秘密或主机绝对路径
""",
    )

    # 4. Routing rules
    _register(
        "schema/skill-routing-rules.md",
        """# Skill 路由规则

## 单一宽入口

`skill-router`（category=routing）是唯一宽入口。
其他 Skill 的 description 必须窄到可区分。

## 优先级

1. 用户当前明确指令
2. 项目 AGENTS.md / Schema / 安全约束
3. Dev Run 当前状态与已批准门禁
4. skill-router 的类型与链路选择
5. 当前领域 Skill
6. 默认风格偏好

## 冲突处理

- 多个领域 Skill 同时匹配时，选范围最窄且满足全部前置条件者
- reviewer 不接管 producer 的产出职责
- discipline 类能力只增加门禁，不成为第二流程控制器
- 无法唯一选择时返回候选和差异，请用户决定
- Skill 链出现环时 validator 失败

## 两条初始链路

知识管理：
ingest-source -> patch-wiki-page
answer-from-wiki -> deposit-answer -> patch-wiki-page
run-wiki-health -> patch-wiki-page

研发自动化：
tech-solution -> tech-review -> coding -> test-prep -> test-fix
                                         -> problem-solve
""",
    )


# Register on import
register_skill_schema_assets()
