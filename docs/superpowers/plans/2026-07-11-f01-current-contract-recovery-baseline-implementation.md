# F01 当前行为契约与恢复基线实施计划

> 日期：2026-07-11
> 状态：已确认，待实施
> 路线图：[`2026-07-11-inkdesk-capability-platform-master-roadmap.md`](./2026-07-11-inkdesk-capability-platform-master-roadmap.md)
> 上位设计：[`2026-07-11-inkdesk-team-rd-capability-platform-design.md`](../specs/2026-07-11-inkdesk-team-rd-capability-platform-design.md)
> 前置依赖：无
> 后续解锁：F02 Python 数据库迁移权威、F03 模块化应用组合壳

## 1. 单一交付目标

F01 只交付一项能力：在任何结构迁移开始前，Inkdesk 能够重复捕获当前可保留行为，备份 PostgreSQL 与 Vault，在隔离目标中恢复，并生成可审计、可比较、不会泄露本地数据的证据。

F01 不是“让当前所有实现永远不变”，也不是普通的全量测试补齐。它建立两层互相独立的基线：

1. **行为契约基线**：回答 API、浏览器流程、OpenAPI、PostgreSQL schema 和代表性数据形状是否发生了未经确认的变化。
2. **真实恢复基线**：回答当前 PostgreSQL 数据与 Vault 文件是否真的能够备份、恢复、校验和再次读取。

SQLite 测试只能证明大部分应用行为，不得作为 PostgreSQL schema、pgvector 或恢复能力的替代证据。

## 2. 已敲定的实现决策

### 2.1 默认运行形态

- 以 `infra/docker-compose.local-docker.yml` 作为 F01 默认本地全栈拓扑。
- `pg_dump`、`pg_restore`、`psql` 和数据库创建/销毁默认在 `local-postgres` 容器内执行，避免依赖宿主机 PostgreSQL 客户端。
- Python、Node、npm、Docker、Compose 和 PostgreSQL 的实际版本写入本地运行证据，不写死在契约中。
- 端口、容器 ID、数据库名和 Vault 来源从 compose 配置与运行状态解析，不写死 `5432`、`8080` 或容器名称。
- 允许显式的 host 模式覆盖，用于非 Docker 部署；host 模式必须提供源数据库 URL、Vault 路径和恢复目标，不能猜测。

### 2.2 两类产物

提交到仓库的脱敏基线：

```text
docs/delivery/baselines/f01/
  README.md
  contract-policy.md
  manifest.schema.json
  known-issues.json
  contracts/
    openapi.json
    behavior-contracts.json
    postgres-schema.json
    representative-records.json
    browser-flows.json
```

只保存在本机的真实证据：

```text
.local/f01-baseline/<run-id>/
  manifest.json
  environment.json
  checksums.sha256
  contracts/
  tests/
  backup/
    postgres.dump
    vault.zip
  fingerprints/
    source.json
    restored.json
  restore/
    report.json
```

仓库根 `.gitignore` 必须加入 `.local/`。不能依赖某个开发者机器上的 `.git/info/exclude` 防止 dump、日志、路径或真实数据被误提交。

### 2.3 默认恢复安全策略

- 默认绝不覆盖活动数据库或活动 Vault。
- 恢复数据库名必须由脚本生成，前缀固定为 `inkdesk_f01_restore_`；脚本拒绝源数据库名、`postgres`、`template0`、`template1` 和不符合前缀的目标。
- Vault 只恢复到本次运行目录下的新目录，拒绝仓库 Vault、compose 活动卷和任意已存在的非空目录。
- ZIP 条目出现绝对路径、`..`、符号链接、reparse point 或目标逃逸时立即失败。
- 校验结束后默认销毁隔离数据库和恢复目录；只有显式 `-KeepRestoreTarget` 才保留，且报告中必须标记。
- 任何失败都不能触发对源数据库、源 Vault 或现有 volume 的清理。

