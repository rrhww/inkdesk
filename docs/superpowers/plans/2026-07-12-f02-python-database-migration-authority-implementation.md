# F02 Python 数据库迁移权威实施计划

> 日期：2026-07-12
> 状态：待用户确认；F01 已验收通过，F02 可实施
> 路线图：[`2026-07-11-inkdesk-capability-platform-master-roadmap.md`](./2026-07-11-inkdesk-capability-platform-master-roadmap.md)
> 上位设计：[`2026-07-11-inkdesk-team-rd-capability-platform-design.md`](../specs/2026-07-11-inkdesk-team-rd-capability-platform-design.md)
> 前置依赖：F01 当前行为契约与恢复基线
> 后续解锁：F04 默认 Organization 与 Capability Space、F05 Durable Job / Attempt Kernel，以及所有后续数据库演进
> 协作归属：用户负责编码、失败测试、迁移执行和故障演练；Codex 负责解释现有数据库路径、拆解任务、审阅 diff、迁移 SQL 和验收证据

## 1. 单一交付目标

F02 只交付一项能力：**Alembic 成为 Inkdesk 唯一、可审计、可验证的数据库 DDL 权威**。

完成后必须成立：

```text
空数据库
-> Alembic upgrade
-> 当前应用 schema

F01 认证的现有数据库
-> 严格 schema 校验
-> Alembic 接管
-> 当前应用 schema 与数据均不变

后续 schema 变化
-> 只能新增 Alembic revision
```

`Base.metadata.create_all()`、`db.py` 中的运行时 `ALTER TABLE` 数组、旧 Flyway SQL 和应用启动副作用不再共同决定数据库结构。

F02 不新增业务表、业务列或产品行为。唯一新增表是 Alembic 自己维护的 `alembic_version` 元数据表。

## 2. F01 验收输入

F02 以 F01 run `20260711T113950Z` 为已验证迁移前基线：

| 证据 | 结果 |
| --- | --- |
| 完整 `-Mode all` | `PASS` |
| 必需 suite | 10/10 `PASS` |
| Known issues | 0 |
| PostgreSQL dump SHA-256 | 与 manifest 相等 |
| Vault ZIP SHA-256 | 与 manifest 相等 |
| 源库与恢复库指纹 | 相等 |
| 源 Vault 与恢复 Vault 指纹 | 相等 |
| 恢复后只读 API | 7/7 返回 200 |
| 恢复目标清理 | `CLEANED` |

真实证据位于 `.local/f01-baseline/20260711T113950Z/`，不提交到 Git。F02 的真实迁移演练必须引用一个 `PASS` 的 F01 evidence 目录；如果实施期间业务数据或 schema 已变化，用户先重新执行 F01 `-Mode all`，不能使用过期备份承担回滚。

F01 PostgreSQL 应用 schema 的兼容 digest 为：

```text
4c7413a2ef0b1c571513bbeb672c9f18dc8afd9cf0a64e1fa7533c4a9c6ba519
```

该 digest 覆盖 16 张应用表、列类型与 nullable/default、主键、唯一约束、外键及 `ON DELETE`、索引方法和索引元素。物理 constraint/index 名不属于兼容 digest。

## 3. 当前问题与保留边界

### 3.1 当前有四个 DDL 权威

| 来源 | 当前行为 | F02 处理 |
| --- | --- | --- |
| `Base.metadata.create_all()` | 应用启动时补建缺失表 | 从运行路径删除；仅允许测试夹具显式构造“未接管当前库” |
| `db.py` 五组升级数组 | 启动时按列存在性执行裸 `ALTER TABLE` | 删除；不再新增 runtime DDL |
| `ensure_pgvector_extension()` | 启动时创建 extension | 移入 Alembic baseline revision |
| `server/src/main/resources/db/migration/V*.sql` | 旧 Flyway 历史文件 | 冻结为历史参考，不删除、不继续编号、不在运行时执行 |

`create_app()` 当前调用 `init_db()` 两次。F02 不提前做 F03 的 app factory 重构；`init_db()` 暂时保留名称与调用点，但语义改为只读 revision/readiness 检查，不再执行 DDL。

### 3.2 F02 支持的输入数据库

