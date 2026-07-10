"""SkillLoader 单元测试：验证从 vault/skills/ 加载真实 Skill package。"""
from __future__ import annotations

from pathlib import Path

import pytest

# 项目根：tests/ -> server/ -> inkdesk/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REAL_VAULT_ROOT = PROJECT_ROOT / "server" / "vault"


def test_load_coding_skill() -> None:
    """验证能加载 coding Skill 的 contract + SKILL.md + references。"""
    from inkdesk_server.skill_loader import SkillLoader

    loader = SkillLoader(REAL_VAULT_ROOT)
    skill = loader.load("coding")

    assert skill is not None, "coding skill should be loaded"
    assert skill.skill_id == "coding"
    assert skill.name == "coding"  # stage name
    assert skill.contract.id == "coding"
    assert skill.contract.kind.value == "producer"
    assert len(skill.contract.hardGates) >= 1, "coding skill should have hard gates"
    assert skill.skill_md, "SKILL.md content should not be empty"
    # coding skill 有 references/ 子目录
    assert len(skill.references) >= 1, "coding skill should have references"


def test_load_solution_skill_with_templates() -> None:
    """验证 tech-solution Skill 加载含 templates。"""
    from inkdesk_server.skill_loader import SkillLoader

    loader = SkillLoader(REAL_VAULT_ROOT)
    skill = loader.load("solution")

    assert skill is not None
    assert skill.skill_id == "tech-solution"
    assert skill.contract.id == "tech-solution"
    # tech-solution 有 templates/solution-template.md
    assert "solution-template.md" in skill.templates, "should load solution template"
    # tech-solution 有 references/architecture-patterns.md
    assert "architecture-patterns.md" in skill.references


def test_load_review_skill() -> None:
    from inkdesk_server.skill_loader import SkillLoader
    skill = SkillLoader(REAL_VAULT_ROOT).load("review")
    assert skill is not None
    assert skill.skill_id == "tech-review"
    assert skill.contract.kind.value == "reviewer"


def test_load_testing_skill() -> None:
    from inkdesk_server.skill_loader import SkillLoader
    skill = SkillLoader(REAL_VAULT_ROOT).load("testing")
    assert skill is not None
    assert skill.skill_id == "test-prep"


def test_load_context_stage_returns_none() -> None:
    """context 阶段没有对应 Skill，应返回 None。"""
    from inkdesk_server.skill_loader import SkillLoader
    skill = SkillLoader(REAL_VAULT_ROOT).load("context")
    assert skill is None


def test_load_deposit_stage_returns_none() -> None:
    """deposit 阶段没有对应 Skill。"""
    from inkdesk_server.skill_loader import SkillLoader
    skill = SkillLoader(REAL_VAULT_ROOT).load("deposit")
    assert skill is None


def test_supports_stage() -> None:
    from inkdesk_server.skill_loader import SkillLoader
    loader = SkillLoader(REAL_VAULT_ROOT)
    assert loader.supports_stage("solution")
    assert loader.supports_stage("coding")
    assert not loader.supports_stage("context")
    assert not loader.supports_stage("deposit")


def test_caching_returns_same_instance() -> None:
    """load() 第二次应返回缓存结果。"""
    from inkdesk_server.skill_loader import SkillLoader
    loader = SkillLoader(REAL_VAULT_ROOT)
    first = loader.load("coding")
    second = loader.load("coding")
    assert first is second, "should return cached instance"


def test_load_nonexistent_vault_returns_none() -> None:
    """vault_root 不存在时 load() 应返回 None 而非抛异常。"""
    from inkdesk_server.skill_loader import SkillLoader
    loader = SkillLoader("/nonexistent/path/vault")
    assert loader.load("coding") is None


def test_get_skill_loader_singleton() -> None:
    """get_skill_loader 对同一路径返回同一实例。"""
    from inkdesk_server.skill_loader import get_skill_loader
    a = get_skill_loader(REAL_VAULT_ROOT)
    b = get_skill_loader(REAL_VAULT_ROOT)
    assert a is b
