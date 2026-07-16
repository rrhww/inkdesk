# F05 Durable Job / Attempt Kernel 实施计划

> 日期：2026-07-16
> 状态：待用户确认；阶段 A 可与 F04 立即并行，阶段 B/C 等待 F04 合并后实施
> 路线图：[`2026-07-11-inkdesk-capability-platform-master-roadmap.md`](./2026-07-11-inkdesk-capability-platform-master-roadmap.md)
> 上位设计：[`2026-07-11-inkdesk-team-rd-capability-platform-design.md`](../specs/2026-07-11-inkdesk-team-rd-capability-platform-design.md)
> 领域前置：F02 Alembic 数据库迁移权威、F03 模块化应用组合壳
> 持久化集成门禁：F04 `f04_0002`、model registry 与 WorkspaceSpaceContext 已合并到 `origin/main`
> 后续解锁：E03 隔离 EvalRun、K05 耐久 Knowledge Compiler、H02 Harness Checkpoint
> 协作归属：用户负责编写失败测试、领域/持久化/Worker 代码和故障演练；Codex 负责拆解状态机、审阅并发与恢复语义、检查 migration 和验收证据

## 1. 单一交付目标

F05 只交付一项能力：**建立通用、关系数据库持久化的 Job / Attempt 执行内核，并把现有 Compile Worker 接入，使任务在进程崩溃、服务重启、重复入队和 lease 失效后仍可被安全接管，且不会覆盖失败历史或重复提交已认证的数据库副作用。**

完成后必须成立：

```text
Command + idempotency key
-> durable Job
-> atomic claim
-> Attempt + lease token + heartbeat
-> registered Handler
-> success / failure / lease loss evidence
-> retry creates a new Attempt

process crash
-> current lease expires
-> old Attempt becomes ABANDONED
-> eligible Job returns to PENDING
-> another Worker creates a new Attempt
-> stale Worker cannot commit completion
```

F05 使用 **at-least-once delivery + durable idempotency + fencing**。计划不宣称通用 exactly-once：进程、数据库和外部系统之间不存在免费的一次性语义。F05 能证明的是：

- 一个 Job 同时最多一个 active Attempt。
- stale lease 不能提交 Job/Attempt 成功状态。
- Compile handler 的 ReviewItem 写入、legacy CompileTask 状态与 Job/Attempt completion 在同一数据库事务中提交。
- 未来外部副作用必须提供自己的 idempotency/Outbox/compensation；F05 不用日志或内存标志伪造保证。

## 2. 并行实施边界

F04 当前正在实现且尚未合并。F05 分为两个实施门，不能跨越。

### 2.1 阶段 A：现在可立即开发

阶段 A 只建立无数据库、无线程、无 FastAPI 的纯领域协议。

允许新增：

```text
server/inkdesk_server/infrastructure/__init__.py
server/inkdesk_server/infrastructure/jobs/__init__.py
server/inkdesk_server/infrastructure/jobs/domain.py
server/inkdesk_server/infrastructure/jobs/policies.py
server/inkdesk_server/infrastructure/jobs/contracts.py
server/tests/jobs/test_job_state_machine.py
server/tests/jobs/test_attempt_state_machine.py
server/tests/jobs/test_lease_policy.py
server/tests/jobs/test_retry_policy.py
server/tests/jobs/test_idempotency_contract.py
```

阶段 A 禁止：

- 新增 Alembic revision 或 ORM models。
- 修改 `db_migrations.py`、`schema_contract.py`、`model_registry.py`、`alembic/env.py`。
- 修改 `compile_worker.py`、`research.py`、`main.py` 或现有 Compile API。
- 导入 F04 未合并的 Organization/Space models。
- 写需要数据库、sleep、真实线程或 Docker 才能验证的测试。

阶段 A 的提交应能基于当前 `origin/main` 独立通过；F04 延期或调整不影响它的领域测试。

### 2.2 阶段 B/C：F04 合并后开发

开始前必须：

1. F04 实现已提交并合并到 `origin/main`。
2. F04 Alembic head、revision ID、四张表和 schema digest 已通过验收。
3. F04 model registry 的公开加载方式已稳定。
4. `WorkspaceSpaceContext` 或等价公共 Adapter 能返回 Organization 与 Project Space，不直接查询 Space 模块内部表。
5. F05 worktree 无未提交变更；阶段 A 已提交后执行 `git fetch origin` 与 `git rebase origin/main`。
6. 用户先运行 F04 focused migration/space tests，确认 rebase 基线是 Green。

预期 F05 revision 为 `f05_0003`，`down_revision = "f04_0002"`。如果 F04 最终 revision ID 或 public context 不同，先更新本计划与失败测试，禁止创建平行 Alembic head。

## 3. 当前 Compile Worker 的失败模型

### 3.1 内存 Queue 不是执行权威

当前 `CompileWorker` 使用进程内 `queue.Queue[str]`：

- `_enqueue_compile_for_source()` 在数据库 commit 前把 task ID 放入内存 Queue，Worker 可能先消费却读不到未提交 task。
- 进程退出后 Queue 消失，只能在启动时扫描 `CompileTask.status == PENDING`。
- 两个 server/Worker 可以同时扫描同一 PENDING task，没有原子 claim。
- `RUNNING` 没有 owner、lease、heartbeat 或 fencing token，无法区分仍在运行与永久失联。
- Worker 捕获顶层异常后只写日志，任务可能长期停留在不可解释状态。

