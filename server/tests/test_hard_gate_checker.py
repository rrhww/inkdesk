"""HardGateChecker 单元测试：验证各 GateKind 的通过/失败逻辑。

测试策略：在 tmp_path 下创建临时 skill package + 临时 db，构造不同 run 状态
验证 gate 检查逻辑。
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest


# ── 测试用 Skill package fixture ──

CODING_CONTRACT = {
    "schemaVersion": "1.0",
    "id": "coding",
    "version": "0.1.0",
    "status": "draft",
    "category": "engineering",
    "kind": "producer",
    "summary": "测试用 coding skill",
    "inputs": [
        {"name": "solution_doc", "type": "string", "required": True, "constraints": "path to solution"},
        {"name": "tech_review_report", "type": "string", "required": True, "constraints": "path to review"},
    ],
    "contextRequirements": [],
    "outputs": [{"type": "code_changes", "location": "runs/<run_id>/coding-log.md", "needsReview": False}],
    "hardGates": [
        {"id": "g-solution", "kind": "required_input", "params": {"field": "solution_doc"}, "on_failure": "方案文档不得为空"},
        {"id": "g-review", "kind": "review_approved", "params": {}, "on_failure": "tech-review 必须已通过"},
        {"id": "g-confirm", "kind": "human_confirmation", "params": {}, "on_failure": "用户必须显式确认"},
    ],
    "capabilities": ["read_vault"],
    "writePolicy": {"canonicalWiki": "denied", "runArtifacts": "allowed", "codeRepository": "delegated"},
    "verification": [{"kind": "lint", "description": "lint pass"}],
    "nextSkills": [{"skillId": "test-prep"}],
    "supportedRuntimes": ["inkdesk"],
}

SOLUTION_CONTRACT = {
    "schemaVersion": "1.0",
    "id": "tech-solution",
    "version": "0.1.0",
    "status": "draft",
    "category": "engineering",
    "kind": "producer",
    "summary": "测试用 solution skill",
    "inputs": [{"name": "requirement", "type": "string", "required": True, "constraints": "min_length:1"}],
    "contextRequirements": [],
    "outputs": [{"type": "solution_doc", "location": "runs/<run_id>/tech-solution.md", "needsReview": True}],
    "hardGates": [
        {"id": "g-req", "kind": "required_input", "params": {"field": "requirement"}, "on_failure": "需求描述不得为空"},
        {"id": "g-vault", "kind": "vault_initialized", "params": {}, "on_failure": "KB 未初始化"},
    ],
    "capabilities": ["read_vault"],
    "writePolicy": {"canonicalWiki": "denied", "runArtifacts": "allowed", "codeRepository": "delegated"},
    "verification": [{"kind": "lint", "description": "lint pass"}],
    "nextSkills": [{"skillId": "tech-review"}],
    "supportedRuntimes": ["inkdesk"],
}


def _create_skill_package(vault_root: Path, skill_id: str, contract: dict) -> None:
    """在 vault_root/skills/<skill_id>/ 下创建测试用 Skill package。"""
    pkg_dir = vault_root / "skills" / skill_id
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "SKILL.md").write_text(f"# {skill_id}\n\n测试用 skill。\n", encoding="utf-8")
    (pkg_dir / "contract.json").write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")


@pytest.fixture()
def test_vault(tmp_path: Path) -> Path:
    """创建含 coding + tech-solution skill 的临时 vault（已初始化所有 SHARED_DIRS）。"""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    # 创建所有 SHARED_DIRS 让 VaultService.get_status() 返回 initialized=True
    for d in ("raw", "wiki", "schema", "skills", "evals", "runs"):
        (vault_root / d).mkdir(exist_ok=True)
    (vault_root / "KB-META.md").write_text("# KB Meta", encoding="utf-8")
    _create_skill_package(vault_root, "coding", CODING_CONTRACT)
    _create_skill_package(vault_root, "tech-solution", SOLUTION_CONTRACT)
    return vault_root


@pytest.fixture()
def db_session(temp_app_env: Path):
    """获取临时 db session，先初始化表结构。"""
    from inkdesk_server.db import init_db, session_scope
    init_db()
    with session_scope() as session:
        yield session


def _create_run(db_session, run_id: str = "run-test123", goal: str = "测试目标",
                current_stage: str = "coding", workspace_id: str = "ws-test") -> str:
    """在 db 中创建一个 DevRun，返回 run_id。"""
    from inkdesk_server.models import DevRun, RunEvent
    now = datetime.now(UTC)
    run = DevRun(
        id=run_id,
        workspace_id=workspace_id,
        type="PRD",
        title="测试任务",
        goal=goal,
        repo_context=None,
        status="active",
        current_stage=current_stage,
        stage_status="pending",
        created_at=now,
        updated_at=now,
    )
    db_session.add(run)
    db_session.commit()
    return run_id


def _add_event(db_session, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    from inkdesk_server.models import DevRun, RunEvent
    from uuid import uuid4
    now = datetime.now(UTC)
    event = RunEvent(
        id=f"revent-{uuid4().hex[:12]}",
        run_id=run_id,
        event_type=event_type,
        stage=stage,
        payload_json=json.dumps(payload, ensure_ascii=False),
        created_at=now,
    )
    db_session.add(event)
    db_session.commit()


# ── 测试用例 ──

def test_no_skill_package_passes(test_vault: Path, db_session) -> None:
    """stage 没有 Skill package 时应 passed=True + warning。"""
    from inkdesk_server.hard_gate_checker import HardGateChecker
    from inkdesk_server.skill_loader import SkillLoader
    from inkdesk_server.vault import VaultService
    from inkdesk_server.core.config import get_settings

    settings = get_settings()
    settings.vault_root = str(test_vault)

    run_id = _create_run(db_session, current_stage="context")

    checker = HardGateChecker(
        skill_loader=SkillLoader(test_vault),
        vault_service=VaultService(settings),
        db=db_session,
        vault_root=test_vault,
    )
    result = checker.check(run_id, "context")
    assert result.passed
    assert len(result.warnings) >= 1


def test_required_input_solution_doc_missing(test_vault: Path, db_session) -> None:
    """coding stage 没有 solution_draft_generated 事件时应失败。"""
    from inkdesk_server.hard_gate_checker import HardGateChecker
    from inkdesk_server.skill_loader import SkillLoader
    from inkdesk_server.vault import VaultService
    from inkdesk_server.core.config import get_settings

    settings = get_settings()
    settings.vault_root = str(test_vault)

    run_id = _create_run(db_session, current_stage="coding")

    checker = HardGateChecker(
        skill_loader=SkillLoader(test_vault),
        vault_service=VaultService(settings),
        db=db_session,
        vault_root=test_vault,
    )
    result = checker.check(run_id, "coding")
    assert not result.passed
    # 应该有 g-solution 失败（required_input: solution_doc）
    failure_ids = [f.gate_id for f in result.failures]
    assert "g-solution" in failure_ids


def test_required_input_solution_doc_present(test_vault: Path, db_session) -> None:
    """coding stage 有 solution_draft_generated 事件且 draft 非空时 g-solution 通过。"""
    from inkdesk_server.hard_gate_checker import HardGateChecker
    from inkdesk_server.skill_loader import SkillLoader
    from inkdesk_server.vault import VaultService
    from inkdesk_server.core.config import get_settings

    settings = get_settings()
    settings.vault_root = str(test_vault)

    run_id = _create_run(db_session, current_stage="coding")
    _add_event(db_session, run_id, "solution", "solution_draft_generated", {"draft": "方案内容"})

    checker = HardGateChecker(
        skill_loader=SkillLoader(test_vault),
        vault_service=VaultService(settings),
        db=db_session,
        vault_root=test_vault,
    )
    result = checker.check(run_id, "coding")
    # g-solution 应通过，但 g-review 可能失败（没有 stage_approved 事件）
    failure_ids = [f.gate_id for f in result.failures]
    assert "g-solution" not in failure_ids, "solution_doc gate should pass when draft present"


def test_review_approved_when_stage_advanced(test_vault: Path, db_session) -> None:
    """当 run.currentStage 已超过 review（如 coding）时，review_approved gate 应通过。"""
    from inkdesk_server.hard_gate_checker import HardGateChecker
    from inkdesk_server.skill_loader import SkillLoader
    from inkdesk_server.vault import VaultService
    from inkdesk_server.core.config import get_settings

    settings = get_settings()
    settings.vault_root = str(test_vault)

    run_id = _create_run(db_session, current_stage="coding")
    _add_event(db_session, run_id, "solution", "solution_draft_generated", {"draft": "方案"})

    checker = HardGateChecker(
        skill_loader=SkillLoader(test_vault),
        vault_service=VaultService(settings),
        db=db_session,
        vault_root=test_vault,
    )
    result = checker.check(run_id, "coding")
    failure_ids = [f.gate_id for f in result.failures]
    assert "g-review" not in failure_ids, "review_approved should pass when currentStage > review"


def test_solution_stage_requirement_empty_fails(test_vault: Path, db_session) -> None:
    """solution stage 的 required_input(requirement) 在 run.goal 为空时应失败。"""
    from inkdesk_server.hard_gate_checker import HardGateChecker
    from inkdesk_server.skill_loader import SkillLoader
    from inkdesk_server.vault import VaultService
    from inkdesk_server.core.config import get_settings

    settings = get_settings()
    settings.vault_root = str(test_vault)

    run_id = _create_run(db_session, goal="", current_stage="solution")

    checker = HardGateChecker(
        skill_loader=SkillLoader(test_vault),
        vault_service=VaultService(settings),
        db=db_session,
        vault_root=test_vault,
    )
    result = checker.check(run_id, "solution")
    assert not result.passed
    failure_ids = [f.gate_id for f in result.failures]
    assert "g-req" in failure_ids


def test_solution_stage_requirement_present_passes(test_vault: Path, db_session) -> None:
    """solution stage 的 required_input(requirement) 在 run.goal 非空时通过。"""
    from inkdesk_server.hard_gate_checker import HardGateChecker
    from inkdesk_server.skill_loader import SkillLoader
    from inkdesk_server.vault import VaultService
    from inkdesk_server.core.config import get_settings

    settings = get_settings()
    settings.vault_root = str(test_vault)

    run_id = _create_run(db_session, goal="实现登录功能", current_stage="solution")

    checker = HardGateChecker(
        skill_loader=SkillLoader(test_vault),
        vault_service=VaultService(settings),
        db=db_session,
        vault_root=test_vault,
    )
    result = checker.check(run_id, "solution")
    failure_ids = [f.gate_id for f in result.failures]
    assert "g-req" not in failure_ids, "requirement gate should pass when goal present"


def test_vault_initialized_gate(test_vault: Path, db_session) -> None:
    """solution stage 的 vault_initialized gate 应在 vault 已初始化时通过。"""
    from inkdesk_server.hard_gate_checker import HardGateChecker
    from inkdesk_server.skill_loader import SkillLoader
    from inkdesk_server.vault import VaultService
    from inkdesk_server.core.config import get_settings

    settings = get_settings()
    settings.vault_root = str(test_vault)

    run_id = _create_run(db_session, goal="测试", current_stage="solution")

    checker = HardGateChecker(
        skill_loader=SkillLoader(test_vault),
        vault_service=VaultService(settings),
        db=db_session,
        vault_root=test_vault,
    )
    result = checker.check(run_id, "solution")
    failure_ids = [f.gate_id for f in result.failures]
    assert "g-vault" not in failure_ids, "vault_initialized should pass when KB-META.md exists"


def test_human_confirmation_returns_warning(test_vault: Path, db_session) -> None:
    """human_confirmation gate 当前未实现，应返回 warning 不阻塞。"""
    from inkdesk_server.hard_gate_checker import HardGateChecker
    from inkdesk_server.skill_loader import SkillLoader
    from inkdesk_server.vault import VaultService
    from inkdesk_server.core.config import get_settings

    settings = get_settings()
    settings.vault_root = str(test_vault)

    run_id = _create_run(db_session, current_stage="coding")
    _add_event(db_session, run_id, "solution", "solution_draft_generated", {"draft": "方案"})

    checker = HardGateChecker(
        skill_loader=SkillLoader(test_vault),
        vault_service=VaultService(settings),
        db=db_session,
        vault_root=test_vault,
    )
    result = checker.check(run_id, "coding")
    # g-confirm 是 human_confirmation，应在 warnings 里不在 failures 里
    assert "g-confirm" not in [f.gate_id for f in result.failures]
    assert any("g-confirm" in w for w in result.warnings)


def test_run_not_found_fails(test_vault: Path, db_session) -> None:
    """run 不存在时应返回 passed=False。"""
    from inkdesk_server.hard_gate_checker import HardGateChecker
    from inkdesk_server.skill_loader import SkillLoader
    from inkdesk_server.vault import VaultService
    from inkdesk_server.core.config import get_settings

    settings = get_settings()
    settings.vault_root = str(test_vault)

    checker = HardGateChecker(
        skill_loader=SkillLoader(test_vault),
        vault_service=VaultService(settings),
        db=db_session,
        vault_root=test_vault,
    )
    result = checker.check("nonexistent-run", "coding")
    assert not result.passed


def test_gate_result_assert_passed_raises(test_vault: Path, db_session) -> None:
    """GateResult.assert_passed() 失败时应抛 ApiError(409)。"""
    from inkdesk_server.hard_gate_checker import GateResult, GateFailure
    from inkdesk_server.security import ApiError

    result = GateResult(
        passed=False,
        failures=[GateFailure(gate_id="g-test", kind="required_input", message="测试失败")],
    )
    with pytest.raises(ApiError) as exc_info:
        result.assert_passed()
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "HARD_GATE_FAILED"


def test_gate_result_assert_passed_ok() -> None:
    """GateResult.assert_passed() 通过时不抛异常。"""
    from inkdesk_server.hard_gate_checker import GateResult
    result = GateResult(passed=True)
    result.assert_passed()  # 不应抛异常
