# F03 模块化应用组合壳实施计划

> 日期：2026-07-14
> 状态：实现与验收完成；代码提交 `aef1c4f`，待推送并合并
> 路线图：[`2026-07-11-inkdesk-capability-platform-master-roadmap.md`](./2026-07-11-inkdesk-capability-platform-master-roadmap.md)
> 上位设计：[`2026-07-11-inkdesk-team-rd-capability-platform-design.md`](../specs/2026-07-11-inkdesk-team-rd-capability-platform-design.md)
> 前置依赖：F01 当前行为契约与恢复基线；F02 代码提交、合并和全量回归闭环
> 后续解锁：F04 默认 Organization 与 Capability Space、F05 Durable Job / Attempt Kernel 的模块化接入点
> 协作归属：用户负责编写失败测试、生产代码和执行验收；Codex 负责解释组合根、拆解步骤、审阅 diff 与验收证据

## 1. 单一交付目标

F03 只交付一项能力：**建立无运行时副作用、可独立测试的 FastAPI 应用组合壳，并用系统健康与 Vault 四个端点证明旧入口可以逐步迁入新模块而不改变外部行为。**

完成后必须成立：

```text
inkdesk_server.api.app.create_api_app(...)
-> 纯 FastAPI 壳
-> CORS + 统一错误处理
-> system health router + vault router
-> 不初始化数据库、不 seed、不启动 Worker、不构建或运行 MCP

inkdesk_server.main.create_app()
-> 保留现有运行时装配与生命周期
-> 调用纯 API 壳
-> 注册未迁移的 legacy routes
-> 最后挂载 /mcp
-> 保留 inkdesk_server.main:app 启动入口
```

F03 不是“把 `main.py` 全部拆完”，而是验证一种后续可重复使用的绞杀式迁移模式。验收关注的是模块边界已经可用、四个端点迁移成功、F01 契约完全不变，不以减少多少行代码作为完成标准。

## 2. 前置证据与实施门禁

### 2.1 F01 契约输入

F03 继续使用 F01 run `20260711T113950Z` 的已验收基线：

- 完整 manifest 为 `PASS`，10/10 必需 suite 通过，known issue 为 0。
- OpenAPI 权威快照位于 `docs/delivery/baselines/f01/contracts/openapi.json`。
- 代表性恢复读路径包含 `/actuator/health` 与 `/api/vault/status`。
- F03 不接受“语义相近”的新 OpenAPI；完整 canonical document 必须与 F01 快照相等。

### 2.2 F02 当前事实

F02 本地专项 verifier run `20260714T151606Z` 的 `overallStatus` 为 `PASS`，并已证明：

- PostgreSQL 空库升级通过。
- F01 数据库严格接管前后 schema hash、data hash 相等。
- unsupported schema、权限失败和 migration lock 故障注入通过。
- 接管后的 7 条只读路径通过。

但 F03 **实施前**仍必须确认以下交付事实，而不是依赖未提交工作树或聊天结论：

1. F02 实现已提交并合并到 F03 的基线分支。
2. F02 后端全量测试与 PostgreSQL integration 输出已审阅。
3. Docker 启动顺序与 `npm run e2e:fullstack` 输出已审阅。
4. F03 分支能从已合并基线干净创建，不 cherry-pick F02 的未提交代码。

不满足时可以确认和改进本计划，但不得开始 F03 生产代码。该门禁避免 F03 在旧 `init_db()` 语义上开发后再与 F02 冲突。

## 3. 当前问题与保留边界

### 3.1 当前组合根承担过多职责

`server/inkdesk_server/main.py` 当前约 760 行，`create_app()` 同时负责：

- 获取 Settings、检查数据库并写入 seed。
- 构建 MCP server 与 session manager。
- 获取并启动 Compile Worker。
- 定义 lifespan，再次检查数据库并写入 seed。
- 创建 FastAPI、安装 CORS 和三个异常处理器。
- 定义全部 HTTP routes。
- 挂载 `/mcp` 并暴露模块级 `app`。

这使得“创建一个用于路由测试的 FastAPI app”与“启动完整 Inkdesk 运行时”无法分离。F04/F05 若继续直接向该函数添加表、模块和 Worker，会把领域边界、进程生命周期与 HTTP 适配层进一步绑死。

