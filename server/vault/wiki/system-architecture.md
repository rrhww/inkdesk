---
type: concept
created: 2026-07-10
updated: 2026-07-10
tags: [架构, 技术栈, 控制面, 执行面]
related: [ai-rd-automation-llm-wiki, product-roadmap, tech-decisions]
source_file: docs/architecture/系统总览.md
status: stable
---

# 系统架构与技术栈

## 定位

Inkdesk 是单人私有、vault-first 的 AI R&D Automation Runtime，非公开发布系统。用户感知主路径为 `PRD/研发任务 -> Dev Run -> Review/Deposit`；内部围绕可审计研究闭环 `raw -> ingest -> wiki -> ask` 展开。

## 核心技术栈

- 前端：Next.js（App Router，同源 API 代理 `/api/**` -> 后端）
- 后端：FastAPI / Python
- Agent runtime：LangGraph（知识层有状态编排）
- 数据库：PostgreSQL（索引/关系/队列/问答记录，非最终真相）
- 对象存储：MinIO
- 内容事实来源：Vault Markdown（`raw/` 和 `wiki/` 是长期真相，DB 缺失时允许从 vault frontmatter 回补）

## 控制面与执行面边界（核心设计）

Inkdesk **不试图替代外部 Agent**（Claude Code/Codex），而是明确分工：

- **Inkdesk 控制面**（LangGraph 编排）：Context Pack 准备、技术方案生成与评审、gate 检查、coding briefing 组装、test-fix 过程追踪、deposit 与知识沉淀、评测
- **外部 Agent 执行面**：读代码仓/写文件、执行 coding、跑测试、debugging 修复

LangGraph 编排的是知识层有状态流程，不是代码生成。Harness 桥接两端：gate 放行时组装 briefing 调用外部 Agent，Agent 完成后通过 run_event 回写，Harness 推进下一阶段。

## 仓库结构

- `web/` — 前端（Next.js App Router）
- `server/` — 后端（FastAPI + SQLAlchemy）
- `infra/` — 基础设施模板
- `server/vault/` — Vault（raw + wiki + schema + skills + runs）

## 后端关键模块

- `main.py` — FastAPI 路由
- `models.py` — SQLAlchemy 模型
- `run_service.py` — Dev Run 状态机（6 阶段：context → solution → review → coding → testing → deposit）
- `stage_actions.py` — Stage action 执行（Skill-driven，hard gate 校验 + SKILL.md 注入 + wiki 检索）
- `skill_loader.py` — 从 vault/skills/ 加载 Skill package
- `hard_gate_checker.py` — 9 种 GateKind 校验
- `coding_session.py` — Claude Agent SDK 交互式 SSE 会话管理
- `mcp_services.py` — ContextPackService + VaultSearchService

## 前端关键路径

- `web/app/app/` — App Router 页面
- `web/components/workbench/stages/` — 6 个 stage panel 组件
- `web/lib/research.ts` — API 封装
- `web/lib/server-api.ts` — fetch 封装（读取响应体传递 error code/message）
- `web/lib/coding-stream.ts` — SSE 流式客户端

## 6 阶段 Dev Run

`context → solution → review → coding → testing → deposit`

每个 stage action 执行前：
1. 检查 Skill contract 的 hard gates（失败抛 409）
2. 注入 SKILL.md + references + templates 到 prompt
3. 从 wiki 检索相关页面注入 prompt（Query 操作）
4. 调用 LLM（DeepSeek）或外部 Agent（Claude Code SDK）执行
