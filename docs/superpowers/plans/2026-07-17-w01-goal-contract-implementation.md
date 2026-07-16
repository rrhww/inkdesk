# W01 Goal Contract 实施计划

> 日期：2026-07-17
> 状态：方案已敲定，等待 F05 交付闭环后开始实施
> 路线图：[`2026-07-11-inkdesk-capability-platform-master-roadmap.md`](./2026-07-11-inkdesk-capability-platform-master-roadmap.md)
> 上位设计：[`2026-07-11-inkdesk-team-rd-capability-platform-design.md`](../specs/2026-07-11-inkdesk-team-rd-capability-platform-design.md)
> 直接依赖：F04 默认 Organization / Capability Space
> 集成门禁：F05 `f05_0003`、最终 HEAD 验收清单、远程合并状态
> 后续解锁：W02 Run 状态机 v2、W03 Artifact / Evidence、W05 Context Pack v2、O01 Outcome 手工关联
> 协作分工：用户负责编写失败测试、实现、迁移演练、测试执行和浏览器验收；Codex 负责契约拆解、方案审阅、兼容性检查和验收证据审阅

## 1. 单一交付目标

W01 只交付一项能力：**每个通过新创建入口产生的 Run，都必须在开始执行前固定一份结构化、可验证、带作用域且不可静默修改的 Goal Contract；历史 Run 继续可读，但系统不得为缺失信息伪造完整契约。**

完成后必须成立：

```text
Organization + Project Space + current member
-> structured Goal Contract v1
-> canonical serialization + contract hash
-> DevRun + GoalContract in one transaction
-> immutable read model
-> Run API / Web detail / later TaskSnapshot consumers

legacy DevRun without GoalContract
-> remains readable
-> goalContractState = legacy
-> goalContract = null
-> legacy goal remains visible
```

Goal Contract 不是一段更长的任务描述。它必须在执行前回答：为什么做、谁和什么受到影响、预期行为如何变化、如何证明技术成功、如何判断真实结果、允许什么副作用、观察多久、何时判定失败以及何时回滚。

## 2. 开始实施前的交付门禁

W01 的路线图直接依赖是 F04，但当前仓库的唯一 Alembic 主线已经进入 F05。因此 W01 的文档设计可以完成，生产实现必须等待以下事实全部成立：

1. F05 分支 `rrh/f05-durable-job-attempt-kernel` 已推送并通过 PR 合并到 `origin/main`。
2. `origin/main` 的唯一 Alembic head 是 `f05_0003`，不存在平行 head。
3. F05 最终 HEAD 重新生成交付清单；清单中的 `commit` 必须等于被合并的实现提交。
4. F05 focused suite、PostgreSQL 并发/崩溃恢复演练、现有 Run API 和 full-stack 流程在最终 HEAD 通过。
5. W01 worktree 从更新后的 `origin/main` 创建或 rebase，工作区干净。

当前已知证据是 `.local/f05-jobs/manifest.json` 记录 58 项检查、0 失败、`overallStatus = PASS`，但其绑定提交为 `5806242`，而本地 F05 分支最终验收提交为 `8bdccdd`。这表示 F05 实现与验收基本完成，但交付证据仍需在最终 HEAD 重放并绑定，不能直接把旧清单当作合并提交的证据。

预期 W01 revision：

```text
revision = "w01_0004"
down_revision = "f05_0003"
```

如果 F05 合并后的 revision 或 schema digest 不同，先更新本计划和迁移失败测试，禁止创建第二条迁移链。

## 3. 产品不变量

### 3.1 创建前固定，创建后不可静默修改

- Goal Contract 与 DevRun 在同一数据库事务中创建。
- W01 不提供修改 Goal Contract 的 `PATCH` / `PUT` API。
- 数据模型没有 `updated_at`；应用仓储不暴露 update 方法。
- Canonical JSON 和 SHA-256 hash 用于发现内容漂移。
- 如果未来需要调整目标，必须由后续计划设计 revision / supersede 语义，不能原地覆盖。