### 3.2 首批迁移端点

F03 只迁移以下四个业务端点：

| 方法 | 路径 | 当前函数名 | 必须保留的 operation ID | 成功语义 |
| --- | --- | --- | --- | --- |
| `GET` | `/health` | `health` | `health_health_get` | `200 {"status":"ok"}` |
| `GET` | `/actuator/health` | `actuator_health` | `actuator_health_actuator_health_get` | `200`，`status` 为 `UP`，保留 retrieval health |
| `GET` | `/api/vault/status` | `vault_status` | `vault_status_api_vault_status_get` | `200`，响应模型仍为 `VaultStatusResponse` |
| `POST` | `/api/vault/initialize` | `vault_initialize` | `vault_initialize_api_vault_initialize_post` | `200`；请求校验错误仍为 FastAPI `422` |

函数名是 OpenAPI 契约的一部分。本计划禁止为了“风格统一”重命名这四个函数，也不显式指定一个不同的 `operation_id` 来掩盖迁移差异。

### 3.3 容易混淆但明确不迁移的端点

以下 Knowledge Health API 继续留在 `main.py`：

```text
GET  /api/health
POST /api/health/runs
GET  /api/health/runs
GET  /api/health/runs/{run_id}
```

`/health`、`/actuator/health` 属于系统可用性；`/api/health*` 属于知识健康业务。F03 必须用测试锁定这条语义边界，不能按字符串相似度一起搬迁。

## 4. 已敲定的架构决策

### 4.1 目标文件结构

```text
server/inkdesk_server/
  api/
    __init__.py
    app.py
    dependencies.py
    errors.py
    routers/
      __init__.py
      system_health.py
      vault.py
```

这是 HTTP 适配与应用组合边界，不是新的业务领域层。F03 不创建通用 `BaseRouter`、Repository 基类、Service Locator 或自动扫描路由机制。

### 4.2 纯 API 壳

`api/app.py` 暴露单一工厂：

```python
create_api_app(*, lifespan=None) -> FastAPI
```

该函数只负责：

1. 使用现有 `title="Inkdesk Python Server"`、`version="0.1.0"` 和传入的 lifespan 创建 FastAPI。
2. 按当前值安装 CORS。
3. 安装现有三类错误处理。
4. include system health 与 Vault routers。
5. 返回 app。

禁止在 `api/app.py` 中导入 `inkdesk_server.main`，也禁止调用 `init_db()`、`session_scope()`、`bootstrap_seed_data()`、`build_mcp_server()` 或 `get_compile_worker()`。导入 `inkdesk_server.api.app` 和调用 `create_api_app()` 都必须不依赖一个可用数据库。

### 4.3 `main.py` 保留运行时装配权威

F03 中 `main.py:create_app()` 仍是唯一 production composition root，按以下顺序工作：

1. 保留 F02 合并后已经确定的 database readiness 与 seed 时机。
2. 构建 MCP server、MCP app 与 session manager。
3. 获取并按当前时机启动 Compile Worker。
4. 定义现有 lifespan，保留 session manager 与 Worker shutdown 语义。
5. 调用 `create_api_app(lifespan=app_lifespan)`。
6. 注册所有未迁移的 legacy routes。
7. 最后挂载 `/mcp`。
8. 返回 app，并保留 `app = create_app()` 与 `inkdesk_server.main:app`。

F03 不借机修复 `create_app()` 中重复 readiness/seed、Worker 在工厂阶段启动或其他可疑生命周期问题。这些是后续独立计划的候选，混入 F03 会让行为兼容性无法判断。

### 4.4 依赖适配

`api/dependencies.py` 提供一个命名明确的 FastAPI dependency，内部继续调用：

```python
get_research_service(db, settings)
```

system actuator 与 Vault router 依赖该适配器，不直接在每个端点重复组装 DB 与 Settings。这样测试可以通过 `app.dependency_overrides` 注入 fake research service，同时保持当前服务行为不变。

F03 不把 `ResearchWorkspaceService` 拆成 Vault/Health 新 service，不移动 ORM query，也不引入依赖注入框架。这个 dependency 是 legacy service 与新 HTTP 模块之间的窄适配层。

### 4.5 错误与 CORS

`api/errors.py` 提供错误处理器安装函数，复用现有类型和响应模型：

