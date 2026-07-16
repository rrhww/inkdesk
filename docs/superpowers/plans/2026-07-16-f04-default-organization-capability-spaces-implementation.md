# F04 默认 Organization 与 Capability Space 实施计划

> 日期：2026-07-16
> 状态：待用户确认；F01-F03 已完成并合并，F04 可实施
> 路线图：[`2026-07-11-inkdesk-capability-platform-master-roadmap.md`](./2026-07-11-inkdesk-capability-platform-master-roadmap.md)
> 上位设计：[`2026-07-11-inkdesk-team-rd-capability-platform-design.md`](../specs/2026-07-11-inkdesk-team-rd-capability-platform-design.md)
> 前置依赖：F02 Alembic 数据库迁移权威、F03 模块化应用组合壳
> 后续解锁：W01 Goal Contract 的运行归属、K01 Knowledge 数据分级、C03 四级作用域解析、T01 完整成员与 Space 管理
> 协作归属：用户负责编写失败测试、迁移与生产代码、执行故障演练；Codex 负责解释空间模型、拆解步骤、审阅 migration/diff 与验收证据

## 1. 单一交付目标

F04 只交付一项能力：**在不改变现有 Workspace API、数据归属和个人使用体验的前提下，为每个旧 Workspace 建立可持久化、可解析、可回退的默认 Organization -> Project Space -> Personal Overlay 拓扑。**

完成后必须成立：

```text
现有 User
-> 默认 Organization Membership

默认 Organization
-> Organization Space
   -> 每个现有 Workspace 对应的 Project Space
      -> Workspace owner 对应的 Personal Overlay

现有 workspace_id
-> WorkspaceSpaceBinding
-> Project Space
-> Organization + owner Membership + Personal Overlay
```

所有旧业务表继续保存原 `workspace_id`，所有旧 API 继续返回原 `workspaceId`。F04 用显式绑定表和 Workspace Adapter 建立兼容桥，不批量改写 Source、Topic、Run、Ask、Review、Retrieval 或 Compile 数据。

F04 不是团队管理功能。它只让“当前单人 Workspace 实际属于哪个组织和能力空间”成为数据库与代码都能回答的事实，为后续团队能力、作用域解析和权限治理提供最小可信底座。

## 2. 已验证输入

### 2.1 F01-F02 数据安全输入

- F01 run `20260711T113950Z` 的完整 manifest 为 `PASS`，PostgreSQL + Vault 成对恢复、10/10 必需 suite 和 7 条恢复读路径均通过。
- F02 migration verifier run `20260714T151606Z` 为 `PASS`，证明空库升级、F01 严格接管、schema/data 指纹不变以及权限/锁失败语义。
- F04 开始真实迁移前，用户必须在 F03 已合并代码和当前真实数据上重新运行一次 F01 `-Mode all`，生成新的 `PASS` 备份 run。旧 run 可证明工具有效，但不能代替 2026-07-16 之后数据的回滚点。

### 2.2 F03 组合与回归输入

F03 已通过 PR #7 合并到 `origin/main`，merge commit 为 `77a848a`。已审阅证据：

- focused API/runtime/OpenAPI：`23 passed`。
- 后端全量：`386 passed, 7 skipped`。
- PostgreSQL migration + pgvector：`17 passed, 1 skipped`。
- 隔离全栈 Playwright：`10 passed`。
- Docker 服务在 `f02_0001 / MANAGED_CURRENT` 后启动。
- production OpenAPI 与 F01 checked-in canonical snapshot 完整相等。

F04 不改变 F03 的纯 API 壳职责，也不新增 Space HTTP router。空间模块先通过 migration、内部应用接口和旧路径适配证明边界，团队治理 API/UI 留给 T01。

## 3. 当前问题与关键约束

### 3.1 当前只有隐式单人 Workspace

现有模型只有：

```text
User 1 -> N Workspace
Workspace 1 -> N Source / Topic / Review / Run / Ask / Retrieval / Compile
```

运行时通过固定 slug `inkdesk` 解析默认 Workspace：

- `research.py:ResearchWorkspaceService.require_workspace()`
- `main.py:_resolve_workspace()`
- `mcp/__init__.py:_resolve_workspace_id()`

这些入口只能回答“当前 Workspace 是谁”，不能回答：

- 它属于哪个 Organization。
- 哪个 Capability Space 是项目正式作用域。
- 当前 owner 的个人覆盖层是哪一个。
- 绑定缺失或拓扑损坏时是否应 fail closed。

### 3.2 不能把 F04 变成全库换键

当前至少九类核心表直接持有 `workspace_id`，更多服务方法把它作为隔离条件。F04 若一次性给所有表新增 `space_id`，会同时触碰知识、Run、Ask、Retrieval 和 Compile 多个领域，无法在 1-3 个开发会话内独立验证或回退。