| 状态 | 判定 | 动作 |
| --- | --- | --- |
| `EMPTY` | 无 `alembic_version`，且除方言系统对象外没有任何用户表 | 执行 baseline revision，创建当前 schema |
| `F01_CURRENT_UNMANAGED` | PostgreSQL 无 `alembic_version`，应用 schema digest 精确等于 F01 | stamp `f02_0001`，不修改应用表 |
| `MANAGED_CURRENT` | revision 为 Alembic head，应用 schema 无 drift | no-op 成功 |
| `MANAGED_BEHIND` | revision 属于当前 revision graph 但落后 | 按 revision 顺序 upgrade |
| `UNSUPPORTED` | 未知 revision、部分旧表、digest 不匹配或混合 schema | 失败且不写入 version，不自动修复 |

原 `test_db_schema_upgrade.py` 中“只创建一张残缺表再让 `create_all` 补齐其他表”的场景不是已认证部署形态。F02 用完整 schema fixture 替换这些测试，不承诺自动猜测任意半成品数据库。若真实部署不是 F01 digest，必须停止 F02，为该 schema 单独制定数据转换计划。

非空且未被 Alembic 管理的 SQLite 数据库同样归类为 `UNSUPPORTED`。SQLite 在当前仓库只承担临时测试和个人开发，不使用 PostgreSQL F01 digest 做自动接管。

## 4. 已敲定的架构决策

### 4.1 Alembic 配置与 revision

- 依赖固定为 `alembic>=1.14,<2.0`，与 SQLAlchemy 2.x 配合。
- 配置根位于 `server/alembic.ini`，migration environment 位于 `server/alembic/`。
- 首个 revision 文件名为 `20260712_f02_0001_baseline.py`，revision ID 固定为 `f02_0001`，`down_revision = None`。
- baseline 使用显式 `op.create_table`、`op.create_index`、constraint 和 PostgreSQL extension DDL；禁止在 revision 内调用 `Base.metadata.create_all()`。
- PostgreSQL 执行 `CREATE EXTENSION IF NOT EXISTS vector`；SQLite 跳过 extension，并使用 Alembic batch 能力处理方言差异。
- PostgreSQL baseline 的应用 schema 必须与 F01 compatibility digest 相同；`alembic_version` 在比较应用 schema 时显式排除。
- baseline `downgrade()` 明确拒绝执行，并提示使用 F01 备份恢复。不能通过 drop 全表伪造可回滚能力。

### 4.2 唯一迁移入口

仓库只公开以下入口：

```powershell
cd server
python -m inkdesk_server.db_migrations status
python -m inkdesk_server.db_migrations check
python -m inkdesk_server.db_migrations upgrade
```

命令语义：

- `status`：只读输出 `state/currentRevision/headRevision/schemaDigest/requiredAction`。
- `check`：确认 revision 为 head 且应用 schema 无 drift；否则非零退出。
- `upgrade`：持锁执行 preflight、严格接管或 Alembic upgrade、postflight schema 校验。

不把裸 `alembic stamp` 作为用户命令。F01 现有库的 stamp 只能由 `db_migrations upgrade` 在 digest 精确匹配后执行。

### 4.3 并发与事务

- PostgreSQL migration command 从 preflight 到 postflight 持有固定 advisory lock，等待上限 30 秒。
- 超时返回 `DB_MIGRATION_LOCK_TIMEOUT`，不启动应用，不绕过锁继续执行。
- PostgreSQL revision 使用事务性 DDL；失败后不得留下 head version 或部分应用 schema。
- SQLite 只用于本地测试和个人模式；依赖文件锁，不把它作为团队并发迁移证明。
- 新增 `INKDESK_MIGRATION_LOCK_TIMEOUT_SECONDS=30`，同步更新所有 `.env*.example` 和环境变量文档。

### 4.4 启动与部署

- `db.py:init_db()` 改为 `assert_database_ready()` 的兼容 facade，只检查 revision 与 schema，不创建表、不加列、不创建 extension。
- `local-server` Docker entrypoint 先执行 `python -m inkdesk_server.db_migrations upgrade`，成功后才 `exec uvicorn`。
- migration 失败时容器退出非零，FastAPI、Compile Worker 和 MCP session manager均不得启动。
- 本地直接运行 Python 后端前，用户显式执行 migration upgrade。
- 本计划不改变 `create_app()` 的双重 readiness check；F03 再处理应用组合与副作用。
- 将来 Team/Organization 部署必须使用独立 migration job；F02 不提前引入 Kubernetes 或多副本发布流程。