### 2.4 一致性窗口

数据库与 Vault 没有跨存储事务，F01 使用短暂静默窗口获得成对备份：

1. 记录服务原始运行状态并完成健康预检。
2. 停止 `local-web` 与 `local-server`，等待 Compile Worker 退出；PostgreSQL 保持运行。
3. 在没有应用写入的窗口内生成数据库 dump、数据库指纹、Vault 文件清单、Vault ZIP 和校验和。
4. `-Mode all` 在同一静默窗口内完成隔离恢复、源目标复核和临时目标清理；不能在备份与恢复之间重启源应用。
5. 在最外层 `finally` 中恢复先前处于运行状态的服务。单独运行 backup 模式时也必须在自己的 `finally` 中恢复服务。

脚本必须在 manifest 中记录静默开始、结束、服务恢复结果和中断原因。无法建立静默窗口时，本次恢复证据直接失败，不能降级为“尽力备份”。

## 3. 契约边界

### 3.1 必须保留的语义

API 形状以生成的 OpenAPI 全量清单为机器权威，OpenAPI 无法表达的状态转换与副作用由 `behavior-contracts.json` 及对应测试节点保护。重点保护以下能力族：

| 能力族 | 必须保护的语义 |
| --- | --- |
| Health / Vault | `/health`、`/actuator/health`、Vault 状态与初始化；路径安全和初始化幂等 |
| Knowledge | `raw -> ingest -> wiki -> ask -> writeback/deposit`；Canonical 写入必须经过 Review |
| Dev Run | 创建、列表、详情、事件、推进、取消、六阶段动作、非法转换 `409`、不存在资源 `404` |
| Deposit | Ask/Run 沉淀的显式性、Review 结果和幂等行为 |
| Skills / Health / Eval | 当前只读契约、健康运行和 Evaluation manifest 入口 |
| Compile | 创建、队列、详情、重试的状态码与错误语义 |
| MCP | `context_pack`、`search`、`deposit`、`health_check` 的工具名、输入输出和错误边界 |

每个 HTTP operation 保护 URL、method、请求必填字段、响应字段、状态码、错误 `code/message` 形状和内容类型。列表默认顺序、随机 ID、时间戳、内部 operation ID 等只有在现有产品语义明确依赖时才进入断言。

浏览器基线保护以下用户可观察流程：

1. 无登录进入 `/app`，Operations/Dev Run 首页可读取。
2. 创建 Dev Run 后，延迟返回的旧列表不能覆盖新建结果。
3. Run 详情显示六阶段轨道，合法推进可完成，非法推进明确失败。
4. Raw、Ingest、Wiki、Ask、Compile、Health、Skills 页面可通过现有入口访问并展示真实后端数据或明确空状态。
5. `source -> review -> topic -> ask -> deposit proposal` 的关键知识链可由 API 准备数据并在对应页面读取。
6. 不存在的资源展示 not-found，不被重定向到已经废弃的登录流程。

### 3.2 明确不固化的实现偶然性

以下内容可以在后续计划中重构，只要上面的外部语义和迁移证据保持成立：

- `main.py` 内部路由嵌套、`research.py` 内部函数和 `stage_actions.py` 的编排方式。
- SQLAlchemy 查询写法、运行时 DDL 数组、旧 Flyway 文件和 `create_all` 的实现方式。
- Compile Worker、MCP session manager 和 Coding session 的进程内对象布局。
- fixture fallback、seed 数据生成细节、确定性 runtime 的内部实现。
- 不影响语义的 JSON 字段顺序、内部 SQL constraint/index 名称、随机 ID、时间戳和无承诺的列表顺序。
- 已废弃的 legacy auth cookie 行为。
- 当前 `fullstack-preflight.mjs` 对 PostgreSQL `5432` 的硬编码，以及 `8000`、`8080`、`8300` 多套后端默认端口；它们登记为基线工具缺陷，不升级为产品契约。

## 4. 证据与判定模型

