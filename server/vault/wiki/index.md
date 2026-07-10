# 知识库目录

## 按页面类型

### 概念
- [AI 研发自动化：LLM-Wiki + 技能包](ai-rd-automation-llm-wiki.md) — 三大支柱、write-time vs query-time 合成、Inkdesk 实现映射
- [产品路线图与阶段规划](product-roadmap.md) — 六大阶段、门禁要求、当前进度
- [系统架构与技术栈](system-architecture.md) — 控制面与执行面边界、技术栈、关键模块
- [技术决策与约束](tech-decisions.md) — 写入策略、Context Ask 策略、Claude Agent SDK 集成约束

### 实体
（自动或手动维护的实体页列表）

### 来源摘要
（自动或手动维护的来源摘要列表）

### 问答存档
（自动或手动维护的查询存档列表）

## 统计
- 总页数：4（含 index 和 log）
- 概念页：4
- 实体页：0
- 来源摘要：0
- 最后更新：2026-07-10

## Rules relevant to this file

Rule Name: e:\dev\projects\inkdesk\server\vault\AGENTS.md

```
# Inkdesk LLM Wiki Agents

This vault follows the raw -> ingest -> wiki workflow.

- raw/ stores imported webpages, PDFs, and migrated internal notes.
- ingest is a review workflow, not a durable content directory.
- wiki/ stores accepted, settled knowledge pages.
- Never silently edit wiki knowledge without a review decision.
- Preserve backlinks from every compiled claim to raw source material.
```
