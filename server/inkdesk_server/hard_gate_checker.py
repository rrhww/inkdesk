"""Hard Gate 校验器：根据 Skill contract.hardGates 在 stage action 执行前检查前置条件。

每个 GateKind 对应一个 check 方法：
- required_input       — 检查指定字段非空（从 run 上下文取值）
- vault_initialized    — VaultService.get_status().initialized
- schema_gate_passed   — warn 级别，不阻塞（wiki schema 健康检查未完整实现）
- dev_run_exists       — DevRun 记录存在
- run_stage_is         — run.currentStage 匹配 params.stage
- review_approved      — 上游 review 阶段 stage_status == "completed"
- artifact_exists      — runs/<run_id>/<artifact> 文件存在
- real_failure_signal_present — diagnostic skill 用，当前未实现（warn）
- human_confirmation   — 需要用户显式确认（前端未配合，当前 warn 不阻塞）

设计原则：
- 失败时返回 GateResult.passed=False，stage action 抛 ApiError(409, "HARD_GATE_FAILED", ...)
- 未实现的 gate 返回 passed=True + warning，不阻塞流程
- Skill package 不存在时返回 passed=True（向后兼容，未 scaffold skill 的 stage 不强制 gate）
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from inkdesk_skill_sdk.contracts import GateKind, HardGate
from inkdesk_server.models import DevRun
from inkdesk_server.skill_loader import LoadedSkill, SkillLoader
from inkdesk_server.vault import VaultService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GateFailure:
    """单个 gate 失败。"""

    gate_id: str
    kind: str
    message: str  # contract.on_failure 文案


@dataclass(frozen=True)
class GateResult:
    """stage action 执行前的 hard gate 校验结果。"""

    passed: bool
    failures: list[GateFailure] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def assert_passed(self) -> None:
        """失败时抛 ApiError(409)。"""
        if not self.passed:
            from inkdesk_server.security import ApiError
            messages = "; ".join(f"{f.gate_id}: {f.message}" for f in self.failures)
            raise ApiError(409, "HARD_GATE_FAILED", messages)


@dataclass
class HardGateChecker:
    """Hard Gate 校验器。

    依赖：
    - skill_loader: 加载 stage 对应的 Skill contract
    - vault_service: vault_initialized gate
    - db: dev_run_exists / run_stage_is / review_approved gate
    - vault_root: artifact_exists gate（runs/<run_id>/ 目录）
    """

    skill_loader: SkillLoader
    vault_service: VaultService
    db: Session
    vault_root: Path

    def check(self, run_id: str, stage: str) -> GateResult:
        """检查指定 stage 的所有 hard gates。"""
        skill = self.skill_loader.load(stage)
        if skill is None:
            # 该 stage 没有 Skill package，不强制 gate（向后兼容）
            return GateResult(passed=True, warnings=[f"no skill package for stage: {stage}"])

        run = self.db.get(DevRun, run_id)
        if run is None:
            # run 不存在，所有 gate 都无法检查
            return GateResult(
                passed=False,
                failures=[GateFailure(
                    gate_id="_pre",
                    kind="dev_run_exists",
                    message=f"DevRun not found: {run_id}",
                )],
            )

        failures: list[GateFailure] = []
        warnings: list[str] = []

        for gate in skill.contract.hardGates:
            result = self._check_one(gate, run, skill)
            if result is None:
                # gate 通过
                continue
            if result == "warn":
                warnings.append(f"{gate.id}({gate.kind}): not implemented, skipped")
                continue
            # 失败
            failures.append(GateFailure(
                gate_id=gate.id,
                kind=gate.kind.value,
                message=gate.on_failure,
            ))

        return GateResult(
            passed=len(failures) == 0,
            failures=failures,
            warnings=warnings,
        )

    def _check_one(self, gate: HardGate, run: DevRun, skill: LoadedSkill) -> str | None:
        """检查单个 gate。返回 None=通过，"warn"=未实现警告，其他字符串=失败原因。"""
        kind = gate.kind

        if kind == GateKind.REQUIRED_INPUT:
            return self._check_required_input(gate, run, skill)

        if kind == GateKind.VAULT_INITIALIZED:
            status = self.vault_service.get_status()
            return None if status["initialized"] else "vault not initialized"

        if kind == GateKind.SCHEMA_GATE_PASSED:
            # wiki schema 健康检查未完整实现，warn 不阻塞
            return "warn"

        if kind == GateKind.DEV_RUN_EXISTS:
            # run 已在 check() 开头加载，这里必然通过
            return None

        if kind == GateKind.RUN_STAGE_IS:
            expected = gate.params.get("stage", "")
            return None if run.current_stage == expected else f"expected {expected}, got {run.current_stage}"

        if kind == GateKind.REVIEW_APPROVED:
            return self._check_review_approved(run)

        if kind == GateKind.ARTIFACT_EXISTS:
            return self._check_artifact_exists(gate, run)

        if kind == GateKind.REAL_FAILURE_SIGNAL:
            # diagnostic skill 用，当前未实现
            return "warn"

        if kind == GateKind.HUMAN_CONFIRMATION:
            # 前端未配合确认流程，当前 warn 不阻塞
            # TODO: 前端实现确认 UI 后改为强制检查
            return "warn"

        logger.warning("Unknown gate kind: %s", kind)
        return "warn"

    def _check_required_input(
        self, gate: HardGate, run: DevRun, skill: LoadedSkill
    ) -> str | None:
        """检查 required_input gate：指定字段非空。

        params.field 对应 Skill 的 input name，需要映射到 run 上下文：
        - solution_doc → review/coding 阶段读取上游 solution_draft_generated.draft
        - tech_review_report → coding 阶段读取上游 review_checklist_generated
        - requirement → run.goal
        - change_scope → coding 阶段产出或 run.goal
        """
        field_name = gate.params.get("field", "")
        if not field_name:
            return "required_input gate missing 'field' param"

        # 直接映射的 run 字段
        if field_name == "requirement":
            return None if run.goal and run.goal.strip() else "requirement is empty"

        if field_name == "change_scope":
            return None if run.goal and run.goal.strip() else "change_scope is empty"

        # solution_doc / tech_review_report：从 run events 查找上游产出
        if field_name == "solution_doc":
            return self._check_upstream_event(
                run, "solution", "solution_draft_generated", "draft"
            )

        if field_name == "tech_review_report":
            return self._check_upstream_event(
                run, "review", "review_checklist_generated", "checklist"
            )

        # 未知 field，warn
        return "warn"

    def _check_upstream_event(
        self, run: DevRun, stage: str, event_type: str, payload_key: str
    ) -> str | None:
        """检查 run 是否有指定上游事件且 payload 非空。"""
        # run.events relationship 已有 order_by=RunEvent.created_at，直接 reversed
        for event in reversed(list(run.events)):
            if event.stage == stage and event.event_type == event_type:
                try:
                    payload = json.loads(event.payload_json) if isinstance(event.payload_json, str) else event.payload_json
                except (json.JSONDecodeError, TypeError):
                    return f"failed to parse {event_type} payload"
                value = payload.get(payload_key) if isinstance(payload, dict) else None
                if value and (isinstance(value, str) and value.strip() or isinstance(value, list) and len(value) > 0):
                    return None
                return f"{event_type}.{payload_key} is empty"
        return f"no {event_type} event found in stage {stage}"

    def _check_review_approved(self, run: DevRun) -> str | None:
        """检查 review 阶段是否已 approved。

        run.stage_status 在 advance_run(action="approve") 后会变为 "completed"，
        同时 current_stage 推进到下一阶段。所以当 run.current_stage == "coding" 时，
        review 阶段必然已 approved（否则无法推进到 coding）。

        但如果 run.current_stage 是手动设置的（测试场景），需要额外检查 events。
        """
        # 如果已经在 coding 或更后面的阶段，review 必然已 approved
        stages_order = ["context", "solution", "review", "coding", "testing", "deposit"]
        try:
            cur_idx = stages_order.index(run.current_stage)
            review_idx = stages_order.index("review")
            if cur_idx > review_idx:
                return None
        except ValueError:
            pass

        # 检查是否有 stage_approved 事件
        for event in reversed(list(run.events)):
            if event.event_type == "stage_approved" and event.stage == "review":
                return None

        return "review stage not approved"

    def _check_artifact_exists(self, gate: HardGate, run: DevRun) -> str | None:
        """检查 runs/<run_id>/<artifact> 文件存在。

        params.field 指定要检查的 input（如 solution_doc），
        实际文件路径根据 stage 推断：runs/<run_id>/<stage>.md
        """
        field_name = gate.params.get("field", "")
        if field_name == "solution_doc":
            artifact_path = self.vault_root / "runs" / run.id / "tech-solution.md"
        elif field_name == "tech_review_report":
            artifact_path = self.vault_root / "runs" / run.id / "tech-review.md"
        elif field_name == "change_scope":
            artifact_path = self.vault_root / "runs" / run.id / "coding-log.md"
        else:
            return "warn"

        return None if artifact_path.is_file() else f"artifact not found: {artifact_path.name}"