- `ApiError`：保留其配置的 HTTP status 与 `{code, message}`。
- `ResourceNotFoundError`：保留 `404` 与 `{code:"NOT_FOUND", message}`。
- 未预期 `Exception`：保留 `500` 与 `{code:"INTERNAL_ERROR", message:"Unexpected server error."}`。

F03 不移动或重命名 `security.py` 中的异常，也不移动 `schemas.py` 中的 `ApiErrorResponse`。CORS 必须保持：

```text
allow_origins = ["http://localhost:3000"]
allow_credentials = true
allow_methods = ["*"]
allow_headers = ["*"]
```

## 5. 文件边界

| 操作 | 文件 | 单一职责 |
| --- | --- | --- |
| 新增 | `server/inkdesk_server/api/__init__.py` | 声明 API package，不产生副作用 |
| 新增 | `server/inkdesk_server/api/app.py` | 纯 FastAPI 壳、CORS、errors、router composition |
| 新增 | `server/inkdesk_server/api/dependencies.py` | legacy research service 的可覆盖依赖适配 |
| 新增 | `server/inkdesk_server/api/errors.py` | 安装现有错误处理语义 |
| 新增 | `server/inkdesk_server/api/routers/__init__.py` | 声明 routers package，不自动扫描 |
| 新增 | `server/inkdesk_server/api/routers/system_health.py` | `/health` 与 `/actuator/health` |
| 新增 | `server/inkdesk_server/api/routers/vault.py` | Vault status 与 initialize |
| 修改 | `server/inkdesk_server/main.py` | 调用 API 壳，删除四个旧内联 route 定义，保留其余运行时与 legacy routes |
| 新增 | `server/tests/api/test_app_shell.py` | 纯度、metadata、CORS、route inventory |
| 新增 | `server/tests/api/test_system_health_router.py` | 两个系统健康端点及 operation ID |
| 新增 | `server/tests/api/test_vault_router.py` | Vault dependency override、响应模型与 422 |
| 新增 | `server/tests/api/test_error_handlers.py` | 404/业务错误/500 body 兼容 |
| 新增 | `server/tests/api/test_runtime_composition.py` | 完整 app、legacy routes、MCP、生命周期和 OpenAPI 兼容 |
| 修改 | `cognitive-map.md` | 完成验收后记录组合根、纯壳边界与仍未理解的 legacy routes |

除非失败测试证明现有 fixture 无法隔离副作用，否则不修改全局 `server/tests/conftest.py`。不修改 `schemas.py`、`security.py`、research/Vault 业务实现、F02 migration 文件、MCP、Compile Worker 或任何 `web/**` 文件。

## 6. 分段实施计划

F03 分为三个连续增量。每个增量都由用户执行 Red -> Green -> Refactor -> 验证；前一个增量未通过并经 Codex 审阅，不进入下一个增量。

### 增量 A：建立纯应用壳

#### 任务 A1：先证明纯度与 metadata

**Red**

1. 新建 `test_app_shell.py`，导入 `inkdesk_server.api.app.create_api_app`。
2. 断言创建壳不调用数据库 readiness、seed、Worker 或 MCP 构建函数。
3. 断言 app title/version 与 F01 相同。
4. 确认测试因 `inkdesk_server.api` 尚不存在而失败，而不是因数据库不可用失败。

```powershell
cd server
python -m pytest tests/api/test_app_shell.py -q
```

**Green**

1. 创建 `api/` 与 `api/routers/` package。
2. 实现最小 `create_api_app(*, lifespan=None)`。
3. 此时只安装壳能力；不移动 legacy routes，不修改 `main.py`。

#### 任务 A2：抽出错误与 CORS 组合

**Red**

1. 在测试 app 上增加会抛出 `ApiError`、`ResourceNotFoundError` 与普通异常的测试端点。
2. 对普通异常使用不会把 server exception 直接抛回测试进程的 client 配置。
3. 断言 status 和响应 body 与第 4.5 节完全一致。
4. 发起来自 `http://localhost:3000` 的 CORS preflight，断言 origin、credentials、methods、headers 保持兼容。

**Green**

1. 在 `api/errors.py` 实现安装函数，不复制新的异常类。
2. 在 `api/app.py` 调用 error 与 CORS installer。
3. 不改变异常优先级和兜底消息。

