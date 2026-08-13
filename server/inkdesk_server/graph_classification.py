from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping


GRAPH_STAGES = (
    "requirements",
    "design",
    "implementation",
    "verification",
    "delivery",
    "knowledge",
)
GRAPH_IMPORTANCE = ("core", "normal", "supporting")
GRAPH_VISIBILITY = ("primary", "secondary", "hidden")
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


@dataclass(frozen=True)
class GraphClassification:
    stage: str = "knowledge"
    domain: str = "general"
    category: str = "document"
    importance: str = "normal"
    visibility: str = "secondary"
    origin: str = "fallback"


@dataclass(frozen=True)
class ClassificationWarning:
    field: str
    value: str
    message: str


def _normalized_text(metadata: Mapping[str, Any], relative_path: str, kind: str) -> str:
    values: list[str] = [relative_path, kind]
    for field in ("title", "type", "kind", "inkdeskType", "generatedBy", "status"):
        value = metadata.get(field)
        if value is not None:
            values.append(str(value))
    tags = metadata.get("tags")
    if isinstance(tags, list):
        values.extend(str(tag) for tag in tags)
    elif tags is not None:
        values.append(str(tags))
    return " ".join(values).replace("_", "-").replace("\\", "/").casefold()


def _contains(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def _infer_stage(text: str) -> tuple[str, bool]:
    if _contains(text, "requirement", "prd", "user-story", "user story", "roadmap", "需求", "用户故事", "路线图"):
        return "requirements", True
    if _contains(text, "test", "audit", "evaluation", "eval", "finding", "quality", "health", "验收", "测试", "审计", "评测"):
        return "verification", True
    if _contains(text, "release", "deploy", "deployment", "runbook", "changelog", "migration", "backup", "运维", "发布", "部署", "备份"):
        return "delivery", True
    if _contains(text, "tech-solution", "solution", "architecture", "adr-", "/adr", "decision", "design", "spec", "api", "data-model", "database", "interface", "架构", "方案", "决策", "设计", "接口", "数据库"):
        return "design", True
    if _contains(text, "implementation", "coding", "capability", "skill", "module", "/plans/", "实施", "开发计划", "编码", "模块"):
        return "implementation", True
    if _contains(text, "concept", "source", "schema", "reference", "wiki", "raw", "知识", "来源"):
        return "knowledge", True
    return "knowledge", False


def _infer_domain(text: str) -> tuple[str, bool]:
    if _contains(text, "harness", "agent", "executor", "claude", "codex"):
        return "harness-agents", True
    if _contains(text, "skill", "capability"):
        return "skills", True
    if _contains(text, "test", "audit", "evaluation", "eval", "finding", "quality", "health", "测试", "审计", "评测", "质量"):
        return "quality", True
    if _contains(text, "product", "requirement", "prd", "user-story", "roadmap", "产品", "需求", "用户故事", "路线图"):
        return "product", True
    if _contains(text, "architecture", "adr-", "/adr", "decision", "tech-solution", "solution", "api", "data-model", "database", "domain-model", "架构", "决策", "技术方案", "接口", "数据库", "领域模型"):
        return "architecture", True
    if _contains(text, "ops", "infra", "deploy", "release", "runbook", "backup", "migration", "environment", "运维", "部署", "发布", "备份"):
        return "operations", True
    if _contains(text, "server/", "web/", "repository", "module", "code", "repo", "仓库", "模块", "源码"):
        return "repository", True
    return "general", False


def _infer_category(text: str, kind: str) -> tuple[str, bool]:
    rules = (
        ("tech-solution", ("tech-solution", "technical solution", "技术方案")),
        ("test-plan", ("test-plan", "test plan", "测试方案", "测试计划")),
        ("audit-report", ("harness-audit", "audit-report", "audit report", "审计报告")),
        ("release-notes", ("release-notes", "release notes", "changelog", "发布说明")),
        ("implementation-plan", ("implementation-plan", "/plans/", "实施计划", "开发计划")),
        ("prd", ("requirement", "prd", "用户故事", "需求文档")),
        ("adr", ("adr-", "/adr", "decision", "技术决策")),
        ("evaluation", ("evaluation", "eval", "评测")),
        ("finding", ("finding", "发现项")),
        ("runbook", ("runbook", "运维手册")),
        ("skill", ("skill", "capability")),
        ("schema", ("schema",)),
        ("reference", ("reference",)),
        ("source", ("source", "raw/", "来源")),
        ("concept", ("concept", "wiki/", "概念")),
    )
    for category, needles in rules:
        if _contains(text, *needles):
            return category, True
    if kind == "solution":
        return "tech-solution", True
    if kind == "source":
        return "source", True
    if kind == "concept":
        return "concept", True
    return "document", False


def _infer_importance(category: str) -> str:
    if category in {"prd", "tech-solution", "adr", "test-plan", "audit-report", "evaluation", "finding", "release-notes"}:
        return "core"
    if category in {"implementation-plan", "runbook", "skill", "concept"}:
        return "normal"
    return "supporting"


def _infer_visibility(relative_path: str, source: str, category: str) -> str:
    normalized = "/" + relative_path.replace("\\", "/").casefold().strip("/") + "/"
    if any(
        marker in normalized
        for marker in (
            "/.claude/",
            "/tests/",
            "/test/",
            "/fixtures/",
            "/skill-fixtures/",
            "/templates/",
        )
    ):
        return "hidden"
    file_name = normalized.rstrip("/").rsplit("/", 1)[-1]
    if file_name in {"readme.md", "agents.md", "claude.md"}:
        return "secondary"
    if category in {
        "prd",
        "tech-solution",
        "adr",
        "test-plan",
        "audit-report",
        "evaluation",
        "finding",
        "release-notes",
        "implementation-plan",
        "runbook",
        "skill",
    }:
        return "primary"
    if source == "vault" and category == "concept":
        return "primary"
    return "secondary"


def _explicit_choice(
    metadata: Mapping[str, Any],
    field: str,
    allowed: tuple[str, ...] | None,
    warnings: list[ClassificationWarning],
) -> str | None:
    raw_value = metadata.get(field)
    if raw_value is None:
        return None
    value = str(raw_value).strip().casefold()
    valid = value in allowed if allowed is not None else bool(SLUG_PATTERN.fullmatch(value))
    if valid:
        return value
    warnings.append(
        ClassificationWarning(
            field=field,
            value=str(raw_value),
            message=f"Invalid graph classification value for {field}",
        )
    )
    return None


def classify_document(
    metadata: Mapping[str, Any],
    relative_path: str,
    *,
    source: str,
    kind: str,
) -> tuple[GraphClassification, tuple[ClassificationWarning, ...]]:
    metadata_text = _normalized_text(metadata, "", kind)
    path_text = _normalized_text({}, relative_path, "")
    metadata_stage, metadata_stage_matched = _infer_stage(metadata_text)
    path_stage, path_stage_matched = _infer_stage(path_text)
    inferred_stage = metadata_stage if metadata_stage_matched else path_stage
    stage_matched = metadata_stage_matched or path_stage_matched
    metadata_domain, metadata_domain_matched = _infer_domain(metadata_text)
    path_domain, path_domain_matched = _infer_domain(path_text)
    inferred_domain = metadata_domain if metadata_domain_matched else path_domain
    domain_matched = metadata_domain_matched or path_domain_matched
    metadata_category, metadata_category_matched = _infer_category(metadata_text, kind)
    path_category, path_category_matched = _infer_category(path_text, "")
    inferred_category = (
        metadata_category if metadata_category_matched else path_category
    )
    category_matched = metadata_category_matched or path_category_matched
    inferred_importance = _infer_importance(inferred_category)
    inferred_visibility = _infer_visibility(relative_path, source, inferred_category)
    warnings: list[ClassificationWarning] = []

    explicit_stage = _explicit_choice(metadata, "stage", GRAPH_STAGES, warnings)
    explicit_domain = _explicit_choice(metadata, "domain", None, warnings)
    explicit_category = _explicit_choice(metadata, "category", None, warnings)
    explicit_importance = _explicit_choice(metadata, "importance", GRAPH_IMPORTANCE, warnings)
    explicit_visibility = _explicit_choice(metadata, "graphVisibility", GRAPH_VISIBILITY, warnings)
    explicit_values = (
        explicit_stage,
        explicit_domain,
        explicit_category,
        explicit_importance,
        explicit_visibility,
    )
    if any(explicit_values):
        origin = "frontmatter"
    elif stage_matched or domain_matched or category_matched or inferred_visibility != "secondary":
        origin = "rule"
    else:
        origin = "fallback"

    return (
        GraphClassification(
            stage=explicit_stage or inferred_stage,
            domain=explicit_domain or inferred_domain,
            category=explicit_category or inferred_category,
            importance=explicit_importance or inferred_importance,
            visibility=explicit_visibility or inferred_visibility,
            origin=origin,
        ),
        tuple(warnings),
    )
