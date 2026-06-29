---
name: patch-wiki-page
description: 修改已有 wiki 页面——补充内容、更新过时信息、标记页面状态。当 ingest-source/deposit-answer/run-wiki-health/extract-insight 产出了针对特定页面的变更提案，且提案已通过审阅时触发。不应在没有目标页面或变更内容为空时触发。
---

# patch-wiki-page

## 核心目标与边界

执行 wiki 页面的实际修改：

- **做**：追加内容、更新过时段落、修正错误、标记状态（stub/draft/stable/outdated）、更新交叉引用
- **不做**：判断变更内容的正确性（上游已审阅）；新建页面结构（那是 upstream proposal 的职责）

## Hard Gates

- `required_input`（target_page + patch_content）：目标页面和变更内容均不得为空
- `review_approved`：提案必须已经审阅通过
- `artifact_exists`（target_page）：目标页面必须存在

任一 gate 失败 → 停止，不执行写入。

## 主流程

1. **定位目标** — 读取目标页面的当前完整内容
2. **冲突检查** — 确认 patch 内容不会与近期其他变更产生写-写冲突
3. **执行合并** — 按 patch 类型（追加/替换/标记）修改页面内容
4. **链接更新** — 检查并更新受影响页面的入链和出链引用
5. **元信息更新** — 更新页面 frontmatter（updated_at、status 等）
6. **记录变更** — 写入 log.md，记录变更类型、影响页面和来源提案

## 关键决策点

- patch 与当前页面内容冲突时：保留所有版本信息，生成冲突报告，不静默覆盖
- 页面不存在但需要新建时：不是本 Skill 的职责，返回给上游 proposal 重新生成

## 需要读取的资源

- `references/`：页面模板（page-template），frontmatter 规范（frontmatter-spec）

## 输出规格与验证

- 输出：修改后的 wiki 页面 + log.md 更新 + 受影响页面的链接更新
- 验证：页面内容包含变更且未丢失原有信息；log.md 记录了变更；链接无新增断链

## 下游衔接

- 无固定下游。写操作完成后返回给调用方。
