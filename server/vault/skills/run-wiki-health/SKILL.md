---
name: run-wiki-health
description: 执行 wiki 健康检查——断链、孤页、缺 frontmatter、缺来源引用、短页、stale/outdated 标记。当用户询问知识库质量或需要健康报告时触发。不应在 wiki 尚未初始化的空库中触发。
---

# run-wiki-health

## 核心目标与边界

对 wiki 知识库执行自动化健康检查并产出可操作的修复建议：

- **做**：扫描全库结构问题、报告具体问题位置、给出修复优先级、生成健康分
- **不做**：自动修复问题（修复由 patch-wiki-page 执行）；评判内容正确性（那是评测的职责）

## Hard Gates

- `vault_initialized`：KB 未初始化时返回 blocked
- `schema_gate_passed`：schema 不合规时先提示修复 schema，再执行检查

## 主流程

1. **结构扫描** — 检查所有页面的 frontmatter 完整性、目录结构合规性
2. **链接检查** — 扫描所有 `[[wikilink]]` 和 markdown 链接，检测断链和孤页
3. **内容质量** — 检测短页（<200 字非 stub 页面）、缺来源引用的 accepted 页面
4. **时效性** — 扫描 `updated_at` 超过 90 天的页面，标记为 stale；检查显式 outdated 标记
5. **重复检测** — 扫描标题相似度高的页面对，提示可能重复
6. **报告生成** — 汇总所有问题，按严重度（ERROR/WARN/INFO）分级，生成健康分和趋势

## 关键决策点

- 短页但标记为 `stub` 的不报告为问题——那是故意的
- 孤页但被 index.md 列出的不报告——有入口路径
- 健康分趋势：对比上次健康检查记录，标记改善/恶化/稳定

## 需要读取的资源

- `references/`：健康检查项定义（health-check-items），评分公式（scoring-formula）

## 输出规格与验证

- 输出：健康报告（health-report.md）+ 问题列表 + 健康分 + 趋势 + 修复建议
- 验证：每个报告的问题有具体位置（文件路径 + 行号）；健康分可追溯计算公式
- 报告保存到 `runs/<run_id>/health-report.md`

## 下游衔接

- → [patch-wiki-page]：如需修复，用户可触发 patch-wiki-page 对每个问题页面生成修复提案