因此 F04 固定采用兼容桥：

```text
legacy object.workspace_id
-> workspaces.id
-> workspace_space_bindings.project_space_id
-> capability_spaces
```

旧对象何时直接归属 Space，由各后续领域计划按 Expand -> Backfill -> Switch -> Contract 单独决定。

### 3.3 F02 migration authority 必须支持第二个 revision

当前 `db_migrations.py` 把 `HEAD_REVISION` 固定为 `f02_0001`，并把 PostgreSQL current schema 永久等同于 F01 digest。增加 F04 revision 后，如果只改 `HEAD_REVISION` 会产生两个严重错误：

1. F04 新表会使 current schema 与 F01 digest 不同，从而被误报为 `SCHEMA_DRIFT`。
2. 未管理 F01 数据库会被直接 stamp 到 F04 head，跳过 F04 schema 创建与数据回填。

F04 必须同步演进 migration authority：F01 未管理库只能 stamp 到其真实对应 revision `f02_0001`，随后正常 upgrade 到 `f04_0002`；每个受支持 revision 使用自己的 schema contract。

## 4. 已敲定的领域最小集

### 4.1 新增四类持久化对象

#### Organization

表示隔离与治理的最高边界。F04 只创建一个内部默认 Organization：

```text
id     = organization-default
slug   = default
name   = Default Organization
status = active
```

名称未来可由 T01 修改，代码不得使用 name 查询；稳定 ID 与 slug 才是 bootstrap contract。

#### OrganizationMembership

连接现有 `users` 与 Organization。当前已认证产品形态只有一个 Workspace owner；F04 为该 owner 创建一个 membership：

```text
organization_id = organization-default
user_id          = existing workspace.owner_user_id
role             = owner
status           = active
```

`role` 在 F04 只是默认所有权标记，不是完整 RBAC。Role 表、邀请、职责分离和权限计算属于 T01/T04。

F04 不猜测多个历史 owner 是否属于同一团队。migration/bootstrap preflight 只接受零个或一个 distinct `workspaces.owner_user_id`；发现多个 owner 时返回 `SPACE_LEGACY_OWNERSHIP_UNSUPPORTED`，并在写入任何 F04 row 前停止。后续必须通过独立转换计划显式决定 Organization 边界和成员角色，不能自动把互不相关的个人数据合并到同一 Organization。

#### CapabilitySpace

表示能力作用域节点，`scope_type` 允许以下稳定值：

```text
organization | domain | project | personal
```

F04 实际只创建：

1. 一个 Organization Space，parent 为 null。
2. 每个 Workspace 一个 Project Space，parent 为 Organization Space。
3. 每个 Workspace owner 一个 Personal Overlay，parent 为对应 Project Space，owner 指向 membership。

F04 不创建虚假的 Domain Space。Domain 节点必须在真实跨项目需求出现后由 T01/C03 建立。

#### WorkspaceSpaceBinding

兼容桥只保存：

```text
workspace_id     -> existing workspaces.id
project_space_id -> capability_spaces.id where scope_type = project
```

Organization 通过 Project Space 得到；Personal Overlay 通过 Project Space + owner membership 得到。绑定表不保存单一 `personal_space_id`，避免未来一个 Project 有多个成员时被当前单人假设锁死。

### 4.2 表级约束

| 表 | 必须约束 |
| --- | --- |
| `organizations` | PK `id`；unique `slug`；status 非空 |
| `organization_memberships` | PK `id`；FK organization/user；unique `(organization_id, user_id)` |
| `capability_spaces` | PK `id`；FK organization/parent/owner membership；unique `(organization_id, slug)`；scope/status 非空 |
| `workspace_space_bindings` | PK/FK `workspace_id`；unique/FK `project_space_id` |

数据库约束负责引用完整性和唯一性；跨行语义由空间模块验证：

- Organization Space 必须 parent null、owner null。
- Project Space 必须属于同一 Organization，parent 为 Organization Space，owner null。
- Personal Space 必须属于同一 Organization，parent 为 Project Space，owner membership 属于同一 Organization。
- Binding 目标必须是 Project Space。
- 每个 Workspace 必须恰好解析出一个 project 与 owner personal overlay。

### 4.3 确定性身份

默认 Organization 使用固定 ID。membership、project、personal space 使用固定 UUIDv5 namespace，分别根据以下 identity key 生成：

```text
membership:{organization_id}:{user_id}
project:{organization_id}:{workspace_id}
personal:{organization_id}:{workspace_id}:{user_id}
```

revision 内复制已冻结的 namespace 与 UUIDv5 算法，不从当前应用模块导入 migration 逻辑。应用 bootstrap 使用同一算法；契约测试验证两端对同一 fixture 生成相同 ID。这样重复 migration、重复启动和恢复演练不会创建第二套拓扑。