### 4.1 Manifest 最小字段

`manifest.schema.json` 至少约束：

```text
schemaVersion, runId, startedAt, completedAt, overallStatus
git.commit, git.branch, git.dirty
environment.os/python/node/npm/docker/compose/postgres
configuration.mode/composeFile/services/database/vaultSource
contracts[].name/path/sha256/status
tests[].suite/command/exitCode/duration/status/stdout/stderr/knownIssueIds
backup.database.path/format/sha256
backup.vault.path/fileCount/sha256
sourceFingerprint.path/sha256
restore.targetDatabase/targetVault/status/cleanupStatus/reportPath
knownIssueIds[]
```

`overallStatus` 只有三种：

- `PASS`：所有必需检查通过，无已知失败。
- `PASS_WITH_KNOWN_ISSUES`：没有未知失败，所有偏差都精确匹配尚未过期的登记项。
- `FAIL`：出现未知失败、恢复不一致、安全保护触发、服务未恢复、缺失证据或 manifest 不完整。

`known-issues.json` 中每项必须含 `id`、`kind`、`scope`、`matcher`、`evidence`、`reason`、`disposition`、`firstObservedAt`、`expiresAt` 和 `blocksNextPlan`。模糊正则、整套测试白名单和无限期豁免不允许通过校验。

### 4.2 OpenAPI 快照

- 由运行中的真实后端 `GET /openapi.json` 捕获。
- 只对 JSON object key 做稳定排序和 UTF-8/LF 格式化；不删除 path、schema、status、required、enum 或错误定义。
- 契约测试在临时 SQLite/Vault、deterministic runtime、关闭 seed 和 no-op Compile Worker 下构造 app，再与提交快照比较。
- `create_app()` 当前会初始化数据库、seed、Compile Worker 和 MCP；F01 只在测试夹具中隔离这些副作用，不把副作用写进契约，也不在本计划重构 app factory。

### 4.3 PostgreSQL schema 快照

必须从真实 PostgreSQL catalog 导出，而不是从 SQLAlchemy metadata 推测。快照包含：

- PostgreSQL 与 pgvector extension 的存在性，不固化 patch 版本。
- public schema 下应用表、列、数据库类型、nullable、default。
- primary key、unique、foreign key 及 `ON DELETE` 语义。
- index 的列/表达式、唯一性和 pgvector 索引方法；物理名称只作诊断，不进入兼容 digest。
- 兼容 digest 与完整诊断 digest，便于 F02 区分语义变化和命名变化。

### 4.4 代表性数据快照

提交快照只使用在隔离数据库中通过现有公共 API 创建的合成数据，并把 ID、时间、绝对路径和自由文本归一化为稳定占位符。至少覆盖：

```text
Source -> ReviewItem -> Topic -> Claim
AskTurn -> Writeback/Deposit Proposal
DevRun -> RunEvent -> completed state
CompileTask -> CompileStep
Workspace/User references
```

真实本地数据不提交。恢复证据对源库每张业务表记录 row count 和按主键排序、逐行 canonical JSON 计算的 SHA-256；Vault 对每个普通文件记录相对路径、字节数和 SHA-256。恢复后必须逐项相等。

## 5. 文件边界