### 4.5 Drift 与契约

F02 同时维护四条一致性检查：

1. PostgreSQL fresh upgrade 后，排除 `alembic_version` 的 compatibility digest 精确等于 F01 PostgreSQL digest。
2. PostgreSQL Alembic head 与 SQLAlchemy `Base.metadata` 无 autogenerate drift。
3. F01 当前库接管前后，排除 `alembic_version` 后 compatibility digest 不变。
4. F01 当前库接管前后，每张应用表的 row count 和 canonical row fingerprint 不变。

SQLite 只验证 revision 可执行、API 测试可运行和 metadata 无方言内 drift。它不与 PostgreSQL 共用 digest，也不能替代 PostgreSQL 16、vector extension、外键与索引语义证明。

为避免改变 F01 默认行为，`scripts/f01/export_postgres_schema.py` 只增加显式 `--exclude-table alembic_version` 参数；F01 不传参数时仍导出完整 public schema，F02 verifier 显式排除 migration metadata。

## 5. 错误语义

| 原因码 | 触发条件 | 可恢复动作 |
| --- | --- | --- |
| `DB_SCHEMA_UNSUPPORTED` | 未管理 schema 不等于 EMPTY/F01 digest | 停止；导出结构差异并制定专门转换计划 |
| `DB_REVISION_UNKNOWN` | `alembic_version` 不在当前 revision graph | 停止；确认部署包与数据库来源 |
| `DB_REVISION_BEHIND` | 应用启动时数据库未到 head | 先执行 migration upgrade，再启动应用 |
| `DB_SCHEMA_DRIFT` | revision 已到 head 但实际 schema 与模型/预期不一致 | 停止；恢复备份或补充明确 revision |
| `DB_MIGRATION_LOCK_TIMEOUT` | 30 秒内未取得 advisory lock | 确认是否已有 migration 在运行后重试 |
| `DB_MIGRATION_FAILED` | revision、stamp 或 postflight 失败 | 保留日志；不得启动应用；必要时恢复 F01 备份 |

错误输出必须同时包含机器原因码、当前 revision、目标 revision、数据库方言和下一条安全命令。不得输出带密码的数据库 URL。

## 6. 文件边界

| 操作 | 文件 | 职责 |
| --- | --- | --- |
| 修改 | `server/pyproject.toml` | 增加 Alembic 依赖 |
| 新增 | `server/alembic.ini` | Alembic 主配置；URL 由应用 settings 注入，不硬编码 secret |
| 新增 | `server/alembic/env.py` | 导入 metadata、配置在线/离线 migration 和 type compare |
| 新增 | `server/alembic/script.py.mako` | revision 模板 |
| 新增 | `server/alembic/versions/20260712_f02_0001_baseline.py` | 空库基线 schema 与不可逆 downgrade 语义 |
| 新增 | `server/inkdesk_server/db_migrations.py` | status/check/upgrade、schema 分类、严格 stamp、advisory lock、脱敏错误 |
| 修改 | `server/inkdesk_server/core/config.py` | 增加 migration lock timeout 配置 |
| 修改 | `server/inkdesk_server/db.py` | 删除 create_all、extension DDL 和运行时升级数组；保留 engine/session/readiness facade |
| 修改 | `server/tests/conftest.py` | 测试数据库先迁移到 head，清理 migration cache |
| 替换 | `server/tests/test_db_schema_upgrade.py` | 删除残缺单表假设，迁为完整迁移测试 |
| 新增 | `server/tests/migrations/test_empty_database.py` | SQLite/PostgreSQL 空库到 head |
| 新增 | `server/tests/migrations/test_f01_adoption.py` | F01 digest 严格接管、数据不变、重复执行 no-op |
| 新增 | `server/tests/migrations/test_schema_guard.py` | unknown/partial/drift/unknown revision 拒绝且无 mutation |
| 新增 | `server/tests/migrations/test_runtime_readiness.py` | 应用只在 managed current 状态启动 |
| 新增 | `server/tests/migrations/test_model_drift.py` | Alembic head 与 SQLAlchemy metadata 无 diff |
| 修改 | `server/tests/test_pgvector_integration.py` | 使用独立临时数据库和 Alembic，不再 `drop_all/create_all` |
| 修改 | `scripts/f01/export_postgres_schema.py` | 增加显式 metadata table 排除参数 |
| 新增 | `scripts/f02/verify-migrations.ps1` | 临时空库、F01 restore、故障注入、指纹和清理编排 |
| 新增 | `scripts/f02/build-migration-report.py` | 生成脱敏 F02 manifest 与一致性报告 |
| 新增 | `infra/docker/local-server-entrypoint.sh` | upgrade 成功后启动 uvicorn |
| 修改 | `infra/docker/local-server.Dockerfile` | 复制 Alembic 配置与 entrypoint |
| 修改 | `infra/docker-compose.local-docker.yml` | 向本地 server 传入 migration lock timeout |
| 修改 | `infra/docker-compose.yml` | 向默认 server 传入 migration lock timeout |
| 修改 | `infra/.env.example` | 增加 migration lock timeout |
| 新增 | `server/src/main/resources/db/migration/README.md` | 声明 Flyway V1-V8 冻结为历史，不再是运行权威 |
| 新增 | `docs/ops/数据库迁移.md` | 本地、Docker、部署、失败和恢复操作手册 |
| 修改 | `docs/ops/环境变量.md` | 记录 migration lock timeout 与默认值 |
| 新增 | `docs/delivery/migrations/f02/README.md` | F02 证据、完成门禁和本地 evidence 边界 |
| 修改 | `docs/ops/部署指南.md` | 启动前 migration 步骤与失败处理 |
| 修改 | `docs/delivery/开发环境搭建.md` | 本地后端启动前执行 upgrade |
| 修改 | `scripts/脚本说明.md` | 登记 F02 migration verifier |
| 修改 | `cognitive-map.md` | 记录 Alembic 权威、遗留黑盒和后续 revision 规则 |