slug 同样使用确定性规则，并受 Organization 内 unique constraint 保护：Organization Space 为 `organization`，Project Space 为 `project-{workspace.slug}`，Personal Overlay 为 `personal-{workspace.slug}-{sha256(user_id)[:12]}`。名称只用于未来展示，不参与解析；slug 被不同确定性 ID 占用时按 identity conflict 处理，不自动追加随机后缀。

## 5. 已敲定的架构决策

### 5.1 模块结构

```text
server/inkdesk_server/
  model_registry.py
  modules/
    __init__.py
    spaces/
      __init__.py
      constants.py
      models.py
      topology.py
      bootstrap.py
      workspace_adapter.py
```

- `constants.py`：scope/status/default identity 与确定性 ID，不访问数据库。
- `models.py`：四张新表的 SQLAlchemy ORM mapping。
- `topology.py`：`WorkspaceSpaceContext`、拓扑不变量与稳定错误码。
- `bootstrap.py`：为已有 Workspace 幂等确保默认拓扑，只写 F04 表。
- `workspace_adapter.py`：从 legacy Workspace 解析并验证 Space context；对外提供最小公开查询接口。
- `model_registry.py`：集中导入 legacy 与模块 ORM models，确保 Alembic、drift check 和测试看到同一 `Base.metadata`。

F04 不创建通用 Domain 基类、Repository 框架、事件总线或自动模块扫描。

### 5.2 Workspace Adapter 公共契约

Adapter 至少提供：

```python
require_workspace_context(db, *, workspace_slug: str) -> WorkspaceSpaceContext
require_workspace_context_by_id(db, *, workspace_id: str) -> WorkspaceSpaceContext
```

返回值包含：

```text
workspace
organization
membership
organization_space
project_space
personal_space
```

F04 切换以下三个解析入口使用 Adapter：

1. `ResearchWorkspaceService.require_workspace()` 调用 context resolver，但继续返回原 Workspace，避免改动所有现有 service signatures。
2. `main.py:_resolve_workspace()` 调用 Adapter，继续返回原 Workspace。
3. `mcp/__init__.py:_resolve_workspace_id()` 调用 Adapter，继续返回原 workspace ID。

现有 Source/Topic/Run/Ask/Compile 逻辑仍按 `workspace_id` 查询。Adapter 的价值是让所有 HTTP、service 和 MCP 默认入口先验证空间绑定，不是提前执行 Capability inheritance。

### 5.3 Fail-closed 语义

空间模块使用稳定内部原因码：

| 原因码 | 触发条件 | 动作 |
| --- | --- | --- |
| `SPACE_WORKSPACE_NOT_FOUND` | workspace slug/id 不存在 | 保持现有 ResourceNotFound 语义 |
| `SPACE_BINDING_MISSING` | Workspace 没有 binding | 启动/bootstrap 修复可安全缺失项；运行期仍缺失则失败 |
| `SPACE_TOPOLOGY_INVALID` | scope、parent、organization 或 owner 不一致 | fail closed，不自动重绑 |
| `SPACE_IDENTITY_CONFLICT` | 确定性 ID/slug 已被不同对象占用 | fail closed，要求人工检查 |
| `SPACE_MEMBERSHIP_MISSING` | owner 不在 Organization | bootstrap 创建；运行期仍缺失则失败 |
| `SPACE_LEGACY_OWNERSHIP_UNSUPPORTED` | 历史 Workspace 存在多个 distinct owner | migration/bootstrap 写入前停止，制定显式组织映射 |

bootstrap 只补充“完全缺失且可由 Workspace 唯一推导”的行。任何已存在但字段冲突的 topology 都不得被静默覆盖。

### 5.4 无新 API、无作用域解析

F04 不新增 `/api/spaces`、`/api/organizations` 或 `/api/members`。完整 OpenAPI 必须继续与 F01 snapshot 相等。

F04 也不实现：

- Personal -> Project -> Domain -> Organization 的能力合并顺序。
- mandatory Policy 覆盖规则。
- visibility、permission 或 RBAC 决策。
- 当前任务应选择哪个 Space 的交互。

这些属于 C03、T01 和 T04。F04 只保证拓扑与归属可被稳定解析。

## 6. F04 Alembic 与 migration authority

### 6.1 Revision

新增唯一 revision：

```text
文件：20260716_f04_0002_default_capability_spaces.py
revision：f04_0002
down_revision：f02_0001
```

upgrade 顺序：

```text
Expand
-> preflight：历史 Workspace owner 数量必须 <= 1
-> 创建 organizations
-> 创建 organization_memberships
-> 创建 capability_spaces
-> 创建 workspace_space_bindings

Backfill
-> 创建默认 Organization + Organization Space
-> 按 distinct workspace.owner_user_id 创建 membership
-> 按每个 Workspace 创建 Project Space + Personal Overlay + Binding

Validate
-> 每个 Workspace 恰好一个 Binding
-> 每个 owner 恰好一个 Organization membership
-> 每个 Binding 拓扑完整
-> 旧表 schema 与旧列数据不变
```