### 3.2 Retry 覆盖失败历史

`POST /api/compile/{task_id}/retry` 当前把原 CompileTask 与五个 CompileStep 全部重置为 PENDING，并清空错误、时间和 payload。用户能重试，但第一次失败的 attempt/owner/时间/错误没有独立耐久记录。

F05 保留现有 CompileTask/CompileStep 作为兼容 workflow read model，同时把每次执行保存为不可覆盖的 JobAttempt。legacy step reset 行为暂时保留以维持 API/UI，但不能再删除 Attempt 失败历史。

### 3.3 当前幂等只是一段竞态查询

当前 enqueue 先查询相同 `content_hash` 且状态为 PENDING/RUNNING 的 CompileTask，再插入新 task。两个并发事务都可能先查询不到，然后各自创建 task 和 Review。

F05 必须用数据库唯一性约束承担 active dedup，不能把 Python `SELECT before INSERT` 当作并发保证。

## 4. 领域契约

### 4.1 Job 状态机

内部状态使用小写稳定值：

```text
pending
running
succeeded
failed
cancelled
```

合法转换：

```text
pending -> running                       atomic claim
pending -> cancelled                     尚未执行时取消
running -> succeeded                     当前 lease 条件提交成功
running -> failed                        handler 失败且不自动重试
running -> pending                       lease loss / retryable failure 且仍有预算
running -> cancelled                     cooperative cancellation
failed -> pending                        只允许显式人工 retry
```

规则：

- `succeeded`、`cancelled` 为终态。
- `failed -> pending` 不复用旧 Attempt；下一次 claim 创建新 Attempt。
- Job status 只描述当前可执行性，完整历史来自 Attempts。
- 非法转换返回领域结果/稳定原因码，不在 domain 层直接抛 SQLAlchemy/FastAPI 异常。

### 4.2 Attempt 状态机

```text
leased -> running -> succeeded
                  -> failed
leased/running -> abandoned
leased/running -> cancelled
```

规则：

- 每个 Attempt 具有递增 `attempt_number` 和不可复用 `lease_token`。
- terminal Attempt 永不改回 active，也不删除。
- lease 超时产生 `abandoned`，重试创建新 Attempt。
- 同一个 Job 同时最多一个 `leased/running` Attempt。
- Job completion 必须引用当前 active Attempt；旧 attempt token 返回 `JOB_LEASE_LOST`。

### 4.3 稳定原因码

| 原因码 | 含义 | 自动动作 |
| --- | --- | --- |
| `JOB_NOT_CLAIMABLE` | Job 非 pending、未到 available time 或已终态 | 跳过 |
| `JOB_ACTIVE_ATTEMPT_EXISTS` | 已有 active Attempt | 不重复 claim |
| `JOB_LEASE_EXPIRED` | heartbeat 超时 | abandon；按 policy 决定是否重新 pending |
| `JOB_LEASE_LOST` | token/attempt 已被替换或过期 | stale Worker 回滚，不提交副作用 |
| `JOB_HEARTBEAT_REJECTED` | token 不匹配或 Attempt 非 active | Worker 停止提交路径 |
| `JOB_HANDLER_NOT_REGISTERED` | Job kind 无 handler | fail，不自动猜测 |
| `JOB_HANDLER_FAILED` | handler 返回/抛出执行失败 | 按 retry policy |
| `JOB_MAX_ATTEMPTS_EXCEEDED` | 重试预算耗尽 | Job failed |
| `JOB_IDEMPOTENCY_CONFLICT` | 同 key 的 immutable command 内容不同 | fail closed |
| `JOB_CANCELLED` | Job 已取消 | 不执行 handler |

错误消息不得包含 payload 全文、Vault 内容、连接地址、Secret 或模型凭证。

### 4.4 Idempotency 与 active dedup

F05 区分两个概念：

- `idempotency_key`：一个已接受 Command 的永久身份，unique 且 immutable。相同 key + 相同 kind/scope/payload 返回原 Job；相同 key + 不同 command 返回 conflict。
- `deduplication_key`：可选的业务活跃窗口约束，只在 Job 为 pending/running 时 unique；terminal 后允许用户发起新的显式业务操作。

Compile Adapter 使用：

```text
idempotency_key  = compile-task:{compile_task_id}
deduplication_key = compile:{workspace_id}:{source_id}:{compile_content_hash}
```

因此并发点击同一未完成 Compile 只创建一个 active task/job；任务 terminal 后，当前 API 仍可按原语义创建新的 CompileTask。手工 retry 复用同一 Job 并创建新 Attempt，不创建第二个 active Job。

### 4.5 Lease、heartbeat 与 fencing

默认配置：

```text
INKDESK_JOB_POLL_INTERVAL_SECONDS=1
INKDESK_JOB_LEASE_SECONDS=60
INKDESK_JOB_HEARTBEAT_SECONDS=10
INKDESK_JOB_SHUTDOWN_GRACE_SECONDS=10
INKDESK_JOB_DEFAULT_MAX_ATTEMPTS=3
```

约束：heartbeat interval 必须小于 lease 的一半；lease、heartbeat、available time 使用 UTC。PostgreSQL repository 使用数据库时间判定过期，避免多个 Worker 主机时钟漂移；SQLite 个人模式使用注入 Clock 并只认证单 Worker。