这里的“不可变”是 W01 的应用契约，不通过数据库 trigger 冒充完整审计。治理审计与正式修订流程属于后续能力。

### 3.2 不伪造历史数据

旧 `dev_runs.goal` 只包含一段文本，无法可靠推导受影响对象、Outcome、观察窗口和回滚条件。因此：

- 旧 Run 不回填虚构的 Goal Contract。
- 旧 Run 返回 `goalContractState = "legacy"` 和 `goalContract = null`。
- 旧 `goal` 字段、详情页描述、阶段和事件保持可读。
- 新 Run 返回 `goalContractState = "structured"`。

禁止把空数组、`unknown` 或模型生成内容写成历史 Run 的“完整契约”。

### 3.3 Scope 是 Run 的属性，不只是 Workspace 的间接属性

W01 为 `dev_runs` 增加并回填：

- `organization_id`
- `capability_space_id`
- `created_by_membership_id`

当前创建入口固定使用 F04 `WorkspaceSpaceContext` 中的 Organization、Project Space 和 owner membership。W01 不开放 Space 选择器；T01 再增加完整成员与 Space 管理体验。

`workspace_id` 继续保留为兼容字段，不能在 W01 删除。

### 3.4 `goal` 是兼容投影，不再是完整真相

对新 Run：

```text
DevRun.goal = GoalContract.purpose
```

现有阶段动作、MCP 和详情页仍能读取 `goal`。Goal Contract 的 Canonical Truth 是结构化快照；W05 再让 Context Pack 消费完整契约。W01 不在 `stage_actions.py` 中复制一套临时 Prompt 拼接逻辑。

## 4. Goal Contract v1 领域契约

### 4.1 顶层结构

```json
{
  "schemaVersion": 1,
  "purpose": "为什么要做",
  "affectedParties": ["受影响的成员、角色或用户群体"],
  "affectedObjects": [
    {
      "kind": "module",
      "reference": "server/inkdesk_server/modules/runs",
      "description": "Run 与 Goal Contract 边界"
    }
  ],
  "expectedBehaviorChange": "完成后可观察到的行为变化",
  "technicalSuccessCriteria": [
    {
      "name": "旧 Run 兼容读取",
      "target": "历史数据读取成功且不伪造契约",
      "verification": "automated"
    }
  ],
  "outcome": {
    "type": "proxy",
    "criteria": [
      {
        "name": "目标信息完整率",
        "target": "新建 Run 为 100%",
        "verification": "automated"
      }
    ],
    "proxyRationale": "W01 尚未接入真实业务结果数据源"
  },
  "allowedSideEffects": [],
  "observationWindow": {
    "durationHours": 24
  },
  "failureConditions": ["任一新 Run 缺少结构化 Goal Contract"],
  "rollbackConditions": ["迁移或兼容读取导致既有 Run 不可用"]
}
```

### 4.2 字段语义

| 字段 | 语义 | v1 约束 |
| --- | --- | --- |
| `schemaVersion` | 契约解释版本 | 服务端写入 `1`，客户端不能自选 |
| `purpose` | 为什么做，而不是实现步骤 | trim 后 1-2000 字符 |
| `affectedParties` | 谁受到影响 | 1-20 项，每项 1-240 字符 |
| `affectedObjects` | 哪些代码、系统、数据、流程或文档受影响 | 1-50 项；`kind` 使用固定枚举；引用允许为空但描述必填 |
| `expectedBehaviorChange` | 交付前后可辨别的行为差异 | trim 后 1-4000 字符 |
| `technicalSuccessCriteria` | 技术正确性和质量门槛 | 1-20 项；每项包含名称、目标和验证方式 |
| `outcome.type` | 真实结果还是代理结果 | 仅 `direct` / `proxy` |
| `outcome.criteria` | 用户、业务或代理成功标准 | 1-20 项；不得与技术测试简单重复 |
| `outcome.proxyRationale` | 为什么只能使用代理指标 | `proxy` 时必填，`direct` 时必须为空 |
| `allowedSideEffects` | 明确允许的副作用 | 字段必传；空数组表示不允许已知副作用 |
| `observationWindow.durationHours` | 交付后观察时长 | 整数 0-8760；0 表示即时人工/自动验收 |
| `failureConditions` | 哪些事实意味着目标失败 | 1-20 项 |
| `rollbackConditions` | 哪些事实要求执行回退 | 1-20 项 |