revision 使用显式 `op.create_table`、constraint/index 和 SQLAlchemy Core 查询。禁止调用 ORM、应用 bootstrap 或 `Base.metadata.create_all()`。

### 6.2 Schema contract 按 revision 管理

`schema_contract.py` 从单一 F01 常量演进为 revision-aware contract：

```text
f02_0001 -> F01 compatibility digest
f04_0002 -> F04 checked-in PostgreSQL schema digest
```

F04 digest 由 fresh PostgreSQL upgrade 的 canonical schema 生成，经 migration/ORM drift review 后写入代码与 `docs/delivery/migrations/f04/contracts/postgres-schema.json`。禁止通过排除四张新表或放宽 comparator 让旧 digest 继续通过。

### 6.3 合法升级路径

| 输入 | 动作 | 最终状态 |
| --- | --- | --- |
| EMPTY | Alembic 从 baseline 连续执行到 `f04_0002` | MANAGED_CURRENT |
| F01_CURRENT_UNMANAGED | 验证 F01 digest -> stamp `f02_0001` -> upgrade `f04_0002` | MANAGED_CURRENT |
| MANAGED `f02_0001` | 先验证 F02/F01 schema contract -> upgrade F04 | MANAGED_CURRENT |
| MANAGED `f04_0002` | 验证 F04 contract | no-op |
| unknown/drift/partial | fail closed | 不写 revision，不补 topology |

F01 adoption 不再 stamp 到 `HEAD_REVISION`。代码必须显式保留 `F01_ADOPTION_REVISION = "f02_0001"`，完成 stamp 后继续走 revision graph。

### 6.4 Model registry

当前 Alembic env 和 SQLite drift check 只 import `inkdesk_server.models`。F04 新 ORM 位于模块目录，必须统一改为调用 `load_orm_models()`，并在以下路径使用同一 registry：

- `server/alembic/env.py`
- `server/inkdesk_server/db_migrations.py`
- migration/model drift tests

未加载空间 models 导致的“数据库有表但 metadata 看不到”属于阻塞失败。

## 7. 文件边界

| 操作 | 文件 | 单一职责 |
| --- | --- | --- |
| 新增 | `server/inkdesk_server/model_registry.py` | 集中注册 legacy 与模块 ORM metadata |
| 新增 | `server/inkdesk_server/modules/__init__.py` | 声明模块化单体 package |
| 新增 | `server/inkdesk_server/modules/spaces/__init__.py` | 暴露稳定的 Space 模块公共入口 |
| 新增 | `server/inkdesk_server/modules/spaces/constants.py` | scope、默认身份、UUIDv5 规则 |
| 新增 | `server/inkdesk_server/modules/spaces/models.py` | Organization/Membership/Space/Binding ORM |
| 新增 | `server/inkdesk_server/modules/spaces/topology.py` | context、不变量、错误码 |
| 新增 | `server/inkdesk_server/modules/spaces/bootstrap.py` | fresh seed 后的幂等 DML bootstrap |
| 新增 | `server/inkdesk_server/modules/spaces/workspace_adapter.py` | legacy Workspace -> Space context 解析 |
| 新增 | `server/alembic/versions/20260716_f04_0002_default_capability_spaces.py` | schema expand、现有 Workspace backfill、受保护 downgrade |
| 修改 | `server/alembic/env.py` | 使用统一 model registry |
| 修改 | `server/inkdesk_server/schema_contract.py` | revision-aware PostgreSQL schema contracts |
| 修改 | `server/inkdesk_server/db_migrations.py` | 新 head、F01 正确 adoption、behind preflight、F04 rollback guard |
| 修改 | `server/inkdesk_server/research.py` | seed 后确保拓扑；默认 Workspace 经 Adapter 验证 |
| 修改 | `server/inkdesk_server/main.py` | `_resolve_workspace` 委托 Adapter，返回契约不变 |
| 修改 | `server/inkdesk_server/mcp/__init__.py` | 默认 workspace ID 经 Adapter 解析 |
| 新增 | `server/tests/spaces/test_topology.py` | identity、层级不变量、错误码 |
| 新增 | `server/tests/spaces/test_bootstrap.py` | fresh、重复、冲突与多 Workspace bootstrap |
| 新增 | `server/tests/spaces/test_workspace_adapter.py` | context 解析与 fail-closed |
| 新增 | `server/tests/migrations/test_f04_space_migration.py` | fresh/backfill/idempotency/legacy fingerprint |
| 修改 | `server/tests/migrations/test_f01_adoption.py` | F01 stamp f02 后继续升级 f04 |
| 修改 | `server/tests/migrations/test_model_drift.py` | F04 head 与完整 metadata 无 drift |
| 修改 | `server/tests/migrations/test_runtime_readiness.py` | f02 behind、f04 current 与 revision contract |
| 新增 | `server/tests/test_space_compatibility.py` | HTTP/service/MCP 保留 workspace ID 与行为 |
| 新增 | `scripts/f04/verify-space-migration.ps1` | 隔离 restore、backfill、故障、回滚编排 |
| 新增 | `scripts/f04/build-space-report.py` | 生成脱敏 manifest 与 topology/fingerprint 报告 |
| 新增 | `docs/delivery/migrations/f04/README.md` | 证据边界、完成门禁与恢复说明 |
| 新增 | `docs/delivery/migrations/f04/contracts/postgres-schema.json` | F04 PostgreSQL canonical schema contract |
| 修改 | `scripts/脚本说明.md` | 登记 F04 verifier 与 scoped rollback |
| 修改 | `docs/architecture/数据库结构.md` | 记录四张新表与 legacy bridge |
| 修改 | `cognitive-map.md` | 记录已理解 Space topology 与仍未实现的权限/解析 |