Claim 创建 Attempt 并生成随机 `lease_token`；`attempt_number` 同时充当单调 fencing number。heartbeat 和 finish 都必须使用：

```text
job_id + attempt_id + attempt_number + lease_token + active status
```

做条件更新。更新 row count 为 0 时视为 lease lost，handler 所在事务整体回滚。不能先提交业务副作用，再单独尝试把 Job 标记成功。

### 4.6 Retry policy

F05 不对所有异常自动重试：

- lease expired：Compile handler 声明为可从数据库事务回滚后重做，预算内自动创建新 Attempt。
- handler 业务异常：保持现有行为，Job/CompileTask FAILED，等待用户调用 retry。
- handler not registered、payload/schema 错误、permission/policy denied：不自动重试。
- 数据库短暂错误：claim/heartbeat 可退避重试；无法证明 lease 有效时不得提交 handler result。
- 每次 manual/automatic retry 都增加 attempt number，旧错误不覆盖。
- `max_attempts` 限制自动恢复预算；一次合法 manual retry 显式授予一个新 Attempt 名额，使 `max_attempts >= attempt_count + 1`，不把旧 Attempt 计数清零。

## 5. 持久化模型（阶段 B）

### 5.1 `jobs`

| 字段 | 语义 |
| --- | --- |
| `id` | String(64) PK |
| `organization_id` | F04 Organization FK，非空 |
| `capability_space_id` | F04 Project Space FK，非空 |
| `kind` | handler registry key，如 `compile_source` |
| `subject_type` / `subject_id` | legacy/domain subject，如 `compile_task` + task ID |
| `idempotency_key` | 永久 unique command identity |
| `deduplication_key` | active-window dedup key，可空 |
| `payload_json` | immutable command payload；不得含 Secret |
| `status` | Job state |
| `priority` | 整数；默认 0 |
| `available_at` | 延迟/重试可领取时间 |
| `attempt_count` / `max_attempts` | 已创建次数与预算 |
| `last_error_code` / `last_error_message` | 当前失败摘要，历史仍在 Attempt |
| `created_at` / `updated_at` / `completed_at` / `cancelled_at` | UTC timestamps |

索引与约束：

- unique `idempotency_key`。
- partial unique `(kind, organization_id, capability_space_id, deduplication_key)` where deduplication key non-null and status in pending/running。
- claim index `(status, available_at, priority, created_at)`。
- non-unique lookup index `(kind, subject_type, subject_id)`；同一 subject 可以有多个 terminal Jobs，不能把该索引误作业务 dedup。

### 5.2 `job_attempts`

| 字段 | 语义 |
| --- | --- |
| `id` | String(64) PK |
| `job_id` | FK jobs ON DELETE CASCADE |
| `attempt_number` | 每 Job 从 1 单调增加 |
| `status` | Attempt state |
| `worker_id` | `hostname:pid:instance-uuid`，不含凭证 |
| `lease_token` | 不可复用随机 token |
| `leased_at` / `lease_expires_at` / `heartbeat_at` | lease evidence |
| `started_at` / `finished_at` | 执行时间 |
| `error_code` / `error_message` | 本 Attempt 失败证据 |
| `result_json` | 小型脱敏结果摘要，不放大 Artifact |
| `created_at` | UTC timestamp |

约束：

- unique `(job_id, attempt_number)`。
- partial unique `job_id` where Attempt status in leased/running。
- lease expiry index `(status, lease_expires_at)`。

大型日志、测试报告和产物不是 result JSON，后续进入 Artifact store。

### 5.3 F04 scope 接入

Repository 不直接查询 F04 内部 tables 来猜 scope。Compile Adapter 通过 F04 public Workspace Adapter 获取 Organization/Project Space，再把稳定 IDs 写入 Job。

F04 binding 缺失或 topology invalid 时，enqueue fail closed；禁止创建 organization/space 为空的“本地特殊 Job”。这使 Local 与未来 Team 使用同一 Job schema。

## 6. Alembic revision 与 backfill（阶段 B）

预期 revision：

```text
文件：20260716_f05_0003_durable_jobs.py
revision：f05_0003
down_revision：f04_0002
```

Expand：

1. 创建 `jobs` 与 `job_attempts`、FK、unique、partial indexes。
2. 更新 model registry 与 revision-aware PostgreSQL schema contract。
3. 不给 CompileTask/CompileStep 新增 job columns；通过 Job `subject_type/subject_id` 兼容绑定。

Backfill 只处理 active legacy CompileTask：

| legacy 状态 | F05 动作 |
| --- | --- |
| PENDING | 创建 pending Job，attempt_count=0，不创建虚假 Attempt |
| RUNNING | 创建 pending Job；创建一个 `abandoned` legacy Attempt，原因 `LEGACY_WORKER_INTERRUPTED`；把 task 与 RUNNING steps 恢复为 PENDING |
| COMPLETED / FAILED | 不创建 Job，不伪造历史 Attempt；GET/queue 继续由 legacy read model 返回 |

每个 backfill Job 通过 Workspace Adapter 对应的持久化 binding 得到 Organization/Project Space。任何 active task 缺少 Workspace/Space binding 时 migration 失败并回滚，不创建 unscoped Job。

Backfill 前后必须证明：

