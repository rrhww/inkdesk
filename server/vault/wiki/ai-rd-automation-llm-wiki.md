---
type: concept
created: 2026-07-10
updated: 2026-07-10
tags: [核心思想, llm-wiki, skill, evaluation]
related: [product-roadmap, system-architecture]
source_file: docs/references/AI研发自动化：Wiki知识库+技能包.md
status: stable
---

# AI 研发自动化：LLM-Wiki + 技能包

## 三大支柱

1. **LLM-Wiki 知识库** — 三层架构：L1 Sources（原始源，LLM 只读不写）、L2 Wiki（LLM 全权拥有的 markdown 集合，含实体页/概念页/综述页/对比页）、L3 Schema（写给 LLM 的工作规范）
2. **专家 SKILL 包** — 覆盖写技术方案、技术评审、coding、测试准备、测试修复、专业答疑、问题排查和全能管家路由，每个 Skill 包含 hard gate + phase 流程 + guard rails
3. **评测驱动质量保证** — Golden tasks + rubrics + promotion gate，阻止 blind prompt drift

## write-time vs query-time 合成

传统 RAG 在 query-time 用向量检索拼装临时答案，知识线性增长且质量不随用变好。LLM-Wiki 在 **write-time（摄入时）合成**，知识复利式增长（多一份源 = 整张网被重写），答案质量随每次问答持续变好。Wiki 是一个持续编译、持续保鲜的 compounding artifact。

## 三大核心操作

- **Ingest（摄入）**：一次触达多页，读源 → 写摘要页 → 更新被影响的实体/概念页 → 更新 index → 追加 log
- **Query（查询）**：基于 wiki 答题并要求"好答案写回 wiki"，让探索也变成沉淀而非消失在聊天历史
- **Lint（巡检）**：定期自检矛盾、过时、孤页、缺失概念和交叉引用

## Inkdesk 实现映射

- L1 Sources → `vault/raw/`（待 ingest 的原始资料）
- L2 Wiki → `vault/wiki/`（已审阅的合成知识）
- L3 Schema → `vault/schema/`（wiki-page-template、ask-answer-rules 等）
- SKILL 包 → `vault/skills/<skill_id>/`（SKILL.md + contract.json + references/templates）
- Query 操作 → `_search_wiki_for_context()`，stage action 执行时从 wiki 检索注入 prompt
- write-time 合成 → ingest-source skill + compile_worker + review_items 审阅流程

## 核心设计原则

- AI 不能直接写 wiki，所有编译和 writeback 结果先进入 review_items，只有 owner 接受后才落入 wiki/
- 知识在 write-time 合成（wiki），query-time 直接读结论
- Skill 的 hard gate 在 stage action 执行前校验，失败抛 409 阻塞执行