不修改 ORM 业务字段、API schemas、前端、MCP、Compile Worker 业务逻辑或 F03 目标模块结构。

## 7. 分段实施计划

F02 按三个连续增量实施。每个增量由用户完成 Red -> Green -> Refactor -> 验证，并把 diff 与输出交给 Codex 审阅；前一增量未通过，不进入下一增量。

### 增量 A：建立 Alembic 权威和空库路径

#### 任务 A1：先锁定命令与失败语义

**Red**

1. 新建 `test_schema_guard.py`，断言 `status` 能区分 EMPTY、F01_CURRENT_UNMANAGED、MANAGED_CURRENT、MANAGED_BEHIND 和 UNSUPPORTED。
2. 断言错误结果包含稳定原因码且数据库 URL 被脱敏。
3. 断言 unknown/partial schema 运行 `upgrade` 后没有 `alembic_version`，原表 hash 不变。
4. 执行：

```powershell
cd server
python -m pytest tests/migrations/test_schema_guard.py -q
```

确认因 migration module 尚不存在而失败，且失败原因与目标一致。

**Green**

1. 添加 Alembic 依赖和配置骨架。
2. 实现 `db_migrations status/check` 与 schema state classifier，不实现 upgrade。
3. 只做到分类、脱敏和无 mutation 测试通过。

#### 任务 A2：空库 baseline revision

**Red**

1. `test_empty_database.py` 断言 SQLite 与 PostgreSQL 空库执行 upgrade 后 revision 为 `f02_0001`。
2. PostgreSQL 断言 16 张应用表、列、约束、索引和 vector extension 与 F01 contract 一致；SQLite 只断言方言内结构与 ORM metadata 一致。
3. 断言重复 upgrade 不产生 schema diff。
4. 断言 baseline downgrade 被明确拒绝，不删除表。

**Green**

1. 编写显式 baseline revision。
2. 实现 EMPTY -> Alembic upgrade 路径。
3. 使用 F02 schema comparator 排除 `alembic_version` 后计算 digest。
4. 修正 revision 与 metadata 的实际差异，直到 autogenerate drift 为空；禁止通过放宽 comparator 隐藏差异。

**增量 A 验收**

```powershell
cd server
python -m pytest tests/migrations/test_schema_guard.py tests/migrations/test_empty_database.py tests/migrations/test_model_drift.py -q
```

预期：全部通过；PostgreSQL fresh schema 的 compatibility digest 等于 F01；SQLite 方言内 drift 为空；PostgreSQL extension 检查通过。