固定枚举：

```text
affectedObjects.kind:
repository | service | module | api | data | workflow | documentation | infrastructure | other

criterion.verification:
automated | manual

outcome.type:
direct | proxy
```

手工验收不是第三种 Outcome 类型。没有直接业务指标的文档、重构、内部工具和基础设施任务仍标记为 `proxy`，其 criterion 可使用 `verification = manual`，并在 `proxyRationale` 中说明原因。这样不会把人工验收伪装成真实业务 Outcome。

### 4.3 领域验证原因码

领域层返回稳定、与 FastAPI/Pydantic 解耦的原因码：

| 原因码 | 含义 |
| --- | --- |
| `GOAL_CONTRACT_REQUIRED` | 新创建入口未提供契约 |
| `GOAL_CONTRACT_INVALID_TEXT` | 必填文本为空或超限 |
| `GOAL_CONTRACT_INVALID_CARDINALITY` | 数组数量不满足约束 |
| `GOAL_CONTRACT_INVALID_OBJECT_KIND` | 受影响对象类型未知 |
| `GOAL_CONTRACT_INVALID_VERIFICATION` | 验证方式未知 |
| `GOAL_CONTRACT_PROXY_RATIONALE_REQUIRED` | proxy 缺少原因 |
| `GOAL_CONTRACT_DIRECT_RATIONALE_FORBIDDEN` | direct 携带了 proxy 原因 |
| `GOAL_CONTRACT_INVALID_OBSERVATION_WINDOW` | 观察时长不合法 |
| `GOAL_CONTRACT_SCOPE_INVALID` | Organization / Project Space / membership 不一致 |

错误消息不能回显整份 Goal Contract，避免把业务信息和未来可能出现的敏感内容写入普通日志。

### 4.4 Canonical 序列化与 hash

- 使用 UTF-8、字段名固定、key 排序、紧凑分隔符的 JSON。
- 所有文本先 trim；数组保持用户声明顺序，不暗中排序。
- hash 为 canonical bytes 的 SHA-256 十六进制值。
- 同一领域值在 Python 进程、SQLite 和 PostgreSQL 中必须得到相同 hash。
- API 响应从已保存的 canonical JSON 反序列化，不能从 `dev_runs.goal` 重新拼装。

## 5. 持久化设计

### 5.1 `dev_runs` Expand / Backfill

新增非空外键：

```text
organization_id          -> organizations.id       ON DELETE RESTRICT
capability_space_id      -> capability_spaces.id   ON DELETE RESTRICT
created_by_membership_id -> organization_memberships.id ON DELETE RESTRICT
```

迁移顺序：

1. 以 nullable 形式 expand 三列。
2. 通过 `workspace_space_bindings`、Project Space 和 workspace owner membership 幂等回填。
3. 检查每个 DevRun 恰好解析出一个 Organization、Project Space 和 membership。
4. 若缺失或歧义，迁移失败并输出计数/ID，不部分提交。
5. 增加外键、索引和 non-null 约束。

### 5.2 `run_goal_contracts`

```text
id               varchar(64) primary key
run_id           varchar(64) not null unique -> dev_runs.id ON DELETE CASCADE
schema_version   smallint not null
contract_json    text not null
contract_hash    varchar(64) not null
created_at       timestamptz not null
```

约束：

- 一个 Run 最多一个 v1 Goal Contract。
- `schema_version = 1` 使用 check constraint。
- `contract_hash` 长度为 64；不要求全局 unique，不同 Run 可以拥有相同目标。
- 不为历史 Run 插入行。
- 不添加 `updated_at`、soft delete 或 revision 表。

Goal Contract 使用关系数据库中的结构化 JSON 快照，是运行真相，不写入 RunEvent payload，也不写入 Vault/Git。事件只记录：