| 操作 | 文件 | 职责 |
| --- | --- | --- |
| 新增 | `scripts/f01/baseline_contracts.py` | JSON canonicalization、hash、manifest、数据库与 Vault 指纹的纯函数 |
| 新增 | `scripts/f01/export_openapi.py` | 从真实 `/openapi.json` 导出和比较 OpenAPI |
| 新增 | `scripts/f01/export_postgres_schema.py` | 读取 PostgreSQL catalog 并生成 schema/digest |
| 新增 | `scripts/f01/verify_baseline.py` | 校验 manifest、known issue、checksums、DB/Vault 指纹和恢复读路径 |
| 新增 | `scripts/f01/capture-baseline.ps1` | `contracts/tests/recovery/all` 总编排与失败传播 |
| 新增 | `scripts/f01/backup-local.ps1` | 建立静默窗口并生成 PostgreSQL/Vault 成对备份 |
| 新增 | `scripts/f01/restore-drill.ps1` | 隔离目标创建、恢复、校验和清理 |
| 新增 | `scripts/f01/README.md` | 参数、Docker/host 模式、故障处理和证据位置 |
| 新增 | `server/tests/baseline/test_contract_exporters.py` | OpenAPI/schema/data canonicalization 回归测试 |
| 新增 | `server/tests/baseline/test_critical_behavior_contract.py` | Review-first、状态机、Deposit、Vault path 与 deterministic fallback 行为契约 |
| 新增 | `server/tests/baseline/test_manifest_validation.py` | manifest、known issue 和证据完整性测试 |
| 新增 | `server/tests/baseline/test_restore_guardrails.py` | 活动目标拒绝、路径逃逸、未知失败和清理规则测试 |
| 新增/扩展 | `web/tests/e2e/f01-critical-flows.spec.ts` | 关键浏览器流程；复用现有 full-stack helper |
| 修改 | `web/scripts/run-fullstack-e2e.mjs` | 让默认 full-stack 入口同时执行现有流程与 F01 关键流程 |
| 修改 | `web/tests/unit/fullstack-runner.test.ts` | 保护 full-stack spec 选择与命令构造 |
| 新增 | `docs/delivery/baselines/f01/**` | 脱敏契约、策略、已知问题和使用说明 |
| 修改 | `.gitignore` | 忽略 `.local/`，阻止真实证据入库 |
| 修改 | `docs/ops/备份与恢复.md` | 用可执行命令替代原则性说明 |
| 修改 | `scripts/脚本说明.md` | 登记 F01 脚本入口 |
| 修改 | `cognitive-map.md` | F01 完成后记录已确认边界、模糊区和黑盒区 |

禁止修改产品路由、schemas、ORM models、运行时 DDL、前端页面和业务行为。若基线测试暴露产品缺陷，先登记；修复必须另开 Bug 计划并遵循失败测试优先。

## 6. 分段实施计划

F01 保持一个能力结果，但按三个可独立审阅的增量实施；任一增量失败都不继续下一个。

### 增量 A：契约与快照工具

#### 任务 A1：先锁定证据格式和安全规则

**Red**

1. 新建 `test_manifest_validation.py`，提供最小合法 manifest 与以下非法样例：缺 checksum、未知状态、模糊 known issue、过期豁免、绝对路径、证据落在 `.local/` 外。
2. 新建 `test_restore_guardrails.py`，断言源数据库、活动 Vault、非空目录、危险 ZIP 条目和非法恢复数据库名被拒绝。
3. 运行：

```powershell
cd server
python -m pytest tests/baseline/test_manifest_validation.py tests/baseline/test_restore_guardrails.py -q
```

确认因 F01 模块尚不存在而失败，且失败原因不是 import 路径或测试夹具错误。

**Green**

1. 实现 `baseline_contracts.py` 和 `verify_baseline.py` 的最小纯函数。
2. 新增 `.gitignore` 的 `.local/`，测试通过 `git check-ignore` 验证。
3. 只做到上述测试通过，不接 Docker、不做备份。

#### 任务 A2：OpenAPI 契约

**Red**

1. 在 `test_contract_exporters.py` 中隔离 app factory 副作用并生成当前 OpenAPI。
2. 断言与尚不存在的 `contracts/openapi.json` 相等。
3. 增加 mutation 测试：删除一个 response status 或 required 字段时比较器必须失败。

**Green**

1. 实现 `export_openapi.py` 的 `capture/compare` 子命令。
2. 从运行中的本地后端捕获快照，检查不存在 token、cookie、主机绝对路径和实际业务数据。
3. 提交 canonical OpenAPI，并使契约测试通过。