- terminal CompileTask/Step rows 和全部其他旧业务表 fingerprint 不变。
- PENDING rows 除新增 Job 外不变。
- RUNNING rows只发生计划中明确的恢复转换，并在 manifest 逐项记录 before/after 与 abandoned Attempt。
- 重复 upgrade 是 no-op。

## 7. Repository 与 Worker 架构（阶段 B）

```text
infrastructure/jobs/
  domain.py           pure state/value objects
  policies.py         lease/retry/idempotency decisions
  contracts.py        JobHandler/Clock/Repository protocols
  models.py           Job/JobAttempt ORM
  repository.py       enqueue/claim/heartbeat/finish/recover
  registry.py         explicit kind -> handler mapping
  worker.py           polling + graceful stop + heartbeat
  adapters/
    __init__.py
    compile.py         legacy CompileTask/Step handler and status mapping
```

### 7.1 Atomic claim

PostgreSQL：

```text
BEGIN
-> select eligible pending Job
   order by priority desc, available_at asc, created_at asc
   FOR UPDATE SKIP LOCKED
-> verify no active Attempt
-> increment attempt_count
-> create leased Attempt + token + expiry
-> Job pending -> running
COMMIT
```

SQLite 只认证 Local 单 Worker，使用短事务和 compare-and-set；不把 SQLite 测试作为多 Worker 并发证明。

### 7.2 Heartbeat

Worker 执行 handler 时由独立控制 session 周期 heartbeat。业务 handler transaction 不承担 heartbeat commit，避免长事务让 lease 看起来永久失联。

heartbeat 连续失败或条件更新为 0 时，Worker 标记本地 lease lost。handler 可以协作停止；即使无法立即停止，最终 completion fencing 必须回滚其数据库副作用。

### 7.3 Graceful stop 与 crash

- `stop()` 先停止 claim 新 Job。
- active handler 在 grace window 内继续 heartbeat 并尝试完成。
- 超过 grace window不把 Job伪造为 FAILED；进程退出后由 lease expiry recovery 接管。
- `start()` 不再扫描并塞入内存 Queue；Worker 持续 poll durable Jobs。
- 两个进程同时启动时依靠数据库 claim，不依靠 Python singleton。

### 7.4 Handler registry

registry 显式登记 `compile_source`。未知 kind fail `JOB_HANDLER_NOT_REGISTERED`。禁止通过动态 import payload、eval、文件路径或任意类名执行 handler。

F05 不接入 Eval、Knowledge Compiler、Coding 或 Harness handler；它们只在各自后续计划复用公开 Job contract。

## 8. Compile Worker Adapter（阶段 B）

### 8.1 保留外部契约

以下路径、函数名、operation ID、status code 和 response body 保持：

| 方法与路径 | 必须保留的 operation ID | status |
| --- | --- | --- |
| `POST /api/raw/{source_id}/compile` | `raw_compile_api_raw__source_id__compile_post` | 202/404/409 |
| `GET /api/compile/queue` | `compile_queue_api_compile_queue_get` | 200 |
| `GET /api/compile/{task_id}` | `compile_task_status_api_compile__task_id__get` | 200/404 |
| `POST /api/compile/{task_id}/retry` | `compile_retry_api_compile__task_id__retry_post` | 202/404/409 |

`CompileTask`、`CompileStep` 与现有 response converters 继续承担兼容 read model。F05 不新增 Job API 或 Operations UI；H06 再提供通用查询与操作界面。

### 8.2 Enqueue transaction

新 Compile：

```text
resolve Source + WorkspaceSpaceContext
-> calculate compile content/dedup key
-> transactionally create CompileTask + five CompileSteps + Job
-> COMMIT
-> durable Worker poll 后才能 claim
```

不再在 commit 前调用内存 `queue.put()`。并发 active dedup unique conflict 时，loser transaction rollback 并读取 winner Job 的 subject CompileTask 返回；不得留下 orphan CompileTask/Steps。

### 8.3 Handler transaction

Compile handler：

1. 根据 subject ID 加载 CompileTask，验证 scope 和当前状态。
2. legacy task 已 COMPLETED/FAILED 时只做 reconcile，不重复执行。
3. 执行现有五个 CompileStep；F05 不重写其业务内容。
4. PATCH 创建 ReviewItem 后，在同一 transaction 内执行 lease fencing completion。
5. fencing 成功才提交 ReviewItem、CompileTask/Steps、Job/Attempt。
6. fencing 失败则整体 rollback，stale Worker 不能留下第二个 Review。

Compile 当前对 pending Review 使用 content hash dedup，继续作为业务防线；数据库 lease fencing 承担 stale Worker 的事务提交防线。两者不能互相替代。

### 8.4 Manual retry

现有 retry endpoint 仍只接受 FAILED CompileTask：

- reset legacy steps 以维持当前 UI/API。
- 将对应 failed Job显式转回 pending。
- 显式增加一个 Attempt 名额；manual retry 不受已耗尽的自动预算静默阻塞。
- 新 claim 创建下一 Attempt。
- 旧 Attempt error/timestamps 保留。
- historical FAILED task 没有 Job 时，Adapter 首次创建 Job 后 pending。
- 若相同 active dedup key 已被更新的 Compile Job 占用，返回稳定 409 conflict，不允许两个 Job 同时进入 pending/running。

## 9. 发布开关与回滚边界

F05 runtime 暂时支持：