```json
{
  "goalContractId": "gcontract-...",
  "goalContractVersion": 1,
  "goalContractHash": "..."
}
```

### 5.3 事务与并发

- Scope 解析、DevRun 创建、Goal Contract 创建和 `created` RunEvent 在一个事务中提交。
- 任一步失败都不能留下 orphan Run 或 orphan Contract。
- `run_id` unique 是最后一道一对一并发约束。
- 创建 API 不自动重试未知数据库错误，不生成第二个 Run。
- W01 不复用 F05 Job；创建 Run 是短事务，不需要后台执行。

## 6. API 与兼容策略

### 6.1 创建请求

`POST /api/runs` 改为：

```json
{
  "type": "PRD",
  "title": "结构化目标示例",
  "repoContext": "inkdesk",
  "goalContract": {
    "purpose": "...",
    "affectedParties": ["..."],
    "affectedObjects": [{"kind": "module", "reference": "...", "description": "..."}],
    "expectedBehaviorChange": "...",
    "technicalSuccessCriteria": [{"name": "...", "target": "...", "verification": "automated"}],
    "outcome": {"type": "proxy", "criteria": [{"name": "...", "target": "...", "verification": "manual"}], "proxyRationale": "..."},
    "allowedSideEffects": [],
    "observationWindow": {"durationHours": 24},
    "failureConditions": ["..."],
    "rollbackConditions": ["..."]
  }
}
```

旧请求中的顶层 `goal` 不再承担创建真相。当前产品没有稳定外部 API 版本承诺，因此 W01 选择一次明确的写契约升级，而不是允许新系统继续制造不完整 Run。所有第一方调用、测试 fixture 和浏览器流程同步升级。

这是**有意的创建请求 breaking change**；必须出现在 W01 OpenAPI diff 和兼容说明中。读取兼容不等于永久保留不完整写入口。

### 6.2 详情响应

`GET /api/runs/{run_id}` 和所有返回完整 `DevRunResponse` 的旧阶段接口增加：

```json
{
  "organizationId": "org-...",
  "capabilitySpaceId": "space-project-...",
  "createdByMembershipId": "membership-...",
  "goal": "兼容 purpose 投影",
  "goalContractState": "structured",
  "goalContract": {
    "id": "gcontract-...",
    "schemaVersion": 1,
    "hash": "...",
    "purpose": "..."
  }
}
```

历史 Run：

```json
{
  "goal": "原始文本目标",
  "goalContractState": "legacy",
  "goalContract": null
}
```

`DevRunSummaryResponse` 在 W01 不扩展完整 Contract，避免列表 payload 膨胀。列表继续展示 title/type/status/stage；详情才加载契约。

### 6.3 路由与兼容 Facade

- 将 `POST /api/runs`、`GET /api/runs`、`GET /api/runs/{id}` 迁入 `modules/runs/api.py`，由 F03 API shell 注册。
- 从 `main.py` 删除这三个重复定义，并用 composition test 证明每个 method/path 只有一个 handler。
- `run_service.py` 暂时保留为阶段动作、MCP、deposit 和旧服务的兼容 Facade。
- W01 只把创建和读取委托给 Runs application service；状态转换仍留在旧 `RunService`，由 W02 迁移。
- 不移动或重写 `stage_actions.py`。

### 6.4 OpenAPI 演进证据

- F01 OpenAPI snapshot 保持不可变，不能覆盖历史基线。
- 生成 W01 当前 OpenAPI snapshot 与 machine-readable diff。
- diff 只允许：Goal Contract schemas、Run scope/contract response 字段、创建 request 变化。
- 任何 Compile、Knowledge、MCP、Health、Coding 或 Evaluation API 差异都阻塞 W01。
- exact-current contract test 对 W01 snapshot；baseline-diff test 对批准的 W01 delta。

## 7. 模块与文件边界

### 7.1 后端新增