随后新增 `behavior-contracts.json` 和 `test_critical_behavior_contract.py`，用稳定的 invariant ID 关联测试，而不是依赖实现文件名作为产品契约。至少覆盖：

- `knowledge.review_first_write`：Ask/writeback/deposit 只产生 Proposal/Review，不绕过审阅直接改 Canonical Wiki。
- `runs.illegal_transition`：非法 Run 转换返回稳定的 `409` 与原因语义。
- `runs.deposit_idempotency`：重复沉淀不产生重复副作用。
- `vault.relative_path_only`：绝对路径与目录逃逸被拒绝。
- `agent.deterministic_fallback`：未配置外部模型时仍有可重复的受限行为。
- `mcp.public_tool_contract`：四个公共 MCP 工具的名称、输入输出和错误边界保持兼容。

#### 任务 A3：PostgreSQL schema 与代表性记录

**Red**

1. 为 schema canonicalizer 写 fixture，覆盖列、FK、unique、index、pgvector extension 和乱序 catalog 结果。
2. 断言列类型或 `ON DELETE` 改变会改变兼容 digest；仅物理 constraint 名改变不影响兼容 digest。
3. 为代表性记录归一化写测试，断言 UUID、时间和绝对路径被替换，关系仍可辨认。

**Green**

1. 实现 `export_postgres_schema.py`，通过 compose 内的 PostgreSQL catalog 生成结构化 JSON。
2. 在临时数据库/Vault 中通过公共 API 创建合成关系图，生成 `representative-records.json`。
3. 提交脱敏快照；任何无法解释的 runtime DDL 与 model 差异登记到 `known-issues.json`，F01 不修复。

**增量 A 验收**

```powershell
cd server
python -m pytest tests/baseline -q
python ..\scripts\f01\export_openapi.py compare --snapshot ..\docs\delivery\baselines\f01\contracts\openapi.json
python ..\scripts\f01\export_postgres_schema.py compare --snapshot ..\docs\delivery\baselines\f01\contracts\postgres-schema.json
```

结果必须对同一输入可重复，连续运行不产生 diff。

### 增量 B：测试与关键浏览器行为基线

#### 任务 B1：命令捕获与已知失败纪律

**Red**

1. 用假的 pass/fail/skip 命令测试编排器结果聚合。
2. 断言未知失败一定得到 `FAIL`；只有精确匹配且未过期的 known issue 可得到 `PASS_WITH_KNOWN_ISSUES`。
3. 断言 stdout、stderr、exit code、耗时和命令缺一不可。

**Green**

`capture-baseline.ps1 -Mode tests` 顺序执行并保留原始退出码：

```powershell
cd server
python -m pytest

cd ..\web
npm test
npm run typecheck
npm run lint
npm run build
npm run e2e
```

PostgreSQL integration 另行使用 `INKDESK_TEST_PGVECTOR_URL` 运行，不能因普通 suite 中 skip 而省略。任何本机环境缺失必须标记 `environment_error`，不得自动登记为产品 known issue。

#### 任务 B2：关键浏览器流程

**Red**

1. `browser-flows.json` 先定义流程 ID、前置数据、步骤、断言和清理策略。
2. 新建 `f01-critical-flows.spec.ts` 读取清单；首次运行应因 full-stack runner 尚未包含该 spec 而使 runner 单元契约失败。
3. 若新增的行为断言立即通过，这是对既有行为的正常基线捕获；若失败，确认是已有缺陷并登记，不修改 UI 来“配合快照”。

**Green**

1. 复用 `local-fullstack.spec.ts` 的真实全栈设置，消除重复 helper。
2. 更新 `run-fullstack-e2e.mjs`，让默认入口显式运行现有 full-stack spec 和 F01 spec；用 `fullstack-runner.test.ts` 保护命令参数。
3. 补齐 `/app`、Run、Raw/Ingest/Wiki/Ask、Compile/Health/Skills 和 not-found 的用户可观察断言。
4. 页面可见行为若已损坏，登记独立 Bug；F01 只在当前行为确实成立时建立保护。