不修改任何 `web/**`、现有 request/response schema、F01 OpenAPI snapshot、Vault 文件结构、Skill contract、Run 状态机、Compile Worker 或 MCP tool contract。

### 7.1 与 F05 并行时的所有权

F04 与 F05 没有业务前后依赖，但共享 migration authority。并行期间固定以下所有权：

| 阶段 | F04 泳道 | F05 泳道 |
| --- | --- | --- |
| F04 合并前 | 独占 `f04_0002`、`db_migrations.py`、`schema_contract.py`、`model_registry.py` 和 migration verifier | 只实现 Job/Attempt/lease/idempotency 纯领域契约、状态转换和无数据库失败测试；不创建 revision，不接 Compile Worker |
| F04 合并后 | 发布新 head、schema digest、model registry 使用方式和验收证据 | rebase 到 F04 merge commit，创建后继 revision，再实现 persistence、Compile Worker Adapter 和恢复演练 |
| 集成验收 | F04 独立完成 topology/rollback/full-stack | F05 独立完成 restart/lease/idempotency/full-stack，不复用 F04 未提交证据 |

F05 分支不得预先创建另一个以 `f02_0001` 为 `down_revision` 的 head，也不得临时修改 F04 revision ID。若 F05 领域设计反向要求修改 Space schema，停止并回到路线图重新划分边界，不能跨分支直接改 F04 文件。

## 8. 分段实施计划

F04 分为三个连续增量。每个增量由用户执行 Red -> Green -> Refactor -> 验证并提交 diff；Codex 审阅通过后才能进入下一增量。

### 增量 A：让 migration authority 支持 F04 schema

#### 任务 A1：先锁定第二个 revision 的状态机

**Red**

1. 更新 `test_runtime_readiness.py`，断言 `f02_0001` 是 `MANAGED_BEHIND`，`f04_0002` 才是 current。
2. PostgreSQL `f02_0001` schema 被篡改时必须返回 `SCHEMA_DRIFT`，不能继续 upgrade。
3. 更新 `test_f01_adoption.py`，断言未管理 F01 库先 stamp `f02_0001`，再实际执行 F04 revision；四张新表必须存在。
4. 断言 unknown revision 与 partial F04 objects fail closed。
5. 确认 Red 失败原因是当前 head/digest/adoption 仍写死为 F02。

```powershell
cd server
python -m pytest `
  tests/migrations/test_runtime_readiness.py `
  tests/migrations/test_f01_adoption.py `
  tests/migrations/test_schema_guard.py -q
