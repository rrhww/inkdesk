---
name: tech-review
description: 结构化审查技术方案——检查边界、风险、依赖、测试覆盖和实现可行性。每条结论必须附带 evidence。当存在待审技术方案时触发。不应在没有方案文档或方案为草稿大纲时触发。
---

# tech-review

## 核心目标与边界

对技术方案执行结构化审查，确保方案在进入 coding 前通过关键质量门禁：

- **做**：逐项检查边界/风险/依赖/测试/可行性，输出带 evidence 的 review report
- **不做**：判断方案是否符合业务需求（那是 human review 的职责）；修改方案内容（返回给 tech-solution 修正）

## Hard Gates

- `required_input`（solution_doc）：待审方案文档不得为空
- `artifact_exists`（solution_doc）：方案文件必须真实存在

## 主流程

1. **方案加载** — 读取方案文档，理解方案的范围和设计
2. **维度审查** — 按 checklist 逐项检查：

   | 维度 | 检查项 |
   |------|--------|
   | 边界 | 方案是否明确做了什么和不做什么 |
   | 风险 | 是否识别了关键风险并给了缓解措施 |
   | 依赖 | 外部依赖是否显式声明，版本和风险是否明确 |
   | 接口 | 对外接口是否足够精确（输入/输出/错误） |
   | 数据流 | 数据从哪来、经过哪些步骤、最终落到哪 |
   | 测试覆盖 | 方案是否给出了测试范围和关键验收点 |

3. **证据收集** — 每个维度的结论必须附带方案文档中的具体引用或代码仓中的证据
4. **Report 输出** — 结构化 review report：通过项 / 需要修正项 / 阻塞项

## 关键决策点

- 阻塞项出现时：review 结果为 FAILED，列出每个阻塞项和修正建议
- 方案过于简略无法评审时：返回状态为 SKIPPED，明确要求补充内容后重新提交
- reviewer 不生成替代方案，不接管方案设计职责

## 需要读取的资源

- `references/`：review-checklist（检查项详细说明）

## 输出规格与验证

- 输出：review report（保存到 `runs/<run_id>/tech-review.md`）
- 验证：每个 findings 有 evidence 引用；阻塞项有明确的修正方向

## 下游衔接

- → [coding]：review PASSED 后，用户确认进入 coding
- → [tech-solution]：review 需要修正时返回