真实浏览器命令：

```powershell
cd web
npm run e2e:fullstack
```

验收同时记录浏览器版本、目标 URL、测试输出、控制台错误和失败请求。F01 不要求视觉截图基线，不用像素差异冻结当前 UI。

**增量 B 验收**

- 所有必需 suite 都有一条 manifest 记录，不能用手写“通过”替代命令输出。
- skipped PostgreSQL 测试不算 PostgreSQL 证据。
- 已知失败与工具缺陷单独登记；未登记失败保持红色。
- 浏览器流程只保护行为与可访问状态，不保护当前 DOM 嵌套和 CSS。

### 增量 C：成对备份、隔离恢复与签收

#### 任务 C1：数据库与 Vault 指纹

**Red**

1. 为表行乱序、JSON key 乱序、空表、无主键表和二进制/时间类型写指纹测试。
2. 为 Vault 内容变化、路径大小写冲突、符号链接和路径逃逸写测试。
3. 断言只记录 hash、count、相对路径，不把真实行内容写入提交目录。

**Green**

1. 数据库按 public 业务表枚举；每表记录 row count 和按主键排序的 canonical row stream SHA-256。
2. 无主键表必须显式失败或使用经审阅的稳定全列排序，不能静默跳过。
3. Vault 对所有普通文件记录相对路径、byte size、SHA-256；临时文件排除规则必须在策略中列明并经过测试。

#### 任务 C2：成对备份

**Red**

使用假的 compose 命令测试：预检失败不停止服务、停止后 dump 失败仍恢复服务、源路径不存在失败、已有目标不覆盖、服务恢复失败导致总体失败。

**Green**

1. `backup-local.ps1` 建立静默窗口。
2. 容器内执行 custom-format `pg_dump -Fc --no-owner --no-acl`，再通过容器 ID 安全复制到 evidence 目录。
3. 从停止的 server 容器复制 Vault 到 staging，验证后用 Python 标准库生成 ZIP。
4. 生成 source fingerprint 和 SHA-256 清单，恢复原服务状态。

#### 任务 C3：隔离恢复演练

**Red**

端到端测试先验证错误 dump、损坏 ZIP、目标冲突、指纹不一致、API 读失败和 cleanup 失败都得到非零退出码。

**Green**

1. 创建带固定安全前缀的临时数据库，把 dump 复制进 PostgreSQL 容器并执行 `pg_restore --exit-on-error`。
2. 安全解压 Vault 到本地临时目录。
3. 重新计算 PostgreSQL/Vault 指纹并与 source fingerprint 逐项比较。
4. 在 deterministic、seed disabled、Compile Worker no-op 的验证夹具中，把现有 app 指向恢复目标，至少读取：

```text
GET /actuator/health
GET /api/vault/status
GET /api/raw
GET /api/ingest
GET /api/wiki
GET /api/runs
GET /api/compile/queue
```

5. 若源数据包含代表性 ID，再读取对应 Run、Topic、Ask 和 CompileTask；没有数据时明确记录 `not_applicable`，不能伪造成功。
6. 清理隔离目标并写入 `restore/report.json`；源数据库与源 Vault 指纹在演练前后必须不变。

#### 任务 C4：一键捕获与文档签收

最终入口：

```powershell
pwsh -File scripts/f01/capture-baseline.ps1 -Mode all
```

脚本依次执行 contracts、tests、backup、restore、verify。任一步失败立即停止后续破坏性步骤，但仍执行服务恢复与临时目标清理。完成后更新：

- `docs/delivery/baselines/f01/README.md`
- `docs/ops/备份与恢复.md`
- `scripts/脚本说明.md`
- `cognitive-map.md`
- 总路线图中的 F01 状态和证据链接

## 7. F01 完成门禁