### 增量 B：严格接管 F01 当前库并切断运行时 DDL

#### 任务 B1：F01 当前库接管

**Red**

1. 使用测试 fixture 构造无 `alembic_version` 的当前 schema，记录 schema digest 和每表 fingerprint。
2. 运行 upgrade，断言 revision 被 stamp 为 `f02_0001`。
3. 断言排除 migration metadata 后 schema digest、row count、row fingerprint 完全不变。
4. 改动一个列类型或 `ON DELETE`，断言接管失败且不 stamp。

**Green**

1. 实现 F01 digest 精确匹配后的受控 stamp。
2. stamp 前后均执行 schema guard；postflight 不一致时整体失败。
3. PostgreSQL 路径从 preflight 到 postflight 持有 advisory lock。
4. 连续两次 upgrade：第一次接管，第二次 no-op。

#### 任务 B2：把运行路径切换为 readiness-only

**Red**

1. `test_runtime_readiness.py` 断言 empty、unmanaged、behind、unknown 和 drift 数据库不能启动 app。
2. 断言失败发生在 seed、Compile Worker 和 MCP session 启动之前。
3. 断言 managed current 数据库可以保持现有 API 行为。

**Green**

1. 删除 `db.py` 中五组升级数组、`create_all` 和 extension DDL。
2. `init_db()` 只调用 `assert_database_ready()`，不产生数据库写入。
3. 测试夹具显式迁移数据库，不依赖应用启动建表。
4. 更新 pgvector integration，强制使用 `inkdesk_f02_test_` 前缀的临时数据库，拒绝活动数据库名。

#### 任务 B3：Docker 启动顺序

**Red**

1. entrypoint 测试断言 migration 失败时 uvicorn 不执行。
2. 并发启动两个 migration command，断言只有持锁者执行，另一方等待或按 30 秒超时失败。
3. 限制 DDL 权限，断言 migration 非零退出、server 不健康、数据库没有 head revision。

**Green**

1. 添加 entrypoint，先 upgrade 后 `exec uvicorn`。
2. Docker image 复制 `alembic.ini`、`alembic/` 和 entrypoint。
3. 日志输出 revision 与状态，不输出密码。

**增量 B 验收**

```powershell
cd server
python -m pytest tests/migrations tests/test_pgvector_integration.py -q
python -m pytest
```

预期：migration suite 与现有后端 suite 全部通过；代码搜索不再发现生产路径的 `create_all`、runtime upgrade arrays 或裸 `ALTER TABLE`。

### 增量 C：真实迁移演练、故障恢复与文档签收

#### 任务 C1：F02 隔离 verifier

**Red**

1. 为错误 F01 evidence、活动数据库目标、非法临时数据库名、hash 不一致和 cleanup 失败写编排测试。
2. 断言 verifier 不允许在源数据库上执行 migration。
3. 断言局部成功不能合并为 PASS。

**Green**

`verify-migrations.ps1` 执行：

```text
验证 F01 manifest = PASS
-> 创建 inkdesk_f02_empty_<runId>
-> Alembic fresh upgrade
-> 创建 inkdesk_f02_adopt_<runId>
-> 从 F01 dump 恢复
-> 记录 schema/data before
-> strict adopt
-> 记录 schema/data after
-> 重复 upgrade 验证 no-op
-> 启动隔离后端并执行只读 API
-> 注入 unsupported/permission/lock failure
-> 清理所有临时目标
-> 生成 F02 manifest
```

真实源数据库与 Vault 全程只读。

#### 任务 C2：全栈与回退验证

用户执行：

```powershell
pwsh -File scripts/f02/verify-migrations.ps1 `
  -F01EvidenceDir .local/f01-baseline/20260711T113950Z

docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml up -d --build

