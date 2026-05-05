# Inkvault Python Main Backend Rewrite Design

## Summary

把当前 `Java Spring Boot server + Python agent sidecar` 重构为一个统一的 **Python 主后端**，同时保留现有 `Next.js` 前端不变。新后端需要继续服务当前产品形态：单人私有、vault-first、`raw -> ingest -> wiki -> ask` 主路径，以及“AI 只能生成可审阅提案，不能静默写 wiki”的产品边界。

## Confirmed Decisions

- 保留 `Next.js` 前端，不改成 Python 前端
- 主后端从 Java 一次性替换成 Python
- 只保留前端当前真正使用的主路径 API
- 沿用当前 PostgreSQL 表结构和 vault markdown 约定
- 把现在的 `agent-service` 并入新的 Python 主后端
- LangGraph 成为主 runtime，deterministic fallback 仅作为开发与降级兜底

## Goals

- 对前端保持兼容的主路径 API 契约
- 对数据库保持兼容的表结构与数据语义
- 对 vault 保持兼容的 `raw/`、`wiki/`、`AGENTS.md` 初始化与 markdown/frontmatter 格式
- 把 Ask / Compile agent runtime 内嵌到主后端
- 移除 Java/Maven 作为主运行时依赖

## Non-Goals

- 不重做前端
- 不保留 `/topics`、`/sources`、`/review` 等兼容别名接口
- 不在本轮引入多 agent graph、自治循环或任务执行系统
- 不重设计数据库和 vault 结构

## Target Architecture

新的 `server/` 将变成一个 Python 服务，采用 `FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic + LangGraph`。

### Runtime shape

- `FastAPI` 负责 HTTP API
- `SQLAlchemy async` 负责 PostgreSQL 访问
- `LangGraph` 负责 `ask` 与 `compile` 的主 runtime
- `VaultService` / `VaultMarkdownService` 继续负责 vault 初始化、路径安全与 markdown 渲染
- `ResearchWorkspaceService` 继续作为主业务编排层，统一组织 raw、ingest、wiki、ask 流程

### Directory shape

- `server/app/main.py`
- `server/app/api/`
- `server/app/core/`
- `server/app/db/`
- `server/app/models/`
- `server/app/repositories/`
- `server/app/services/`
- `server/app/agents/`
- `server/app/vault/`
- `server/alembic/`
- `server/tests/`

## Public API Scope

Python 主后端需要提供以下 API：

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/admin/home`
- `GET /api/raw`
- `POST /api/raw`
- `POST /api/raw/web`
- `POST /api/raw/pdf`
- `GET /api/ingest`
- `GET /api/ingest/{id}`
- `POST /api/ingest/{id}/accept`
- `POST /api/ingest/{id}/reject`
- `GET /api/wiki`
- `GET /api/wiki/{id}`
- `POST /api/ask`
- `POST /api/ask/{id}/writeback`
- `GET /health`

## Data Compatibility

### Database

- 继续使用现有 PostgreSQL 表
- 把当前 Flyway SQL 迁移复制为 Alembic 可执行迁移
- 数据模型字段名、主键格式、状态枚举语义保持兼容

### Vault

- 继续使用 `INKVAULT_VAULT_ROOT`
- 启动时确保 `raw/`、`wiki/`、`AGENTS.md` 存在
- 继续使用当前 raw/wiki markdown 模板
- 继续执行 vault 路径逃逸校验与原子写入

## Agent Integration

- `ask` graph：回答问题、给出 citation / confidence / knowledge gaps / follow-up questions
- `compile` graph：把新 raw 编译成 ingest proposal
- `writeback` 继续生成 review proposal，而不是直接改 wiki
- 当模型不可用时，使用 deterministic fallback 保持产品可用

## Migration Strategy

采用 **先建新 Python 后端，再切断 Java 运行路径** 的一次性替换策略：

1. 在 `server/` 下建立 Python 主后端骨架
2. 迁移配置、数据库访问、认证和 vault 能力
3. 迁移 raw / ingest / wiki / ask 主链路
4. 并入现有 `agent-service` 的 LangGraph runtime
5. 迁移测试与本地运行脚本
6. 跑通前后端验证后移除 Java/Maven 主路径

## Risks And Mitigations

- API 契约漂移
  - 用前端现有测试与 Python API 测试双重锁定
- 数据库兼容性问题
  - 优先复刻现有表结构和字段语义，不借迁移机会“顺手优化”
- vault 写入回归
  - 单独保留 vault 服务与测试，覆盖初始化、路径校验、写入、重建索引
- agent 层集成不稳
  - 先把 sidecar 中已验证的 LangGraph runtime 原样并入，再逐步增强

## Verification

- `server`: `pytest`
- `web`: `npm test`
- `web`: `npm run typecheck`
- `web`: `npm run lint`
- `web`: `npm run build`

## Success Criteria

- 前端无需改 API 调用方式即可继续跑通主路径
- Python 后端独立提供当前主产品所需全部主路径 API
- LangGraph 不再依赖独立 sidecar
- Java 后端不再是运行前提