```

**Green**

1. 增加 revision-aware schema contract。
2. 把 F01 adoption target 与 current head 分开。
3. managed-behind upgrade 前验证当前 revision 对应的 schema contract。
4. 保留 advisory lock、脱敏错误与现有 CLI 语义。

#### 任务 A2：显式 schema 与 fresh upgrade

**Red**

1. `test_f04_space_migration.py` 断言 fresh SQLite/PostgreSQL upgrade 后四张表、约束、索引和 revision 存在。
2. `test_model_drift.py` 断言加载 model registry 后 `compare_metadata == []`。
3. 断言只 import legacy `models.py` 不再是测试成立的隐式前提。

**Green**

1. 创建模块 ORM 与 model registry。
2. 编写 revision 的 Expand 部分。
3. 生成并审阅 F04 PostgreSQL canonical schema contract。
4. SQLite 使用 Alembic 支持的方言路径，不用它替代 PostgreSQL 约束证明。

**增量 A 验收**

```powershell
cd server
python -m pytest tests/migrations/test_empty_database.py tests/migrations/test_f04_space_migration.py tests/migrations/test_model_drift.py -q
python -m inkdesk_server.db_migrations status
```

预期：fresh 数据库只通过 Alembic 到 `f04_0002`；F04 schema 与 ORM metadata 一致；F01 adoption 没有跳 revision。

### 增量 B：回填默认拓扑并建立 Workspace Adapter

#### 任务 B1：确定性 topology 与 migration backfill

**Red**

构造至少以下 F02 fixture：

```text
User A -> Workspace 1, Workspace 2, Workspace 3
每个 Workspace 均包含代表性 Source/Topic/Run/Ask/Review/Compile 数据
```

断言 upgrade 后：

- 1 个默认 Organization、1 个 Organization Space。
- 1 个 membership。
- 3 个 Project Spaces、3 个 Personal Overlays、3 个 bindings。
- 每个 Personal Overlay 指向正确 owner membership 与 Project parent。
- 所有旧表 row count 和旧列 fingerprint 完全不变。
- 第二次 upgrade 是 no-op。
- migration 与应用确定性 ID 对同一输入完全一致。
- 另建 User B -> Workspace 4 的 unsupported fixture，断言 migration 在创建任何 F04 row 前失败，不能把两个 owner 自动合并到默认 Organization。

**Green**

1. 实现 revision Backfill/Validate。
2. 不 update `workspaces` 或任何旧业务表。
3. 所有查询与 insert 使用参数绑定，不拼接用户数据。
4. PostgreSQL migration 整体保持事务性；中途失败不写入 `f04_0002`。

#### 任务 B2：fresh seed bootstrap

fresh empty database 执行 migration 时还没有 User/Workspace，因此应用 seed 后必须补 topology。

**Red**

1. migration -> `bootstrap_seed_data()` 后，默认 `workspace-inkdesk` 能解析完整 context。
2. 连续执行 bootstrap 两次，四张 F04 表 row count 与字段不变。
3. 预置字段冲突的确定性 ID 或错误 parent，断言 `SPACE_IDENTITY_CONFLICT` / `SPACE_TOPOLOGY_INVALID`，原值不被覆盖。
4. 一个已有 User 但多个 Workspace 的数据库也能补齐全部缺失 topology，不受当前 `User count > 0` 早退影响。

**Green**

1. 将现有 seed 的早退改为“仅跳过 legacy demo data 创建”，随后始终执行 topology ensure。
2. bootstrap 只写新四表，并依赖唯一约束保证重复安全。
3. 已存在且正确时 no-op；已存在但冲突时 fail closed。

#### 任务 B3：切换三个默认解析入口

**Red**

1. Adapter 按 slug/id 返回完整 `WorkspaceSpaceContext`。
2. binding 缺失、目标不是 Project、跨 Organization parent、错误 owner membership 均失败。
3. HTTP、Research service 与 MCP 仍得到原 `workspace-inkdesk`。
4. 去掉 binding 后，三个入口都不能绕过 Adapter 继续读取旧数据。

**Green**

1. 替换 `research.require_workspace()`、`main._resolve_workspace()`、MCP resolver 的直接查询。
2. 外部仍返回 Workspace 或 workspace ID，不扩大现有 service 改动。
3. 不把 Space context 注入所有旧 service method。

**增量 B 验收**

```powershell
cd server
python -m pytest tests/spaces tests/test_space_compatibility.py -q
python -m pytest tests/test_research_api.py tests/test_run_api.py tests/test_mcp_tools.py -q
```

预期：旧 Workspace 成为可验证的兼容入口；拓扑损坏不能被直接查询绕过；所有旧 ID 和响应保持不变。

### 增量 C：真实演练、故障恢复与签收

#### 任务 C1：F04 隔离 verifier

先在 F03 当前真实数据上生成新的 F01 备份：

```powershell
pwsh -File scripts/f01/capture-baseline.ps1 -Mode all
$F01EvidenceDir = Read-Host "输入刚生成并已确认 PASS 的 evidence 目录"
```

然后用户对该 `PASS` run 执行：

```powershell
pwsh -File scripts/f04/verify-space-migration.ps1 `
  -F01EvidenceDir $F01EvidenceDir
```

verifier 必须：

```text
校验新 F01 manifest 与备份 hash
-> 创建 fresh F04 临时库并 upgrade/seed
-> 从新 F01 dump 恢复到隔离 adopt 库
-> 记录全部 legacy schema/data fingerprints
-> F01 adoption 到 f02，再 upgrade f04
-> 验证 topology cardinality 与 hierarchy
-> 再次 upgrade/bootstrap 验证 no-op
-> 启动隔离 backend，执行 7 条读路径与关键写后读
-> 注入 schema drift / permission / topology corruption / multi-owner / lock failure
-> 演练 rollback-f04
-> 验证回到 f02 后 legacy fingerprints 相等
-> 清理所有临时库与 Vault
-> 生成脱敏 F04 manifest
```