**增量 A 验收**

```powershell
cd server
python -m pytest tests/api/test_app_shell.py tests/api/test_error_handlers.py -q
```

预期：纯壳无需数据库即可创建；metadata、CORS 和三类错误语义通过；当前 `main.py` 尚未切换。

### 增量 B：迁移 system health 与 Vault routers

#### 任务 B1：system health router

**Red**

1. 使用纯壳和 fake research service 测试 `GET /health` 与 `GET /actuator/health`。
2. 断言 `/health` 精确返回 `200 {"status":"ok"}`。
3. 断言 actuator 返回 `status: UP`，且 `retrieval` 原样来自 fake service。
4. 从 `app.openapi()` 断言两个 method/path、response schema 与 operation ID 完全保持。

**Green**

1. 在 `dependencies.py` 添加 legacy research service dependency。
2. 在 `system_health.py` 定义无 prefix 的 `APIRouter` 与两个原名函数。
3. 在 `api/app.py` include router。

#### 任务 B2：Vault router

**Red**

1. fake service 分别返回未初始化、已初始化 Vault 状态，断言 GET body 不被 router 重写。
2. POST `{"vaultType":"general"}`，断言 service 收到 `general` 且响应模型不变。
3. POST 缺少 `vaultType` 或类型非法 payload，断言仍由 FastAPI 返回 `422`。
4. 让 fake service 抛出一个现有 409 `ApiError`，断言 handler body 不变。
5. 断言两个 Vault operation ID 精确匹配第 3.2 节。

**Green**

1. 在 `vault.py` 定义两个原名函数并复用现有 request/response models。
2. 通过同一 legacy service dependency 调用 `get_vault_status()` 与 `initialize_vault(vault_type)`。
3. 在 `api/app.py` include router。

#### 任务 B3：最终 route inventory

在 `test_app_shell.py` 增加最终断言：

- 纯壳中恰好存在上述四个迁移业务 method/path；FastAPI 自带 docs/openapi routes 不计入业务 route 数。
- 每个业务 method/path 只出现一次。
- `/api/health` 与 `/api/health/runs*` 不在纯壳中。
- 壳创建两次不会共享 dependency override、route mutation 或其他可变状态。

**增量 B 验收**

```powershell
cd server
python -m pytest tests/api/test_app_shell.py tests/api/test_system_health_router.py tests/api/test_vault_router.py tests/api/test_error_handlers.py -q
```

预期：四个端点可以完全脱离 production lifecycle 测试；依赖可覆盖；没有 duplicate route；Knowledge Health 未被误迁移。

### 增量 C：切换 production composition root 并签收契约

#### 任务 C1：先锁定运行时装配

**Red**

1. 新建 `test_runtime_composition.py`，对 F02 合并后的 `main.create_app()` 建立调用顺序特征测试。
2. 断言 database readiness/seed、MCP 构建、Worker start、lifespan session run 与 Worker stop 的当前时机不变。
3. 断言 `inkdesk_server.main:app` 仍存在，`/mcp` 仍挂载且位于 legacy HTTP routes 之后。
4. 断言 `/api/health*` 仍只由 legacy main 注册。
5. 扫描完整 app 的 method/path 对，断言四个待迁移端点各出现一次；Red 阶段应因新旧 router 重复注册而失败。

**Green**

1. `main.py` 改为调用 `create_api_app(lifespan=app_lifespan)`。
2. 只删除四个已迁移的内联函数及其不再需要的 imports。
3. 保留所有其他 route 的文本与顺序，保留 `/mcp` 最后挂载。
4. 禁止在这一步重排 imports 之外的大段 legacy 代码或顺手抽取第五个 route。

#### 任务 C2：完整契约比较

**Red/验证**

1. 读取 checked-in F01 OpenAPI 快照。
2. 将完整 production app 的 canonical OpenAPI 与快照比较。
3. 若出现任何 diff，先定位 operation ID、response model、422 schema、route 顺序或 import 造成的差异；禁止直接更新快照。

本地 app 测试通过后，在 Docker 服务上再次执行独立比较：

```powershell
python scripts/f01/export_openapi.py compare `
  --url http://localhost:8000 `
  --snapshot docs/delivery/baselines/f01/contracts/openapi.json