```text
INKDESK_JOB_BACKEND=durable   # 默认与验收路径
INKDESK_JOB_BACKEND=legacy    # 仅紧急 Switch 回退
```

`legacy` 保留当前单进程内存 Compile Worker，只用于 F05 观察期回退；不支持多 Worker，也不能作为 F05 完成证据。该开关必须同步 `.env*.example` 和运维文档，并在 H02 前重新评估删除。

### 9.1 Expand 前/未执行 Attempt

如果只完成 schema/backfill、尚无 Attempt 执行，可由 scoped `rollback-f05` 检查：

- current revision 为 `f05_0003`。
- job_attempts 为空或仅有 migration 标记的 legacy abandoned rows。
- 没有 F05 runtime 创建的业务 Job/history。
- legacy fingerprints 可恢复。

满足时允许 downgrade 到 `f04_0002`；否则返回 `DB_MIGRATION_ROLLBACK_UNSAFE`。

### 9.2 Durable Switch 回退

已执行真实 Attempt 后，Job/Attempt 是不可伪造的运行历史，禁止 drop tables。正常回退：

1. 停止 durable Worker claim。
2. 等待 active handler grace completion；未完成者让 lease expire。
3. 将可恢复 CompileTask reconcile 为 PENDING。
4. 设置 `INKDESK_JOB_BACKEND=legacy`，保留 F05 schema、history 和 migration runtime。
5. 验证旧 Compile API 与单进程处理。

重新切回 durable 时，Adapter 先 reconcile legacy Worker 已完成的 CompileTask；terminal task 对应 Job只同步 terminal 状态，不重新执行 handler。

### 9.3 完整旧 binary 回退

F03/F04 旧 binary 不认识 F05 head。存在真实 Attempt 后如必须完整回退，只能停止写入并恢复 F05 前最新 PostgreSQL + Vault 成对备份；不能为了启动旧 binary 删除 Job history。恢复会丢失备份后的业务写入，因此必须作为最后手段并明确影响窗口。

## 10. 文件边界

### 10.1 阶段 A 文件

| 操作 | 文件 | 职责 |
| --- | --- | --- |
| 新增 | `server/inkdesk_server/infrastructure/__init__.py` | infrastructure package |
| 新增 | `server/inkdesk_server/infrastructure/jobs/__init__.py` | 只导出稳定领域契约，无副作用 |
| 新增 | `server/inkdesk_server/infrastructure/jobs/domain.py` | Job/Attempt 状态和值对象 |
| 新增 | `server/inkdesk_server/infrastructure/jobs/policies.py` | lease/retry/idempotency 纯决策 |
| 新增 | `server/inkdesk_server/infrastructure/jobs/contracts.py` | Clock、Handler、Repository protocols |
| 新增 | `server/tests/jobs/test_job_state_machine.py` | Job 合法/非法转换 |
| 新增 | `server/tests/jobs/test_attempt_state_machine.py` | Attempt 与历史不可变 |
| 新增 | `server/tests/jobs/test_lease_policy.py` | expiry、heartbeat、stale token/fence |
| 新增 | `server/tests/jobs/test_retry_policy.py` | 自动/人工重试与预算 |
| 新增 | `server/tests/jobs/test_idempotency_contract.py` | same key/same command 与 conflict |

### 10.2 阶段 B/C 文件

| 操作 | 文件 | 职责 |
| --- | --- | --- |
| 新增 | `server/inkdesk_server/infrastructure/jobs/models.py` | Job/Attempt ORM |
| 新增 | `server/inkdesk_server/infrastructure/jobs/repository.py` | durable enqueue/claim/heartbeat/finish/recover |
| 新增 | `server/inkdesk_server/infrastructure/jobs/registry.py` | explicit handler registry |
| 新增 | `server/inkdesk_server/infrastructure/jobs/worker.py` | poller、heartbeat、graceful stop |
| 新增 | `server/inkdesk_server/infrastructure/jobs/adapters/__init__.py` | Adapter package |
| 新增 | `server/inkdesk_server/infrastructure/jobs/adapters/compile.py` | CompileTask/Step compatibility Adapter |
| 新增 | `server/alembic/versions/20260716_f05_0003_durable_jobs.py` | jobs/attempts schema 与 active Compile backfill |
| 修改 | F04 `model_registry.py` | 注册 Job ORM |
| 修改 | `server/inkdesk_server/db_migrations.py` | F05 head/schema/guarded rollback |
| 修改 | `server/inkdesk_server/schema_contract.py` | `f05_0003` PostgreSQL contract |
| 修改 | `server/inkdesk_server/core/config.py` | backend/poll/lease/heartbeat/grace/default attempts |
| 修改 | `server/inkdesk_server/compile_worker.py` | 保留 facade/legacy fallback，默认委托 durable Worker |
| 修改 | `server/inkdesk_server/research.py` | transactionally create CompileTask/Steps/Job |
| 修改 | `server/inkdesk_server/main.py` | retry 委托 Adapter；保留生命周期时机与 API 形状 |
| 修改 | 所有 `.env*.example` | 同步 F05 settings |
| 新增 | `server/tests/jobs/test_job_repository.py` | enqueue、dedup、claim、finish |
| 新增 | `server/tests/jobs/test_job_concurrency_postgres.py` | SKIP LOCKED、双 Worker、active attempt unique |
| 新增 | `server/tests/jobs/test_worker_recovery.py` | crash、expiry、reclaim、stale finish |
| 新增 | `server/tests/jobs/test_compile_job_adapter.py` | legacy status/API/side-effect transaction |
| 新增 | `server/tests/migrations/test_f05_job_migration.py` | fresh、backfill、model drift、rollback guard |
| 修改 | `server/tests/test_compile_pipeline.py` | 强化 active dedup、Attempt history、retry/restart |
| 新增 | `scripts/f05/verify-durable-jobs.ps1` | 临时库、双进程、强杀、恢复、回滚编排 |
| 新增 | `scripts/f05/build-job-report.py` | 脱敏 manifest/attempt timeline |
| 新增 | `docs/delivery/jobs/f05/README.md` | evidence、运行与恢复边界 |
| 修改 | `docs/ops/环境变量.md` | F05 settings 与 fallback |
| 修改 | `docs/ops/部署指南.md` | expand/switch/reconcile/rollback |
| 修改 | `scripts/脚本说明.md` | verifier 和 rollback-f05 |
| 修改 | `docs/architecture/数据库结构.md` | Job/Attempt tables 与 Compile read model |
| 修改 | `cognitive-map.md` | 已理解 durable kernel 与外部 exactly-once 黑盒 |