只有以下条件全部成立，F01 才能标记完成并解锁 F02/F03：

1. 提交的 OpenAPI、PostgreSQL schema、代表性记录和浏览器流程快照均可重复生成且无敏感数据。
2. 后端、前端、类型、lint、build、普通 E2E、真实 full-stack E2E 和 PostgreSQL integration 都有带版本与退出码的运行证据。
3. 没有未知失败；所有已知问题都有精确匹配、证据、处置、失效时间和是否阻塞后续计划的判断。
4. PostgreSQL custom dump 与 Vault ZIP 都有 SHA-256，并在隔离目标中成功恢复。
5. 源库与恢复库的每表 count/hash 相同，源 Vault 与恢复 Vault 的路径/大小/hash 相同。
6. 恢复目标能通过现有应用的健康检查和关键只读 API。
7. 恢复演练没有覆盖或修改活动数据库、活动 Vault；临时目标清理完成，原服务状态恢复。
8. `.local/` 被仓库级 ignore，`git status` 不出现 dump、ZIP、真实 manifest 或测试日志。
9. `docs/ops/备份与恢复.md` 中的命令由本次真实演练验证，不再只是原则描述。
10. 本计划没有产品行为变更、领域表新增、UI 重构或顺手修复。

任一恢复 hash 不一致、源数据被修改、服务未恢复或证据泄露都属于 F01 阻塞失败，不能以 known issue 豁免。

## 8. 失败、回滚与重跑

- 契约快照错误：只回退本次快照与脚本，不触碰数据库/Vault；修正 canonicalizer 后全量重捕获。
- 测试出现未知失败：保留日志，停止签收；确认是已有缺陷后登记，若阻塞 F02/F03 则另开 Bug 计划。
- 备份失败：恢复原服务状态，删除本次不完整 evidence 目录或标记 `INCOMPLETE`，不得发布 checksum。
- 恢复失败：清理隔离目标并保留报告；源资产不参与回滚，因为从未被写入。
- 服务恢复失败：manifest 必须为 `FAIL`，输出精确的 compose 恢复命令，由用户确认服务恢复后才能重跑。
- 快照有意变化：后续计划必须同时提交实现变更、契约 diff、迁移/兼容理由和新快照；禁止直接运行 accept 命令掩盖回归。

每次重跑使用新的 `run-id`，不覆盖历史 evidence。F01 的签收依据是单次完整 `all` 运行，不把多次失败运行中的局部成功拼成一次通过。

## 9. 明确范围外

- 不引入 Alembic，不新增、删除或重命名业务表/列。
- 不拆分 `main.py`、`research.py`、`stage_actions.py` 或前端 feature。
- 不修复现有端口默认值、legacy auth、Worker 耐久性或 app factory 副作用。
- 不建立生产备份调度、跨地域容灾、对象存储、加密密钥管理或 RPO/RTO 承诺。
- 不把本机真实数据、数据库 dump、Vault archive、secret、绝对路径或完整环境变量提交到 Git。
- 不建立视觉截图回归，不冻结当前 UI 样式。
- 不提前实施 F02-F05 的迁移、模块边界、Organization/Space 或 Durable Job。

## 10. 计划自审结论

- **完整性**：覆盖路线图要求的 API、浏览器、OpenAPI、schema、代表性数据、PostgreSQL/Vault 备份恢复和已知失败。
- **设计一致性**：保护外部语义并明确排除实现偶然性，支持后续绞杀式迁移与 Expand/Backfill/Switch/Contract。
- **可构建性**：每项都有精确文件、Red-Green 顺序、命令、产物和失败语义；Docker 是默认路径，host 模式不阻塞默认交付。
- **安全性**：恢复目标隔离、源目标拒绝、静默窗口、checksum、路径逃逸防护和仓库级 ignore 都是硬门禁。
- **分解合理性**：三个增量分别建立契约、行为证据和恢复证据，但共同只交付“迁移前可信基线”这一项能力。
