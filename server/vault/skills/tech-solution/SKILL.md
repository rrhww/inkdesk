---
name: tech-solution
description: 从需求描述、KB 上下文和代码仓状态生成可评审技术方案。当用户提供了需求且 KB 已就绪时触发。不应在没有明确需求、或 KB 完全空白无法提供上下文的场景下触发。
---

# tech-solution

## 核心目标与边界

从需求出发，结合知识库和代码仓上下文，生成结构化、可评审的技术方案：

- **做**：理解需求 → 调研现有系统 → 产出方案（架构/模块/接口/数据流/风险）
- **不做**：执行任何代码变更；替代 tech-review 做方案审查

## Hard Gates

- `required_input`（requirement）：需求描述不得为空
- `vault_initialized`：KB 未初始化时返回 blocked
- `schema_gate_passed`：wiki schema 不合规时提示但允许继续（方案写作不直接写 wiki）

## 主流程

1. **需求理解** — 解析需求的业务目标、边界条件和非功能约束
2. **上下文调研** — 从 KB 中检索相关模块、已有接口、约束规则；从代码仓获取当前架构状态
3. **方案设计** — 四路并发完成需求、知识库、代码仓和安全分析，再综合输出方案概述 + 模块拆分 + 接口设计 + 数据流 + 风险与假设 + 测试范围建议
4. **输出格式化** — 使用 `templates/solution-template.md` 生成标准方案文档

## 关键决策点

- 需求中有歧义时：列出多种理解和对应方案，不做单一选择
- 方案存在外部依赖风险时：显式标记为"待确认"
- KB 相关信息不足时：在方案中标记信息缺口，建议先补充 wiki

## 需要读取的资源

- `references/`：架构决策模式（architecture-patterns）
- `templates/`：方案模板（solution-template.md）

## 输出规格与验证

- 输出：提案技术方案文档（保存到 `wiki/generated/<prd-stem>-tech-solution.md`）
- 验证：YAML Frontmatter、需求反向链接、方案概述、模块职责、接口契约、数据流、风险、测试范围和 Mermaid `sequenceDiagram`
- 仅覆盖由 Inkdesk 为同一来源生成的既有提案；写入使用原子替换。

## 下游衔接

- → [tech-review]：方案产出后，由 tech-review 进行结构化评审