不修改任何 `web/**`、Compile response schemas、F01 OpenAPI snapshot、Run/Coding/Evaluation 状态机、Vault 目录结构、Space schema 或 F04 topology rules。

## 11. 分段实施计划

### 阶段 A：纯 Job / Attempt 领域内核（现在并行）

#### 任务 A1：Job 与 Attempt 状态机

**Red**

1. 为第 4.1/4.2 节每条合法转换写 table-driven tests。
2. terminal Job/Attempt 继续转换必须返回稳定 illegal-transition reason。
3. `failed -> pending` 只有 explicit retry command 才允许。
4. retry 决策必须返回 `next_attempt_number`，不能 mutate 旧 Attempt。
5. 确认因 domain types 尚不存在而失败。

```powershell
cd server
python -m pytest tests/jobs/test_job_state_machine.py tests/jobs/test_attempt_state_machine.py -q
```

**Green**

实现 frozen dataclass/StrEnum/value results；不导入 SQLAlchemy、FastAPI、Settings 或 Compile models。

#### 任务 A2：Lease / retry / idempotency policy

**Red**

1. heartbeat 在 token 匹配且未终态时延长 lease。
2. expired lease 产生 abandoned decision；预算内/外分别 pending/failed。
3. stale token、旧 attempt number、terminal attempt heartbeat 全部拒绝。
4. same idempotency key + canonical command hash 返回 existing；不同 hash conflict。
5. handler business error 默认不自动 retry；lease loss 可 retry。
6. 所有时间测试使用 FakeClock，不 sleep。

```powershell
cd server
python -m pytest tests/jobs -q
```

**Green**

实现 pure policies 与 protocols。canonical command hash 只覆盖 kind、scope IDs 与规范化 payload，不包含创建时间、worker ID 或随机 token。

#### 阶段 A 完成门禁

- `tests/jobs` 全部无数据库通过。
- `rg` 确认新增 production files 不 import SQLAlchemy/FastAPI/Compile/F04 modules。
- 没有修改阶段 A 白名单外文件。
- 状态机、原因码、重试预算、Clock 与 idempotency hash 经 Codex 审阅。
- 提交独立 commit；在 F04 合并前保持 `integration_wait`，不开始阶段 B。

### 阶段 B：持久化 Kernel 与 Compile Adapter（F04 合并后）

#### 任务 B0：rebase 与基线门禁

```powershell
git status --short
git fetch origin
git rebase origin/main

cd server
python -m pytest tests/spaces tests/migrations -q
python -m pytest tests/jobs -q
```

确认 F04 head 和公开 Adapter 后再写 migration。

#### 任务 B1：Job/Attempt schema 与 migration

**Red**

1. fresh F05 head 有完整约束/index，model drift 为空。
2. F04 current 被识别为 MANAGED_BEHIND，drift F04 schema 在 upgrade 前失败。
3. active Compile backfill 遵循第 6 节；terminal rows fingerprint 不变。
4. F04 Space binding 缺失时 migration 全部 rollback。
5. 重复 upgrade no-op；平行 head/unknown revision fail closed。

**Green**

创建 models/revision，更新 registry、schema contract 和 migration authority。禁止 revision import ORM/Adapter。

#### 任务 B2：Repository 并发语义

**Red**

1. 同 idempotency key + 同 command 返回一个 Job；不同 command conflict。
2. 并发 active dedup 只留下一个 Job/subject CompileTask。
3. 两个 PostgreSQL claimers 对一个 Job 只创建一个 active Attempt。
4. 不同 Jobs 可由两个 Workers 并行 claim。
5. heartbeat/token/finish 条件更新与 lease expiry recovery 通过。
6. stale finish 的 handler transaction rollback。

**Green**

实现短事务 Repository；PostgreSQL 使用 `FOR UPDATE SKIP LOCKED`，SQLite 只实现单 Worker compare-and-set。

#### 任务 B3：Durable Worker

**Red**