```text
server/inkdesk_server/modules/runs/__init__.py
server/inkdesk_server/modules/runs/domain.py
server/inkdesk_server/modules/runs/models.py
server/inkdesk_server/modules/runs/repository.py
server/inkdesk_server/modules/runs/service.py
server/inkdesk_server/modules/runs/schemas.py
server/inkdesk_server/modules/runs/api.py
server/inkdesk_server/modules/runs/projections.py

server/alembic/versions/20260717_w01_0004_goal_contract.py
server/tests/runs/test_goal_contract_domain.py
server/tests/runs/test_goal_contract_serialization.py
server/tests/runs/test_run_creation.py
server/tests/runs/test_legacy_run_projection.py
server/tests/migrations/test_w01_goal_contract_migration.py
```

### 7.2 后端修改

```text
server/inkdesk_server/api/app.py
server/inkdesk_server/api/dependencies.py
server/inkdesk_server/model_registry.py
server/inkdesk_server/db_migrations.py
server/inkdesk_server/schema_contract.py
server/inkdesk_server/models.py
server/inkdesk_server/run_service.py
server/inkdesk_server/main.py
server/inkdesk_server/schemas.py
server/tests/api/test_runtime_composition.py
server/tests/test_run_api.py
cognitive-map.md
```

`models.py` 和 `schemas.py` 只保留最小兼容修改；Goal Contract 的新 ORM/Pydantic 定义不得继续堆入这两个热点文件。

### 7.3 前端新增

```text
web/features/runs/types.ts
web/features/runs/api.ts
web/features/runs/components/goal-contract-form.tsx
web/features/runs/components/goal-contract-summary.tsx
web/app/app/runs/new/page.tsx
web/tests/unit/goal-contract-form.test.tsx
web/tests/unit/goal-contract-summary.test.tsx
web/tests/e2e/w01-goal-contract.spec.ts
```

### 7.4 前端修改

```text
web/components/workbench/dev-run-console.tsx
web/app/app/runs/[id]/page.tsx
web/lib/types.ts
web/lib/research.ts
web/tests/unit/dev-run-console.test.tsx
web/tests/e2e/dev-run-console.spec.ts
web/tests/e2e/local-fullstack.spec.ts

docs/delivery/contracts/w01/openapi.json
docs/delivery/contracts/w01/openapi-diff.json
docs/delivery/runs/w01/README.md
docs/delivery/runs/w01/manifest.schema.json
docs/delivery/runs/w01/manifest.json
```

`web/lib/types.ts` 和 `web/lib/research.ts` 只保留兼容 re-export/delegation；新 Run 契约与 API 调用归 `web/features/runs/`。

## 8. 分阶段开发计划

每个任务都执行：先写失败测试，运行并确认因为目标能力缺失而失败；再实现最小改动；最后运行 focused suite。禁止一次写完所有测试后再批量实现。

### 阶段 0：关闭 F05 并建立 W01 基线

#### 任务 0.1：F05 最终证据绑定

失败条件：manifest commit 不等于最终 F05 HEAD，或最终 HEAD 未重放 58 项检查。

完成条件：

- F05 verifier 在最终 HEAD 重新执行并 PASS。
- manifest 的 commit/hash/timestamp 更新。
- F05 分支推送、PR 合并，`origin/main` 可追溯到验收提交。

#### 任务 0.2：创建 W01 worktree

```powershell
git fetch origin
git worktree add .worktrees/w01-goal-contract -b rrh/w01-goal-contract origin/main
```

先验证 sole head、F04 topology、F05 migration/jobs 和现有 Run API，再开始 W01。

### 阶段 A：纯 Goal Contract 领域

#### 任务 A1：值对象和验证矩阵

先覆盖：

- 最小合法 direct Contract。
- 最小合法 proxy + manual acceptance Contract。
- 每个必填字段缺失/空白/超限。
- 数组 0 项和超上限。
- 非法 object kind / verification / outcome type。
- proxy 无 rationale、direct 带 rationale。
- observation 小于 0、大于 8760、非整数。

实现不得导入 FastAPI、SQLAlchemy、Settings、Clock 或文件系统。

#### 任务 A2：Canonical serialization/hash

先证明：

