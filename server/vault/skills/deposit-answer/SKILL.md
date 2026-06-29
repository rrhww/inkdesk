---
name: deposit-answer
description: 将回答中有复用价值的知识片段沉淀为 wiki 审阅提案。当 answer-from-wiki 或 problem-solve 的输出中包含可被 wiki 收录的结构化知识时触发。不应在内容纯属一次性对话、无长期保留价值时触发。
---

# deposit-answer

## 核心目标与边界

从回答中提取值得长期保存的知识片段，格式化为 wiki proposal：

- **做**：识别可复用片段、提取事实/模式/规则、生成 wiki proposal、关联来源
- **不做**：判断回答正确性（那是 answer-from-wiki 的职责）；直接写 accepted wiki

## Hard Gates

- `required_input`（answer_content）：待沉淀的回答内容不得为空
- `vault_initialized`：KB 未初始化时返回 blocked

## 主流程

1. **片段识别** — 从回答中找出具有复用价值的知识片段（能被未来类似问题用到的信息）
2. **去重检查** — 对照 wiki 现有内容，过滤已有记录的知识
3. **关联标记** — 为每个片段标注来源回答、原始问题和上下文
4. **页面匹配** — 判断每个片段应写入哪个已有 wiki 页面，或需要新建页面
5. **提案生成** — 格式化为 wiki proposal，进入 ingest 审阅队列

## 关键决策点

- 片段是更新现有页面还是新建页面：已有相关页面则更新，完全新领域则新建
- 片段价值判断：优先沉淀「事实」和「规则」，其次沉淀「解释」，不沉淀「临时状态」
- 一个回答包含多个独立片段时：拆分为多个独立 proposal

## 需要读取的资源

- 无额外资源。核心逻辑在 SKILL.md 正文。

## 输出规格与验证

- 输出：一个或多个 wiki proposal，每个包含片段内容、来源回答引用、目标页面
- 验证：proposal 与来源回答可追溯，不包含纯对话性内容

## 下游衔接

- → [patch-wiki-page]：审阅通过后执行写入