1. start/stop 幂等，stop 后不再 claim。
2. handler 执行期间 heartbeat 持续，第二 Worker 不接管。
3. heartbeat failure 后当前 Worker 不能完成。
4. handler exception 形成 failed Attempt/Job，不只写日志。
5. unregistered kind 稳定失败且 payload 不出现在日志。

**Green**

实现 registry、poller、control session heartbeat 和 grace shutdown。不要使用内存 Queue 作为 truth。

#### 任务 B4：Compile Adapter Switch

**Red**

1. API paths/status/body/operation ID 与 F01 相等。
2. enqueue commit 前 Worker 不能看见 Job；commit 后可 claim。
3. concurrent compile 只创建一组 active CompileTask/Steps/Job。
4. success 同事务提交 Review、legacy state 与 Job/Attempt。
5. stale Worker 完成 rollback，不产生第二个 Review。
6. manual retry 创建新 Attempt并保留旧错误。
7. legacy terminal task 查询不要求虚构 Job。
8. durable/legacy backend switch 都能处理现有 CompileTask，但只有 durable 路径满足 F05 gate。

**Green**

保留 `compile_worker.py` facade 与 F03 start/stop 时机，内部默认委托 DurableWorker；enqueue/retry 通过 Adapter，不直接 queue.put。

### 阶段 C：进程故障、恢复与交付验收

#### 任务 C1：隔离 verifier

用户执行：

```powershell
pwsh -File scripts/f05/verify-durable-jobs.ps1
```

verifier 必须使用临时 PostgreSQL/隔离 Vault：

```text
fresh upgrade to f05
-> F04 scoped Compile enqueue
-> 双 Worker 并发 claim
-> heartbeat 阻止误接管
-> 强杀持 lease 的 Worker 进程
-> 等待 lease expiry
-> 第二 Worker 创建新 Attempt并完成
-> 验证旧 Attempt abandoned、stale token rejected
-> 验证恰好一个 pending Review / terminal Compile result
-> handler business failure + manual retry
-> duplicate command/idempotency conflict
-> graceful shutdown
-> legacy backend Switch 回退与 durable reconcile
-> pre-attempt rollback-f05 / post-attempt unsafe guard
-> cleanup + 脱敏 manifest
```

测试必须强杀独立 Worker 进程，不能只在单元测试中调用 `stop()` 代替 crash。

#### 任务 C2：全量回归

```powershell
cd server
python -m pytest tests/jobs tests/migrations/test_f05_job_migration.py tests/test_compile_pipeline.py -q
python -m pytest

# PostgreSQL 并发与 pgvector
python -m pytest tests/jobs/test_job_concurrency_postgres.py tests/migrations tests/test_pgvector_integration.py -q

cd ..
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml up -d --build

python scripts/f01/export_openapi.py compare `
  --url http://localhost:8080 `
  --snapshot docs/delivery/baselines/f01/contracts/openapi.json