- 等价 key 顺序得到同一 hash。
- 文本 trim 后稳定。
- 数组顺序变化会改变 hash。
- 非 ASCII 内容在序列化和往返后不损坏。

#### 阶段 A 门禁

- 纯领域测试无需数据库和 Web 环境即可运行。
- v1 字段、枚举、原因码和 hash 规则经审阅后冻结。
- 后续阶段不得为了方便 UI 临时改变领域语义。

### 阶段 B：Scope Backfill 与 Goal Contract 持久化

#### 任务 B1：先写 migration tests

至少覆盖：

1. `f05_0003 -> w01_0004` 升级。
2. fresh database 全链升级。
3. 重复 upgrade 幂等。
4. 多 Workspace / 多 Run 正确绑定各自 Organization、Project Space、membership。
5. 缺少 binding、Project Space 或 membership 时 fail closed。
6. 历史 Run 没有 `run_goal_contracts` 记录。
7. FK、unique、check、index 和 ORM model drift 对齐。
8. 有 Goal Contract 数据时 guarded downgrade 拒绝丢弃。

#### 任务 B2：实现 `w01_0004`

只包含本计划定义的一组 scope 列和一张 Goal Contract 表，不夹带 W02 状态字段、W03 Artifact 表或 O01 Outcome 表。

#### 任务 B3：Repository 原子创建

先写数据库集成测试证明：

- 成功时 Run/Contract/Event 一起存在。
- Contract 插入失败时三者都不存在。
- 同一 Run 第二份 Contract 被 unique 拒绝。
- 保存后读取的 canonical JSON 和 hash 一致。
- repository 没有 update/delete Contract 公共方法。

#### 阶段 B 门禁

- Alembic 仍只有一个 head。
- PostgreSQL 是 schema/constraint 的正式证据；SQLite 只承担快速开发反馈。
- 迁移前后的既有业务表 row fingerprint 除预期 scope 列外不变。

### 阶段 C：Run API 与兼容投影

#### 任务 C1：Application service

先覆盖新创建流程中的 type 校验、scope 一致性、Contract 验证、goal projection、event hash 引用和事务回滚。

#### 任务 C2：历史读取兼容

以真实旧 DevRun fixture 证明：

- `goal`、status、stage、events、timestamps 不变。
- scope 字段来自 migration backfill。
- Contract 缺失时返回明确 `legacy/null`，不会 500。
- 列表仍可读取且不发生 N+1 Contract 查询。

#### 任务 C3：迁移三个 HTTP 路由

先让 composition test 因重复/缺失路由失败，再迁入 API shell。验证 auth/error handlers/dependencies 与旧路径一致。

#### 任务 C4：OpenAPI delta

更新第一方 Run fixtures，生成 W01 snapshot 和批准 diff；确认没有无关 API 漂移。

#### 阶段 C 门禁

- 新 Run 不可能通过正式 API 绕过 Goal Contract。
- 旧 Run 可读，旧完整响应字段未删除或改义。
- 所有阶段 mutation 返回的 `DevRunResponse` 都包含一致 Contract 投影。
- 不修改状态转换或失败语义。

### 阶段 D：创建 Run 与详情 UI

#### 任务 D1：独立创建页面

将首页的简短内联表单替换为 `/app/runs/new` 创建页。页面分为连续的三个信息区：

1. 目标与变化：type、title、purpose、expected behavior。
2. 影响边界：affected parties、affected objects、allowed side effects。
3. 成功与回退：technical criteria、Outcome type/criteria、proxy rationale、observation window、failure/rollback conditions。

动态列表必须支持新增、删除、校验定位和键盘操作；提交期间防重复；服务端原因码映射到字段或页面级错误。

#### 任务 D2：详情 Goal Contract 摘要

详情页在阶段轨道之前展示可扫描的 Goal Contract：目标、影响、技术门槛、Outcome 类型、观察窗口、副作用和回退条件。hash/version 放在次要元数据位置，不用原始 JSON 作为主要界面。

旧 Run 展示明确的“历史文本目标”状态，不显示一组假的空字段，也不阻塞旧阶段查看。

