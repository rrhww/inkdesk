# Inkdesk

Inkdesk 是一个本地优先的研发知识图谱工作台。它扫描 Vault 与代码仓库中的 Markdown，解析文档关系，并在可搜索、可缩放的 React Flow 画布中展示完整拓扑。

## 当前能力

- 文件图谱：扫描 `INKDESK_VAULT_ROOT/wiki` 与 `INKDESK_REPO_ROOT` 中的 Markdown。
- 实时更新：Watchdog 监听文件变化，通过 SSE 推送新快照。
- 图谱降噪：模块分组、GLOBAL / TASK / MACRO 视图与语义缩放。
- 文档阅读：侧滑 Markdown 阅读器、代码高亮和 Mermaid 安全渲染。
- DAG 引擎：纯内存 Kahn/BFS 调度和 SSE 流式结果，不依赖任务表或数据库。

## 架构

```text
Markdown files
      |
      v
FastAPI graph index + in-memory DAG engine
      |  JSON / SSE
      v
Next.js knowledge graph workbench
```

PostgreSQL、pgvector、持久化 Job 队列和旧 CRUD 页面不在当前运行链路中。

## 本地启动

后端需要 Python 3.12+：

```powershell
Set-Location server
python -m pip install -e ".[dev]"
python -m uvicorn inkdesk_server.main:app --host 127.0.0.1 --port 8080
```

新开终端启动前端（Node.js 20.9+）：

```powershell
Set-Location web
npm install
npm run dev
```

打开 `http://localhost:3000/app/wiki`。前端默认代理到 `http://localhost:8080`，也可通过 `INKDESK_API_BASE_URL` 覆盖。

## Docker

```powershell
Copy-Item infra/.env.example infra/.env
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml up -d --build
```

Docker 组合只包含 Web 和 FastAPI 服务；Markdown Vault 使用具名卷，仓库以只读方式挂载给图谱扫描器。

## 验证

```powershell
Set-Location server
python -m pytest -q

Set-Location ../web
npm test
npm run typecheck
npm run lint
npm run build
npm run e2e
```

## 核心接口

- `GET /health`
- `GET /api/graph?source=vault|repo`
- `GET /api/graph/document?nodeId=...`
- `GET /api/graph/stream?source=vault|repo`
- `GET /api/engine/health`
- `POST /api/engine/stream`

## 仓库结构

```text
web/       Next.js 图谱工作台与前端测试
server/    FastAPI 文件索引、DAG 引擎与 Skill SDK
infra/     无数据库依赖的本地容器配置
docs/      设计、决策与历史交付资料
```
