---
name: minimal-reviewer
description: 一个最小合法 reviewer Skill，用于验证校验器能正确识别 reviewer 类型 package。reviewer 保留结构化检查项，结论必须有 evidence。不应被实际触发执行。
---

# Minimal Reviewer

## 核心目标与边界

仅用于测试，不做任何实际工作。检查项统一以结构化列表输出，每条结论附带证据引用。

## Hard Gates

- required_input: review_target — 待审查内容不得为空
- on_failure: 返回 blocked，不生成空结论