```

如果本机映射端口不同，只替换 `--url`，不替换 snapshot。

#### 任务 C3：回归与文档签收

用户依次执行并保存输出：

```powershell
cd server
python -m pytest tests/api tests/test_health.py tests/test_compile_pipeline.py -q
python -m pytest

# 使用 F02 已认证的 PostgreSQL 测试环境
python -m pytest tests/migrations tests/test_pgvector_integration.py -q

cd ..
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml up -d --build

cd web
npm run e2e:fullstack
```

签收时审阅：

- Docker server 仍在 migration ready 后启动，`/health` 与 `/actuator/health` 可用。
- Vault 初始化和状态读取通过原全栈流程。
- MCP endpoint 与 Compile Worker 没有启动/关闭回归。
- 无新增前端代码，因此不要求视觉截图；full-stack 真实流程仍是必需证据。
- `cognitive-map.md` 已记录纯壳与 production composition root 的边界。

## 7. F03 完成门禁

只有以下条件全部成立，F03 才能标记完成并允许 F04/F05 依赖新组合壳：

1. F02 实现已提交合并，专项 verifier、后端全量、PostgreSQL integration 与 full-stack 证据已审阅。
2. `create_api_app()` 的导入和调用不初始化数据库、不 seed、不构建 MCP、不获取或启动 Worker。
3. 纯壳中只有四个迁移业务 method/path，每个只注册一次。
4. 四个 operation ID、response model、status code 和 response body 与 F01 完全兼容。
5. `/api/health*` 仍留在 legacy main，且完整 app 中没有 duplicate method/path。
6. CORS 与三类错误处理语义保持不变。
7. `main.create_app()` 的 F02 readiness/seed、MCP session 与 Compile Worker 生命周期保持不变。
8. `inkdesk_server.main:app` 与 `/mcp` mount 保持可用。
9. F01 完整 canonical OpenAPI 比较通过，不修改权威 snapshot。
10. F03 focused tests、后端全量、PostgreSQL integration 和 full-stack E2E 全部通过。
11. 没有业务 schema、数据库 revision、前端、Vault 数据或 API 行为变更。
12. `cognitive-map.md` 与路线图状态已更新，验证输出可追溯到 commit SHA。

任一 OpenAPI diff、duplicate route、纯壳产生运行时副作用、MCP/Worker 生命周期变化，或用更新 F01 snapshot 的方式消除 diff，都属于阻塞失败。

### 7.1 2026-07-15 实施与验收记录

- `api/app.py` 提供无运行时副作用的 `create_api_app()`；`main.create_app()` 仍是唯一 production composition root，并保留 readiness、seed、MCP、Worker 和未迁移 legacy routes 的所有权。
- 仅迁移 `GET /health`、`GET /actuator/health`、`GET /api/vault/status`、`POST /api/vault/initialize`；`/api/health*` 保留在 legacy main。
- focused API/runtime/OpenAPI 契约测试为 `23 passed`；其中 production `app.openapi()` 与 F01 checked-in canonical snapshot 完整相等。
- 后端全量测试为 `386 passed, 7 skipped`；PostgreSQL migration + pgvector 为 `17 passed, 1 skipped`。
- Docker 实测服务器在 `f02_0001` / `MANAGED_CURRENT` 后启动，`/health`、`/actuator/health`、`/api/vault/status` 均为 HTTP 200。镜像构建时显式规范化入口脚本为 LF，并以测试锁定 Windows CRLF 工作树的启动兼容性。
- Docker 服务的 `export_openapi.py compare --url http://localhost:8080` 与 F01 checked-in snapshot 比较通过。
- 隔离的真实全栈 Playwright 回归为 `10 passed`，覆盖 F01 关键浏览器流和 Dev Run 创建、Ask、Deposit、阶段推进、完成与非法状态转换。
- F03 代码实现与测试提交：`aef1c4f`（`feat: 建立 F03 模块化 API 组合壳`）。

## 8. 回滚策略

F03 没有数据库或数据迁移，回滚只涉及代码：

1. 停止新 server。
2. 回退 F03 commits，恢复四个 route 的原内联定义与原 FastAPI 构造位置。
3. 保留 F02 数据库 revision 与数据，不执行 Alembic downgrade。
4. 启动原 `inkdesk_server.main:app`。
5. 重新执行 focused routes、F01 OpenAPI compare 与 MCP/Worker lifecycle smoke tests。

