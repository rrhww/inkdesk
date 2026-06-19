"""
Vault 初始化共享资产：manifest 与默认 Markdown 内容。

所有内容均源自设计文档《知识库初始化设计》的约定。
支持代码项目型（code）与通用知识型（general）两类 Vault。
"""

from __future__ import annotations

from typing import NamedTuple


class DefaultAsset(NamedTuple):
    relative_path: str
    content: str


# 所有类型共享的顶层目录
SHARED_DIRS = ["raw", "wiki", "schema", "skills", "evals", "runs"]

# 按类型区分的 wiki 子目录
VAULT_TYPE_WIKI_DIRS = {
    "code": ["wiki/entities", "wiki/concepts"],
    "general": ["wiki/topics", "wiki/sources", "wiki/queries"],
}

# 仅对代码项目型创建空占位，通用知识型不需要
VAULT_TYPE_ONLY_DIRS = {
    "code": [],
    "general": [],
}

# 所有类型共享的默认文件
SHARED_FILES: list[DefaultAsset] = []


def _register(path: str, content: str) -> DefaultAsset:
    asset = DefaultAsset(relative_path=path, content=content)
    SHARED_FILES.append(asset)
    return asset


_register(
    "AGENTS.md",
    """# Inkdesk LLM Wiki Agents

This vault follows the raw -> ingest -> wiki workflow.

- raw/ stores imported webpages, PDFs, and migrated internal notes.
- ingest is a review workflow, not a durable content directory.
- wiki/ stores accepted, settled knowledge pages.
- Never silently edit wiki knowledge without a review decision.
- Preserve backlinks from every compiled claim to raw source material.
""",
)

_register(
    "wiki/index.md",
    """# 知识库目录

## 按页面类型
### 概念
（自动或手动维护的概念页列表）

### 实体
（自动或手动维护的实体页列表）

### 来源摘要
（自动或手动维护的来源摘要列表）

### 问答存档
（自动或手动维护的查询存档列表）

## 统计
- 总页数：
- 概念页：
- 实体页：
- 来源摘要：
- 最后更新：
""",
)

_register(
    "wiki/log.md",
    """# 操作日志

## {date} | 初始化 | 知识库初始化完成
- 创建目录结构
- 生成 Schema 文件
""",
)

_register(
    "KB-META.md",
    """# KB-META

## 基本信息
- name: {name}
- created: {date}
- schema_version: 1.0

## 目录结构
- raw: raw/
- wiki: wiki/
- schema: schema/
- skills: skills/
- evals: evals/
- runs: runs/

## 关联资源
- code_repo:
- related_kbs:

## 当前统计
- 概念页：
- 实体页：
- 来源摘要：
- 总页数：
""",
)

_register(
    "schema/vault-layout.md",
    """# Vault 目录约定

## 目录职责
- `raw/`：原始材料。Agent 只读，不可修改。
- `wiki/`：已接受的长期知识页。Agent 可以提案修改，但必须经 owner 审阅。
- `schema/`：本目录。Agent 的维护规则。
- `skills/`：可复用工作流定义。
- `evals/`：评测任务和评分标准。
- `runs/`：Agent 运行记录。

## 文件命名
- 知识页：`{主题关键词}.md`，使用连字符分隔
- 来源摘要：`{来源标题}.md`
- 问答存档：`YYYY-MM-DD-{问题关键词}.md`

## 新增页面的规则
- 先检查是否已有同主题页面（搜索 wiki/ 目录）
- 新页面必须至少有一个 inbound 链接
- 创建后更新 index.md
""",
)

_register(
    "schema/wiki-page-template.md",
    """# Wiki 页面模板

## 所有页面必须
- 包含完整的 frontmatter（type / created / updated / tags / related / source_file / status）
- 至少有一个 inbound 链接（从其他页面指向它）
- 引用来源时使用 `[[来源页名]]` 格式

## 概念页（type: concept）
详见 `templates/concept-page.md`

## 实体页（type: entity）
详见 `templates/entity-page.md`

## 来源摘要页（type: source）
详见 `templates/source-summary.md`

## 状态流转
stub → draft → stable → outdated
- stub：刚创建，内容不完整
- draft：主要内容已填充，待补充细节
- stable：内容完整，来源清晰
- outdated：内容可能过时，待更新
""",
)

_register(
    "schema/source-citation-rules.md",
    """# 来源引用规则

## 强制要求
- 每个知识页的 claims 必须能追溯到 raw 来源或已接受的 wiki 页面
- 来源引用格式：`[[来源页名]]` 或 `[标题](raw/路径)`
- 从外部网页或 PDF 提取的信息，必须先创建来源摘要页再引用

## 禁止行为
- 不得编造不存在的来源
- 不得引用已被拒绝的提案
- 不得引用不存在或已删除的 raw 文件
""",
)

_register(
    "schema/ingest-proposal-rules.md",
    """# 摄入提案规则

## 提案类型
- new-topic：创建新知识页
- patch-topic：修改已有知识页
- open-question：标记待澄清问题
- conflict-resolution：解决知识冲突

## 提案必须包含
- 提案类型
- 目标页面路径
- 变更说明（新增/修改/删除的内容）
- 来源依据
- 影响的关联页面列表

## 审阅规则
- 提案未经 owner 接受前不得写入 wiki/
- 被拒绝的提案记录原因后归档
- 冲突提案需列出冲突双方并建议裁决方向
""",
)

_register(
    "schema/ask-answer-rules.md",
    """# 查询回答规则

## 查询优先级
1. 先搜索 wiki/ 中的已接受知识
2. 再搜索 raw/ 中的原始材料
3. 最后使用模型自身知识（需标注"模型知识，未经本知识库验证"）

## 回答格式
- 引用 wiki 页面时使用 `[[页面名]]` 格式
- 引用 raw 来源时附路径
- 不确定的内容标注"待验证"

## 沉淀建议
- 回答涉及新发现且不在 wiki 中 → 建议创建新页面
- 回答补充或修正了已有 wiki 内容 → 建议 patch
- 回答发现了知识矛盾 → 建议创建冲突裁决提案
""",
)

_register(
    "schema/wiki-health-rules.md",
    """# Wiki 健康检查规则

## 结构检查
- 缺 frontmatter：页面无 type / created / tags 字段
- 缺来源引用：stable 状态页面无 source_file 或内联引用
- 断链：`[[xxx]]` 指向不存在的页面
- 孤页：无任何 inbound 链接的页面
- 短页：内容少于 100 字符的页面（可能是 stub 但未标记）

## 内容检查
- 重复标题：两个页面标题相同或高度相似
- 过期标记：引用的 raw 文件已删除但页面未标记 outdated
- 矛盾检测：不同页面对同一事实的描述冲突

## 健康分计算
- 每项检查通过得 1 分，失败得 0 分
- 总分 / 检查项数 = 健康分（0-100）
- 低于 60 分触发维护提醒
""",
)