真实源数据库与 Vault 全程只读。临时数据库继续使用受保护前缀，拒绝活动数据库名。

#### 任务 C2：受保护回滚

F04 提供 migration CLI 的 scoped command：

```powershell
cd server
python -m inkdesk_server.db_migrations rollback-f04
```

该命令只允许：

- current revision 精确为 `f04_0002`。
- 四张表只包含可由当前 Workspace/owner 确定性重建的默认 topology。
- 不存在 Domain、第二 Organization、自定义 Space、额外 membership 或字段冲突。
- legacy fingerprints 在 downgrade 前后相等。

满足时，在 advisory lock 内 downgrade 到 `f02_0001` 并删除四张纯派生表；不修改旧 16 张表。发现任何非派生数据时返回 `DB_MIGRATION_ROLLBACK_UNSAFE`，停止并采用前向修复或已验证备份，不 destructive drop。

正常应用回退优先只撤销 Adapter switch，保留 additive F04 schema 与支持 F04 head 的 migration runtime。只有必须部署完整 F03 binary 时，才先运行受保护 rollback，再切换代码。

#### 任务 C3：全量兼容验收

用户执行：

```powershell
cd server
python -m pytest tests/spaces tests/migrations tests/test_space_compatibility.py -q
python -m pytest

# F02 认证的 PostgreSQL 测试入口
python -m pytest tests/migrations tests/test_pgvector_integration.py -q

cd ..
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml up -d --build

python scripts/f01/export_openapi.py compare `
  --url http://localhost:8080 `
  --snapshot docs/delivery/baselines/f01/contracts/openapi.json