#### 任务 D3：前端类型与 API 收口

新类型和调用进入 `web/features/runs/`；现有公共导出先兼容，避免 W01 顺便迁移所有 Run 页面。

#### 阶段 D 门禁

- 表单不能提交领域上无效的 Contract，但服务端仍独立验证。
- direct/proxy 切换不会保留非法隐藏值。
- 最长允许文本、20 项列表和窄屏不重叠、不溢出。
- 桌面和移动端真实浏览器完成创建、查看、错误修正和历史 Run 阅读。

### 阶段 E：交付验收

#### 任务 E1：回归矩阵

执行：

```powershell
Set-Location server
python -m pytest tests/runs tests/migrations/test_w01_goal_contract_migration.py tests/api/test_runtime_composition.py tests/test_run_api.py -q
python -m alembic heads
python -m pytest -q

Set-Location ../web
npm run unit -- tests/unit/goal-contract-form.test.tsx tests/unit/goal-contract-summary.test.tsx tests/unit/dev-run-console.test.tsx
npm run typecheck
npm run lint
npm run build
npm run e2e -- tests/e2e/w01-goal-contract.spec.ts
npm run e2e:fullstack
```

设置 `INKDESK_TEST_PGVECTOR_URL` 后，migration/schema/backfill focused suite 必须在 PostgreSQL 再执行一次；没有 PostgreSQL 证据不能完成阶段 B。

覆盖范围：

```text
Goal Contract pure domain
Runs repository/application/API
W01 migration + model drift + sole head
F04 Space topology
F05 migration/jobs focused suite
existing Run/Stage/MCP tests
web unit/typecheck/lint/build
local full-stack E2E
W01 real-browser flows
```

#### 任务 E2：交付清单

生成 `docs/delivery/runs/w01/README.md` 和 machine-readable manifest，至少记录：

- commit、migration head、schema digest。
- 测试套件数量、通过/失败/跳过。
- 新 Run Contract id/version/hash 与 scope。
- 旧 Run legacy projection 证据。
- 原子回滚与 duplicate Contract 拒绝证据。
- OpenAPI delta 路径和分类。
- desktop/mobile 浏览器验收结果。
- 已知限制和回退步骤。
- `cognitive-map.md` 中“已理解 / 模糊区 / 黑盒区”的 W01 更新。

manifest 只记录 ID/hash/计数，不复制业务 Goal Contract 全文。

## 9. 浏览器验收场景

必须在真实本地服务中验证，而不只依赖 mock：

1. 创建 direct Outcome 的 PRD Run，详情展示全部字段。
2. 创建 proxy + manual criterion 的 REFACTOR Run，rationale 和 0 小时即时验收正确显示。
3. 清空 affected party、technical criterion、rollback condition，提交被定位阻止。
4. 从 proxy 切换 direct，proxy rationale 被清除且 payload 合法。
5. 服务端返回领域错误时保留用户输入，不跳回首页。
6. 双击/快速重复提交只创建一个 Run。
7. 打开迁移前旧 Run，文本目标、阶段、事件仍可操作。
8. 360px、768px、1440px 视口无横向溢出、文字遮挡或动态列表位移。

截图只作为视觉证据；网络请求、数据库记录和 API 响应才证明 Contract 已持久化。

## 10. 回退与恢复

### 10.1 应用回退

W01 上线后如果新 UI 或 API 出现问题：

- 停止创建入口，保留读取。
- 不删除已经创建的 Goal Contract。
- 回退前端到只读 Run 列表/详情时，后端仍保持 W01 schema。
- 不能切回旧 POST 并继续制造无 Contract Run。

### 10.2 数据库回退

- 迁移前执行 PostgreSQL + Vault 成对备份并验证恢复点。
- 尚无 Goal Contract 数据时，可 guarded downgrade 删除新增表/列。
- 已存在 Goal Contract 时，默认拒绝 downgrade；旧 binary 不认识 W01 schema 时使用备份恢复作为最后手段。
- 恢复会丢失备份后的写入，必须记录影响窗口。

## 11. 明确不做