cd web
npm run e2e:fullstack
```

F05 无前端变更，不要求新增视觉截图；full-stack 必须覆盖 Raw -> Compile -> Review 查询/接受与 Dev Run 既有流程。

## 12. F05 完成门禁

只有以下条件全部成立，F05 才能标记完成并解锁 E03/K05/H02：

1. 阶段 A 在 F04 合并前只修改白名单文件，纯领域测试通过并独立提交。
2. 阶段 B 基于已合并 F04 rebase；Alembic 单 head 为 `f05_0003`，down revision 为真实 F04 head。
3. Job/Attempt 状态机、原因码、retry policy 与 idempotency contract 无数据库也可验证。
4. PostgreSQL jobs/attempts schema、partial unique indexes、scope FKs 与 ORM metadata 完全一致。
5. F04 current -> F05 upgrade、fresh upgrade、active Compile backfill、重复 upgrade 与 drift guard 通过。
6. enqueue、claim、Attempt 创建、heartbeat、finish 与 recovery 使用短事务和条件更新。
7. 两个 PostgreSQL Workers 不能同时 claim 同一 Job；可并行 claim 不同 Jobs。
8. lease 未过期时不会误接管；进程强杀后新 Worker 能接管并保留 abandoned Attempt。
9. stale Worker 不能提交 completion 或 Compile Review 副作用。
10. automatic/manual retry 都创建新 Attempt，旧失败历史不覆盖。
11. active Compile 并发入队只产生一个 task/job；terminal 后的显式新 Compile 保留当前行为。
12. Compile API、OpenAPI、legacy task/step response 与 F03 生命周期兼容。
13. durable backend 是默认和验收路径；legacy backend 只作为有文档、有测试的紧急 Switch 回退。
14. pre-attempt rollback 可恢复 F04；存在真实 Attempt 时 destructive downgrade 被拒绝。
15. focused、后端全量、PostgreSQL concurrency/integration、Docker、OpenAPI 和 full-stack 全部通过。
16. F05 verifier manifest 包含 worker IDs、attempt timeline、lease/fence 结果、唯一副作用证明和 cleanup，且不泄露 payload/Secret/连接地址。
17. 运维、环境变量、数据库、脚本和 cognitive map 文档已更新，证据可追溯到 commit SHA。

任一双 active Attempt、stale Worker 可提交、失败 Attempt 被覆盖、内存 Queue 仍是调度 truth、F05 创建平行 Alembic head、Job 没有 Organization/Space、handler payload/Secret 进入日志，或用更新 F01 snapshot 接受无关 API 变化，都属于阻塞失败。

## 13. 明确范围外

- 不实现 Exactly-once 营销承诺；不为任意外部系统自动生成幂等能力。
- 不实现通用 Outbox、Saga 或 compensation engine；H05 再扩展。
- 不新增 Job/Attempt HTTP API、Operations Console 或前端页面；H06 再提供。
- 不迁移 Dev Run、Coding Session、EvalRun 或 Knowledge Compiler 到 Job kernel。
- 不实现 Harness Checkpoint、Workflow Definition 或 step-level 通用恢复；H01/H02 负责。
- 不改变 Compile 五步业务算法、Review schema、Vault 写入规则或 acceptance workflow。
- 不删除 CompileTask/CompileStep；它们继续是兼容 workflow read model。
- 不修改 F04 Space schema、topology、membership 或 Workspace binding。
- 不实现 distributed scheduler leader election；数据库 SKIP LOCKED 是当前协调机制。
- 不认证 SQLite 多 Worker；Team 并发证明只来自 PostgreSQL。
- 不引入 Redis、RabbitMQ、Celery、Temporal 或新的外部基础设施；当前单体规模使用 PostgreSQL durable kernel。
- 不把大日志、Artifact、测试报告或 Secret 存入 payload/result JSON。
- 不提前开始 W01、E03、K05 或 H02。

## 14. 主要风险与审阅重点

| 风险 | 隐蔽原因 | 必须怎样发现 |
| --- | --- | --- |
| enqueue before commit race | 当前 queue.put 发生在 commit 前 | Worker 不可见未提交 Job 的集成测试 |
| 双 Worker 重复执行 | Python singleton 只在单进程有效 | PostgreSQL 双进程 SKIP LOCKED + active unique |
| heartbeat 与业务长事务互相阻塞 | 使用同一 Session 无法及时提交 heartbeat | 独立 control session 与真实长 handler 测试 |
| stale Worker 提交副作用 | 只检查开始时 lease，不检查提交时 fence | lease 被替换后 completion rowcount=0，整个事务 rollback |
| retry 覆盖历史 | legacy endpoint reset 原 task/steps | Attempt rows 数量/错误/timestamps 不变断言 |
| 幂等与 dedup 混淆 | 永久 unique 会阻止用户未来显式重跑 | 永久 idempotency key + active partial dedup 双契约 |
| migration 虚构历史 | 给 terminal legacy task 生成假成功 Attempt | terminal 不 backfill，只兼容读取 |
| RUNNING legacy task 永久卡死 | 无 lease 无法判断 owner | 明确转 pending + legacy abandoned Attempt + manifest |
| F04/F05 平行 Alembic head | 两分支都从 f02 创建 revision | F05 阶段 B 强制 rebase，down_revision 验证 |
| fallback 与 durable 同时运行 | 发布开关或生命周期接线错误 | backend mutually exclusive 测试、两个 worker type 不可同时 start |
| Job payload 泄密 | 通用 JSON 容易塞入上下文/凭证 | schema sanitizer、日志捕获与 forbidden-value tests |
| 误把 SQLite 当并发证明 | 本地测试看似通过 | PostgreSQL 专项 suite 是完成门禁 |

## 15. 学习与审阅检查点

用户完成阶段后，应能解释：

1. at-least-once、idempotency、deduplication、lease 和 fencing 分别解决什么问题。
2. 为什么 heartbeat 必须使用独立短事务，为什么只有 heartbeat 仍不够。
3. 为什么 stale Worker 的最终提交必须用 token/attempt number 条件更新。
4. 为什么 retry 创建新 Attempt，而不是把失败记录重置。
5. 为什么 CompileTask/Step 暂时保留，Job/Attempt 不能替代其业务 read model。
6. 为什么 F05 阶段 A 能与 F04 并行，而阶段 B 在技术上必须等待 F04。
7. 为什么 active partial dedup 与永久 idempotency key 必须分开。
8. 为什么已经产生真实 Attempt 后不能安全 destructive downgrade。
9. 哪些副作用能在同一数据库事务内保护，哪些未来必须使用 Outbox/compensation。

Codex 审阅优先级：并发唯一性与 stale fencing > crash recovery > migration chain/scope > Attempt 历史 > Compile 兼容 > 配置与代码风格。

## 16. 计划自审结论

- **单一能力**：只建立 Durable Job/Attempt Kernel 并迁移 Compile 调度，不夹带 Eval、Harness、UI 或通用 Outbox。
- **并行安全**：阶段 A 有严格白名单且不依赖 F04；阶段 B 明确 rebase gate，不创建 Alembic 多 head。
- **语义诚实**：采用 at-least-once + idempotency + fencing，不声称通用 exactly-once。
- **恢复完整**：覆盖双 Worker、heartbeat、强杀、lease expiry、stale completion、manual retry 和 graceful stop。
- **数据安全**：terminal legacy history 不伪造；RUNNING recovery 显式留 abandoned evidence；真实 Attempts 禁止 destructive downgrade。
- **兼容性**：Compile API、Task/Step read model、OpenAPI 与 F03 lifecycle 保持，durable Worker 替换的只是调度权威。
- **团队扩展性**：Job 从第一天归属 Organization/Project Space，未来 Eval/Knowledge/Harness 复用同一协议。
- **可实施性**：状态、原因码、表、索引、claim algorithm、文件、Red-Green 步骤、命令和门禁均已确定。