cd web
npm run e2e:fullstack
```

F04 无前端变更，不要求新增视觉截图；真实 full-stack 流仍必须证明旧 UI 能读取和写入迁移后的数据。

## 9. F04 完成门禁

只有以下条件全部成立，F04 才能标记完成：

1. F03 已合并，新的迁移前 F01 `-Mode all` run 为 `PASS` 并被 F04 manifest 引用。
2. Alembic head 为 `f04_0002`，fresh SQLite/PostgreSQL 都能从空库升级成功。
3. F01 未管理库先 stamp `f02_0001` 再执行 F04，不直接 stamp 新 head。
4. PostgreSQL 对 f02/f04 使用各自 schema contract；behind drift 在 upgrade 前失败。
5. model registry 覆盖 legacy 与 Space ORM，head 与 metadata drift 为空。
6. 每个现有 Workspace 恰好有一个 Project binding、owner membership 和 Personal Overlay。
7. 单 owner 多 Workspace fixture 的数量、parent、organization、owner 和确定性 ID 全部正确；multi-owner 输入在 mutation 前被拒绝。
8. 所有旧表 schema、row count 和旧列 fingerprint 在 F04 backfill 前后完全不变。
9. migration、bootstrap 和重复启动均幂等；冲突 topology fail closed 且不被覆盖。
10. HTTP、Research service、MCP 和 Compile 路径都经过 Adapter，外部 workspace ID 与行为不变。
11. 没有新增 API；F01 canonical OpenAPI compare 完全通过。
12. focused、后端全量、PostgreSQL integration、Docker 和 full-stack E2E 全部通过。
13. schema drift、DDL permission、migration lock 和 topology corruption 故障注入通过。
14. `rollback-f04` 在纯默认 topology 上恢复到 f02 且 legacy fingerprints 不变，在额外数据存在时拒绝执行。
15. F04 manifest、数据库文档、脚本说明和 cognitive map 已更新，证据可追溯到 commit SHA。

任一旧业务 fingerprint 变化、F01 直接 stamp 到 F04、Adapter 可被默认入口绕过、错误 topology 被静默修复、额外 Space 被 rollback 删除，或通过更新 F01 OpenAPI snapshot 接受契约变化，都属于阻塞失败。

## 10. 回滚策略

### 10.1 Switch 回滚

如果 Adapter 集成导致运行期问题但 schema/topology 正确：

1. 停止服务。
2. 回退三个默认解析入口到原 Workspace 查询。
3. 保留 F04 revision、四张表和 revision-aware readiness 代码。
4. 启动服务并执行旧 API/MCP/full-stack smoke tests。

这是默认回退，因为 F04 schema 是 additive，旧业务逻辑不会读取新表。

### 10.2 完整 F03 binary 回滚

完整 F03 binary 不认识 `f04_0002`，不能直接部署到 F04 数据库。必须：

1. 停止所有写入。
2. 执行 `rollback-f04` 并确认 revision 为 `f02_0001`。
3. 比较 legacy fingerprints。
4. 部署 F03 binary。
5. 验证 readiness、OpenAPI、7 条读路径和全栈主流程。

若 rollback guard 拒绝，禁止强制 drop；保留 F04 migration runtime，前向修复 Adapter，或恢复最新已验证 F01 PostgreSQL + Vault 成对备份。

## 11. 明确范围外

- 不新增登录、注册、邀请、SSO 或用户切换。
- 不新增成员、Organization、Project、Domain 或 Personal Space 管理 API/UI。
- 不创建 Role 表、RBAC engine、permission、visibility、authority 或 Policy 规则。
- 不实现四级能力继承、冲突解析或 Resolution Trace。
- 不创建默认 Domain Space 或伪造不存在的组织层级。
- 不给 Source、Topic、Run、Ask、Review、Retrieval、Compile 等旧表新增 `space_id`。
- 不改变 `workspaceId` request/response、固定默认 workspace 体验或前端类型。
- 不迁移 Vault 目录到 Organization/Space 分层路径。
- 不修改 Skill、Evaluation、Capability Registry 或 Run 状态机。
- 不重构 ResearchWorkspaceService、Compile Worker 或 MCP tool contract。
- 不开始 F05 Durable Job，也不开始 W01 Goal Contract。
- 不把本地 dump、manifest、连接地址或真实组织数据提交到 Git。

## 12. 主要风险与审阅重点

| 风险 | 隐蔽原因 | 发现方式 |
| --- | --- | --- |
| F01 被直接 stamp 到 F04 | 旧代码使用 `HEAD_REVISION` 作为 adoption target | F01 restore 断言 revision 执行轨迹和四表存在 |
| 新 head 永久被判 drift | PostgreSQL digest 仍固定 F01 | revision-aware schema contract 测试 |
| 新 ORM 未进入 metadata | Alembic env 只 import legacy models | registry 测试 + PostgreSQL autogenerate drift |
| 多 owner 被错误合并为一个组织 | 默认 Organization 被误当成无条件数据汇聚桶 | multi-owner fixture 必须在 mutation 前 fail closed |
| 单 owner 多 Workspace 重复 membership | backfill 按 Workspace 而非 distinct owner | 单 owner、多 Workspace cardinality fixture |
| Personal Space 被绑定表写死 | 当前单人模型诱导保存单一 personal ID | binding 只指 Project，personal 按 member 解析 |
| bootstrap 静默覆盖损坏拓扑 | “幂等”被误实现为 upsert all fields | 冲突 fixture 必须 fail closed 且字段不变 |
| 旧数据被无意重写 | 为方便查询批量更新旧表 | 全部 legacy table/column fingerprints |
| Adapter 只是未使用的新代码 | main/research/MCP 继续直接查询 Workspace | 删除 binding 后三入口均失败的集成测试 |
| rollback 删除未来数据 | downgrade 无拓扑来源检查 | 额外 row/domain fixture 必须返回 unsafe |
| F04 越界成团队管理 | 新增 API/UI/RBAC 看似顺手 | 文件边界、OpenAPI exact compare、范围外审阅 |

## 13. 学习与审阅检查点

用户完成每个增量后，应能解释：

1. 为什么 Workspace 是兼容入口，而 CapabilitySpace 才是未来作用域模型。
2. 为什么 Binding 只指 Project，不应保存单一 Personal Space。
3. 为什么 migration backfill 与 fresh seed bootstrap 都需要，但职责不同。
4. 为什么 Alembic revision 不能导入当前应用 bootstrap。
5. 为什么 F01 adoption target 与当前 head 必须分离。
6. 为什么 revision-aware schema contract 比永远比较 F01 digest 更正确。
7. 为什么正常回退保留 additive schema，完整 binary 回退必须先处理 revision。
8. F04 建立了哪些团队原生边界，又刻意没有实现哪些权限与治理行为。

Codex 审阅优先级：旧数据不变与迁移状态机 > 拓扑不变量 > Adapter 不可绕过 > API 兼容 > 命名和格式。

## 14. 计划自审结论

- **单一能力**：只建立默认 Organization/Space topology 与 Workspace 兼容解析，没有夹带团队 UI、RBAC 或能力继承。
- **数据安全**：四张新表 additive；旧表零改写；真实演练使用隔离 restore；rollback 有来源 guard。
- **迁移正确性**：明确解决第二 revision 的 head digest 与 F01 adoption 问题，而不是只增加一份 SQL。
- **团队可扩展性**：Binding 锁定 Project，不把 Personal Overlay 写死为单例；Domain Space 按真实需求后建。
- **兼容性**：旧 `workspace_id`、OpenAPI、MCP、Vault 和前端行为全部保持。
- **可实施性**：文件、模型、revision、测试、Red-Green 顺序、故障注入、证据和回退命令均已确定。
- **前后级清晰**：F04 为 W01/K01/C03/T01 提供归属边界，但不提前实现这些能力。