建议把“新增纯壳/routers”和“main 切换”保持为可审阅的小提交，但最终回滚以完整 F03 变更集为单位，避免留下新旧 route 双注册。

## 9. 明确范围外

- 不新增或修改任何业务表、字段、Alembic revision 或 seed 数据。
- 不开始 F04 Organization、Identity、Capability Space 或 Workspace Adapter。
- 不开始 F05 Job、Attempt、lease、heartbeat 或 Worker durability。
- 不重构 F02 migration/readiness 实现。
- 不修复或重新设计 Compile Worker 与 MCP 生命周期。
- 不迁移 Knowledge Health、Run、Ask、Raw、Wiki、Skill 或其他 legacy routes。
- 不拆分 `schemas.py`、models、research service 或 ORM query。
- 不引入自动路由扫描、DI container、Repository 基类或事件总线。
- 不修改前端 UI、API client 或 TypeScript types。
- 不更新 F01 OpenAPI snapshot 来接受无意的契约变化。
- 不以 `main.py` 行数、目录数量或“架构更漂亮”作为验收结果。

## 10. 主要风险与审阅重点

| 风险 | 为什么隐蔽 | 必须怎样发现 |
| --- | --- | --- |
| 新旧 route 双注册 | FastAPI 可能仍返回成功，OpenAPI 也可能只暴露一个形状 | 枚举完整 `app.routes` 的 method/path 并断言唯一 |
| operation ID 漂移 | 默认 ID 由函数名和路径生成，功能测试不会发现 | 对四个 ID 做精确断言并比较完整 OpenAPI |
| “纯壳”通过 import 启动 runtime | import 链可间接加载 `main.app` | 在无数据库环境导入并创建两次，监控所有副作用边界 |
| 依赖 override 失效 | router 若直接调用 service factory，测试会回到真实 DB | fake service 驱动 actuator/Vault 全部分支 |
| MCP mount 抢占或顺序变化 | mount 与 route composition 依赖 Starlette 匹配顺序 | 完整 app route inventory 与 MCP smoke test |
| 500 测试误判 | TestClient 默认把服务端异常重新抛出 | 明确使用 `raise_server_exceptions=False` 验证响应 |
| 把 `/api/health` 一起迁移 | 名称相似但领域含义不同 | 纯壳不存在、完整 app 存在的双向断言 |
| 与 F02 未合并代码冲突 | `main.py` 和启动时序正是两个计划的共同热点 | F02 合并后重建 F03 分支并先运行基线 |

## 11. 学习与审阅检查点

用户完成每个增量后，应能用自己的话解释：

1. 为什么 app factory 的“纯”不是代码风格，而是测试隔离和未来模块组合的前提。
2. production composition root 与 HTTP router 各自拥有哪类依赖和生命周期。
3. 为什么依赖反转在这里表现为一个窄 FastAPI dependency，而不是引入大型框架。
4. 为什么 duplicate route、operation ID 和 OpenAPI 全量比较比“请求能返回 200”更能证明无行为迁移。
5. 为什么 F03 只迁移四个端点，比一次性拆完整个 `main.py` 更符合路线图的可回退绞杀策略。

Codex 审阅 diff 时优先检查边界是否真实成立，再检查命名和格式；如果实现需要靠 import 顺序、全局 mutable app 或真实数据库才能通过 router tests，说明组合壳仍未建立。

## 12. 计划自审结论

- **单一能力**：只建立应用组合壳并迁移四个端点，没有夹带业务模块或生命周期重构。
- **契约完整**：路径、方法、函数名、operation ID、状态码、模型、错误、CORS、MCP 与启动入口均有可观察断言。
- **前后级清晰**：F01 提供行为权威，F02 必须先完成交付闭环，F03 为 F04/F05 提供模块接入点。
- **可实施性**：文件、测试、Red-Green 顺序、命令、门禁和回退均已确定，三个增量可独立审阅。
- **可回退性**：没有数据变化；失败时整体回退 F03 代码并复用 F02 数据库。
- **范围控制**：明确拒绝全量拆分 `main.py`、重做 service、修复 Worker/MCP 或提前建设 Organization/Job。
