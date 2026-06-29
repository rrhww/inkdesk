---
name: ingest-source
description: 摄入 raw 材料，提取 Insight 并生成 wiki 审阅提案。当用户上传文档、导入资料或要求摄入新知识源时触发。不应在 wiki 已有相同材料的纯查重场景、或材料格式不可解析时触发。
---

# ingest-source

## 核心目标与边界

将 raw 材料（文档、代码片段、对话记录、网页内容）转化为结构化的 wiki 提案：

- **做**：解析内容、提取实体/概念/关系、生成 Insight、产出可审阅的 wiki 变更提案
- **不做**：直接写 accepted wiki；判断材料质量（那是 human review 的职责）；执行代码或运行脚本

## Hard Gates

- `required_input`（source_content）：raw 材料不得为空
- `vault_initialized`：KB 未初始化时返回 blocked
- `schema_gate_passed`：当前 wiki schema 不合规时阻止 ingest，先修复 schema

任一 gate 失败 → 停止并报告阻塞原因。

## 主流程

1. **解析** — 识别材料格式（Markdown/纯文本/代码/HTML），提取可读文本
2. **实体抽取** — 识别材料中的关键实体（文件、函数、概念、依赖），对照现有 wiki 判断哪些是新实体
3. **Insight 提取** — 从材料中提取可复用知识：模式、约束、关系、边界条件
4. **冲突检查** — 对比现有 wiki 页面，标记冲突或矛盾
5. **提案生成** — 将 Insight 格式化为 wiki proposal（页面新增 / 内容追加 / 状态更新），写入 ingest 审阅队列
6. **索引更新** — 更新 index.md 中的新条目引用

## 关键决策点

- 材料包含多主题时：拆分为多个独立提案还是一个综合提案？优选拆分，每个提案单一职责
- 材料与现有 wiki 矛盾时：标记冲突而非静默覆盖，提案中注明矛盾点和来源
- 材料质量不足以提取 Insight 时：生成摘要提案，标记 `status: stub`

## 需要读取的资源

- `references/`：entity-extraction-rules（实体识别规则），proposal-template（提案格式模板）

## 输出规格与验证

- 输出：一个或多个 wiki proposal，保存到 `ingest/`
- 验证：每个 proposal 包含 source 引用、受影响页面列表、变更类型（new/update/deprecate）
- 提案格式符合 `schema/wiki-page-template.md`

## 下游衔接

- → [patch-wiki-page]：审阅通过后，由 patch-wiki-page 执行实际 wiki 写入