cd web
npm run e2e:fullstack
```

验收时确认：

- Docker server 日志先出现 migration head，再出现 uvicorn ready。
- 原 `/actuator/health` 和关键读路径可用。
- F01 代表性 API/OpenAPI 行为无变化。
- 回滚到 F01 代码仍能读取仅多出 `alembic_version` 的数据库。
- 任一 schema/data 指纹不一致时，使用 F01 dump + Vault ZIP 恢复到隔离目标验证，不执行 downgrade。

#### 任务 C3：文档与权威切换

1. 冻结 Flyway README，明确新 SQL 不得进入旧目录。
2. 更新本地开发、Docker 部署、失败恢复和脚本说明。
3. 更新 cognitive map：Alembic 已理解；Flyway V1-V8 仅历史；未知外部部署 schema 为黑盒。
4. 记录 F02 evidence run ID、revision、before/after digest、fingerprint 与 failure injection 结果。
5. Codex 对照第 8 节逐项审阅，通过后把路线图 F02 标记完成并允许 F04/F05 使用新 migration authority。

## 8. F02 完成门禁

只有以下条件全部成立，F02 才能标记完成：

1. F01 的 PASS evidence 存在、哈希可验证，并被 F02 manifest 引用。
2. SQLite 和真实 PostgreSQL 空库都能只通过 Alembic 到达 `f02_0001`。
3. PostgreSQL fresh schema 与 F01 PostgreSQL compatibility digest 相同；SQLite 方言内 metadata drift 为空。
4. F01 恢复库接管前后应用 schema digest、每表 row count 和 fingerprint 不变。
5. 重复 upgrade 是 no-op；未知、partial、drift、unknown revision 都失败且不写入版本。
6. PostgreSQL advisory lock 和权限失败注入通过；migration 失败时应用未启动。
7. 应用运行路径不存在 `create_all`、runtime `ALTER TABLE` 数组或 extension DDL。
8. Alembic head 与 SQLAlchemy metadata 的 drift 检查为空。
9. 后端全量测试、PostgreSQL integration 和 full-stack E2E 通过。
10. Docker 新建环境和现有 F01 数据环境都能启动并读取原 API/UI 数据。
11. rollback 演练使用 F01 备份成功，不调用 destructive downgrade。
12. Flyway 冻结、本地/部署命令、失败原因码和新增环境变量均有文档，`.env*.example` 同步。

任一数据 fingerprint 变化、自动接管未知 schema、migration 失败后继续启动服务、泄露数据库 URL 或无法恢复源数据都属于阻塞失败，不能登记为 known issue 后继续 F04/F05。

## 9. 回滚策略

### 9.1 接管当前 F01 数据库

接管只增加 `alembic_version`。若发布后需要回退应用代码：

1. 停止新 server。
2. 回退到 F01 应用镜像。
3. 保留 `alembic_version`；旧应用不会读取该表。
4. 重新验证健康检查和关键读路径。

只有 schema/data 指纹异常时才恢复 F01 dump 与 Vault ZIP。

### 9.2 Alembic 创建的新空库

空库没有需要保留的数据。失败时销毁该临时数据库并重新创建，不执行 baseline downgrade。

### 9.3 未来 revision

F02 只定义规则，不承诺所有未来 revision 可 downgrade。每个后续计划必须单独声明 expand/backfill/switch/contract 和回退方式；数据型变更优先前向修复或备份恢复。

## 10. 明确范围外

- 不新增 Organization、Capability Space、Job、Attempt 或任何业务字段。
- 不迁移、清理或重命名现有业务数据。
- 不自动升级任意 Flyway 版本或未知 partial schema。
- 不删除旧 Flyway SQL；只冻结其权威。
- 不重构 `create_app()`、Compile Worker 或 MCP 生命周期。
- 不引入独立 migration service、Kubernetes Job、蓝绿发布或多区域数据库。
- 不承诺零停机 schema 变更；F02 只建立后续计划必须遵循的权威和安全入口。
- 不修改前端页面、API/OpenAPI、Vault 文件或产品交互。
- 不把本地 F01/F02 dump、manifest、连接地址或真实数据提交到 Git。

## 11. 计划自审结论

- **完整性**：覆盖空库、F01 当前库、重复执行、未知 schema、drift、锁、权限失败、Docker 启动和恢复。
- **设计一致性**：符合路线图“Python migration authority”与 Expand/Backfill/Switch/Contract 原则，不提前创建 F04 业务结构。
- **可构建性**：文件、revision ID、CLI、原因码、Red-Green 步骤、命令和预期结果均已确定。
- **数据安全**：真实迁移只针对隔离 restore；源数据库只读；未知 schema fail closed；回滚依赖已验证 F01 备份。
- **分解合理性**：三个增量分别建立权威、接管运行路径和完成真实演练，共同只交付数据库迁移权威这一项能力。
