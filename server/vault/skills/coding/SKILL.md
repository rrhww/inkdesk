---
name: coding
description: 在方案已确认后执行受控代码实现。当 tech-review 通过且用户确认进入实现阶段时触发。不应在方案未确认、或有未解决的 Hard Gate 阻塞时触发。
---

# coding

## 核心目标与边界

在技术方案已确认的前提下，执行受控代码实现：

- **做**：按方案拆解任务 → 逐模块实现 → 保持与方案一致 → 记录实现偏差
- **不做**：修改技术方案（如需调整，返回 tech-solution）；执行未经确认的架构级变更

## Hard Gates

- `required_input`（solution_doc + tech_review_report）：方案和评审报告均不得为空
- `review_approved`：tech-review 必须已通过
- `human_confirmation`：用户必须显式确认进入实现

## 主流程

1. **方案理解** — 加载方案文档和 review report，理解需要实现的模块和接口
2. **任务拆解** — 将方案拆解为可独立验证的实现步骤
3. **逐模块实现** — 按依赖顺序实现：接口定义 → 核心逻辑 → 边界处理 → 错误路径
4. **一致性检查** — 每个模块完成后对照方案确认接口契约和数据流一致
5. **偏差记录** — 若实现过程中发现方案需要调整，记录偏差，不擅自大改架构
6. **变更记录** — 所有代码变更关联到 Dev Run 记录

## 关键决策点

- 发现方案不可行或需要重大调整时：暂停实现，记录发现，返回 tech-solution 修正方案
- 小范围优化（不改变接口）可直接执行，但需在变更记录中说明
- 涉及数据库 migration 或 API breaking change 时：必须先获得用户确认

## 需要读取的资源

- `references/`：代码规范（coding-standards），架构约束（architecture-constraints）

## 输出规格与验证

- 输出：代码变更 + 实现记录（保存到 `runs/<run_id>/coding-log.md`）
- 验证：实现与方案接口一致；所有变更在 Dev Run 中可追溯；关键路径有测试覆盖

## 下游衔接

- → [test-prep]：实现完成后，进入测试准备
