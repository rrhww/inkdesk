"""
Scaffold a new draft Skill package from built-in templates.

Does NOT save templates as fake packages in skills/.
All generated files reference user-provided description/category/kind.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from inkdesk_skill_sdk.contracts import (
    ALLOWED_OPTIONAL_DIRS,
    SkillCategory,
    SkillKind,
)


def init_skill_package(
    target_dir: Path,
    name: str,
    description: str,
    category: str,
    kind: str,
    resources: list[str] | None = None,
    overwrite: bool = False,
) -> Path:
    """Create a new draft Skill package at target_dir.

    Raises FileExistsError if target_dir exists and overwrite is False.
    Returns the created directory path.
    """
    if target_dir.exists() and not overwrite:
        raise FileExistsError(f"Skill package already exists: {target_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)

    # Validate category and kind
    category_value = SkillCategory(category)
    kind_value = SkillKind(kind)

    # 1. SKILL.md
    _write_skill_md(target_dir, name, description)

    # 2. contract.json
    contract = _build_contract(name, description, category_value.value, kind_value.value)
    (target_dir / "contract.json").write_text(
        json.dumps(contract, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # 3. agents/openai.yaml
    agents_dir = target_dir / "agents"
    agents_dir.mkdir(exist_ok=True)
    openai_yaml = _build_openai_yaml(name, description, kind_value.value)
    (agents_dir / "openai.yaml").write_text(
        yaml.dump(openai_yaml, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )

    # 4. Optional resource directories
    for res in resources or []:
        if res in ALLOWED_OPTIONAL_DIRS:
            (target_dir / res).mkdir(exist_ok=True)

    return target_dir


def _write_skill_md(target_dir: Path, name: str, description: str) -> None:
    content = f"""---
name: {name}
description: {description}
---

# {name}

## 核心目标与边界

（待补充：这个 Skill 做什么、不做什么）

## Hard Gates

（待补充：什么条件不满足时必须停止）

## 主流程

（待补充：核心执行步骤和关键决策点）

## 需要读取的资源

（待补充：bundled resources 加载说明）

## 输出验证与下游衔接

（待补充：输出后如何验证，如何衔接到下一个 Skill）
"""
    (target_dir / "SKILL.md").write_text(content, encoding="utf-8")


def _build_contract(name: str, description: str, category: str, kind: str) -> dict[str, Any]:
    return {
        "schemaVersion": "1.0",
        "id": name,
        "version": "0.1.0",
        "status": "draft",
        "category": category,
        "kind": kind,
        "summary": description,
        "inputs": [],
        "contextRequirements": [],
        "outputs": [],
        "hardGates": [],
        "capabilities": [],
        "writePolicy": {
            "canonicalWiki": "proposal-only",
            "runArtifacts": "allowed",
            "codeRepository": "denied",
        },
        "verification": [],
        "nextSkills": [],
        "supportedRuntimes": ["inkdesk"],
    }


def _build_openai_yaml(name: str, description: str, kind: str) -> dict[str, Any]:
    default_prompt = _make_default_prompt(name, description, kind)
    return {
        "interface": {
            "display_name": name.replace("-", " ").title(),
            "short_description": description,
            "default_prompt": default_prompt,
        },
        "policy": {
            "allow_implicit_invocation": kind == "router",
        },
    }


def _make_default_prompt(name: str, description: str, kind: str) -> str:
    if kind == "router":
        return f"Use ${name} as the single entry point for routing user intents to domain skills."
    return f"Use ${name} to {description}"