W01 不做：

- W02 的 Run 状态机、blocked/failed/retry 原因码重构。
- W03 的 Artifact / Evidence 模型。
- W04 Capability Manifest。
- W05 Context Pack 对完整 Contract 的消费。
- O01 ChangeSet、Deployment、ObservationWindow、OutcomeMetric 实体与真实结果采集。
- F05 Job 接入、后台执行或 Harness checkpoint。
- Goal Contract 编辑、修订、审批或版本晋级流程。
- 完整 Space 选择器、成员管理或 RBAC。
- `DevRun` ORM 的一次性搬家和 `stage_actions.py` 拆分。
- 覆盖 F01 历史 OpenAPI baseline 来隐藏 breaking change。

## 12. W01 完成门禁

只有以下条件全部成立，W01 才能标记完成并解锁 W02/W03/W05/O01：

1. F05 已合并，W01 基于合并后的唯一 `f05_0003` head。
2. Goal Contract v1 的字段、枚举、验证、canonical JSON 和 hash 有纯领域测试。
3. 所有新正式 API 创建的 Run 都有 Organization、Project Space、creator membership 和一份 Contract。
4. Run、Contract、created event 在一个事务中提交；失败不留 orphan。
5. Contract 创建后没有应用修改路径；读取 hash 与保存 hash 一致。
6. 历史 Run 返回 `legacy/null` 且所有旧字段、阶段和事件可读。
7. scope backfill 在完整数据上成功，在缺失/歧义数据上 fail closed。
8. fresh/current/repeat migration、PostgreSQL constraints、schema digest、model drift 和 guarded downgrade 通过。
9. OpenAPI diff 只包含批准的 W01 变化，F01 baseline 未被覆盖。
10. 新创建页面和详情摘要在桌面/移动真实浏览器通过。
11. 现有 Run、Stage、MCP、F04 Space、F05 Job、Compile 和 full-stack 回归通过。
12. W01 manifest 绑定最终提交，不包含 Contract 全文或敏感信息。
13. `cognitive-map.md` 与总路线图状态已更新，尚未理解的 Outcome 修订/审计边界没有被写成既定事实。

以下任一情况属于阻塞失败：

- 允许新 Run 没有 Goal Contract。
- 从旧 `goal` 自动编造完整 Contract。
- Goal Contract 只存在于 RunEvent JSON 或前端状态。
- Contract 与 Run 分事务提交。
- direct/proxy 语义混淆，或文档/重构被伪装为 direct Outcome。
- Run 仍只有 Workspace 间接作用域。
- W01 创建平行 Alembic head。
- 为 W01 提前重写状态机、接入 Job/Harness 或创建 Outcome 实体。
- 通过覆盖 F01 snapshot 接受无关 API 漂移。

## 13. 完成后的下一步

W01 完成后：

- 主线下一计划是 W02 Run 状态机与失败语义 v2。
- W03 Artifact / Evidence 依赖 W02，不能与 W02 同时修改 Runs domain。
- O01 仍依赖后续 H04，不因 W01 已有 Outcome 声明就提前实现真实观测。
- W05 可使用 W01 Contract，但仍需等待 W03/W04。
- 与 W02 无共享写边界的 Evaluation 前置工作可另行评估并行，不能直接修改 Runs migration/API。

## 14. 实施者应能解释的关键问题

W01 验收时，用户应能清楚解释：

1. 为什么 Goal Contract 不能继续塞进 `dev_runs.goal` 或 RunEvent payload。
2. 为什么旧 Run 返回 legacy/null 比自动补全更诚实。
3. 为什么 `goal` 仍保留，以及它与 Canonical Contract 的关系。
4. 为什么 Run 要直接绑定 Organization / Project Space。
5. 为什么 proxy Outcome 与 manual verification 是两个不同维度。
6. 为什么创建请求的 breaking change 必须显式记录，而不能靠 optional fallback 隐藏。
7. 为什么 W01 不接入 F05 Job，也不开始 W02 状态机。
8. canonical hash 能证明什么、不能替代什么审计能力。
