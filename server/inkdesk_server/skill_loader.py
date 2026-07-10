"""Skill 加载器：从 vault/skills/<stage>/ 加载 SKILL.md + contract.json + 资源文件。

每个 stage action 通过 SkillLoader 获取该阶段的 Skill 定义，用于：
1. Hard Gate 校验（执行 stage action 前检查 contract.hardGates）
2. Prompt 注入（把 SKILL.md 内容 + references + templates 注入 LLM prompt）

stage → skill_id 映射：
- solution → tech-solution
- review   → tech-review
- coding   → coding
- testing  → test-prep

context 和 deposit 阶段不调用 LLM 生成内容，不需要 Skill。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from inkdesk_skill_sdk.contracts import Contract

logger = logging.getLogger(__name__)


# stage 名称 → vault/skills/ 下的目录名（即 contract.id）
STAGE_TO_SKILL_ID: dict[str, str] = {
    "solution": "tech-solution",
    "review": "tech-review",
    "coding": "coding",
    "testing": "test-prep",
}


@dataclass(frozen=True)
class LoadedSkill:
    """已加载的 Skill package 内容。"""

    name: str  # stage 名称，如 "coding"
    skill_id: str  # contract.id，如 "tech-solution"
    contract: Contract
    skill_md: str
    references: dict[str, str] = field(default_factory=dict)  # filename -> content
    templates: dict[str, str] = field(default_factory=dict)
    package_path: str = ""


class SkillLoader:
    """从 vault_root/skills/ 加载 Skill package，带进程级缓存。

    缓存策略：首次加载后缓存，Skill 文件不常变。如需刷新缓存（开发期），
    调用 clear_cache() 或重启进程。
    """

    def __init__(self, vault_root: Path | str) -> None:
        self._skills_root = Path(vault_root).expanduser().resolve() / "skills"
        self._cache: dict[str, LoadedSkill | None] = {}

    def supports_stage(self, stage: str) -> bool:
        """该 stage 是否有对应 Skill（context/deposit 没有）。"""
        return stage in STAGE_TO_SKILL_ID

    def load(self, stage: str) -> LoadedSkill | None:
        """加载 stage 对应的 Skill。不存在时返回 None。"""
        if stage in self._cache:
            return self._cache[stage]

        skill_id = STAGE_TO_SKILL_ID.get(stage)
        if skill_id is None:
            self._cache[stage] = None
            return None

        result = self._load_package(stage, skill_id)
        self._cache[stage] = result
        return result

    def load_or_raise(self, stage: str) -> LoadedSkill:
        skill = self.load(stage)
        if skill is None:
            raise ValueError(f"Skill package not found for stage: {stage}")
        return skill

    def clear_cache(self) -> None:
        self._cache.clear()

    def _load_package(self, stage: str, skill_id: str) -> LoadedSkill | None:
        pkg_dir = self._skills_root / skill_id
        if not pkg_dir.is_dir():
            logger.warning("Skill package directory not found: %s", pkg_dir)
            return None

        # 解析 contract.json
        contract = self._load_contract(pkg_dir)
        if contract is None:
            return None

        # 读取 SKILL.md
        skill_md = self._read_file(pkg_dir / "SKILL.md")

        # 读取 references/ 和 templates/
        references = self._read_directory(pkg_dir / "references")
        templates = self._read_directory(pkg_dir / "templates")

        return LoadedSkill(
            name=stage,
            skill_id=skill_id,
            contract=contract,
            skill_md=skill_md,
            references=references,
            templates=templates,
            package_path=str(pkg_dir),
        )

    @staticmethod
    def _load_contract(pkg_dir: Path) -> Contract | None:
        contract_path = pkg_dir / "contract.json"
        if not contract_path.is_file():
            logger.warning("contract.json not found in %s", pkg_dir)
            return None
        try:
            import json
            data = json.loads(contract_path.read_text(encoding="utf-8"))
            return Contract.model_validate(data)
        except Exception:
            logger.exception("Failed to parse contract.json in %s", pkg_dir)
            return None

    @staticmethod
    def _read_file(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    @staticmethod
    def _read_directory(dir_path: Path) -> dict[str, str]:
        """读取目录下所有 .md 文件，返回 {filename: content}。"""
        result: dict[str, str] = {}
        if not dir_path.is_dir():
            return result
        for path in sorted(dir_path.glob("*.md")):
            try:
                result[path.name] = path.read_text(encoding="utf-8")
            except OSError:
                continue
        return result


# 进程级单例：vault_root 在进程生命周期内不变
_loader_cache: dict[str, SkillLoader] = {}


def get_skill_loader(vault_root: Path | str) -> SkillLoader:
    """获取进程级 SkillLoader 单例。"""
    key = str(Path(vault_root).expanduser().resolve())
    if key not in _loader_cache:
        _loader_cache[key] = SkillLoader(vault_root)
    return _loader_cache[key]
