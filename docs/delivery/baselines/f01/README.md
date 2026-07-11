# F01 当前行为契约与恢复基线

F01 是结构性迁移前的本地恢复基线。它固定当前对外 HTTP 形状、关键行为、浏览器路径、PostgreSQL 结构和代表性记录形状，并通过一次 PostgreSQL + Vault 成对备份与隔离恢复证明恢复路径可读。

## 边界

- 已提交的内容只包括脱敏契约与说明；目录中的 JSON 不包含真实记录、凭据、Cookie、本地 URL、绝对路径、转储、压缩包或运行日志。
- 真实 dump、Vault 压缩包、manifest、日志、指纹和恢复目录只会写入仓库根目录 `.local/f01-baseline/<runId>/`。`.local/` 已被 Git 忽略。
- F01 不修改产品 API、ORM 模型、运行时 DDL 或 UI 行为。
- `PASS` 或 `PASS_WITH_KNOWN_ISSUES` 只能来自一次完整的 `-Mode all` 运行。单项模式仅用于诊断，不能认证基线。

## 已提交契约

- `contracts/openapi.json`：完整 FastAPI OpenAPI 文档。
- `contracts/behavior-contracts.json`：OpenAPI 无法表达的状态机、幂等、Review-first、Vault 路径和 MCP 边界。
- `contracts/browser-flows.json`：全栈浏览器验收流清单。
- `contracts/representative-records.json`：由隔离 SQLite/Vault 和公开 API 生成的合成记录形状。
- `contracts/postgres-schema.json`：默认 Docker PostgreSQL 运行后捕获并人工审阅的结构快照。该文件尚未生成时，F01 不能认证。

`contract-policy.md` 定义规范化、敏感信息与已知问题纪律；`known-issues.json` 只允许精确、可过期且可追溯的例外。

## 运行

先启动默认本地 Docker 栈，并确认 `local-postgres`、`local-server` 与 `local-web` 全部健康。首次为当前 Docker PostgreSQL 建立结构基线时，使用从 Compose 配置解析出的本地 PostgreSQL URL 运行：

```powershell
python scripts/f01/export_postgres_schema.py capture --database-url '<compose PostgreSQL URL>' --snapshot docs/delivery/baselines/f01/contracts/postgres-schema.json
```

检查 diff、确认快照不含业务记录或连接凭据后，再运行完整证据采集：

```powershell
pwsh -File scripts/f01/capture-baseline.ps1 -Mode all
```

采集过程会先比较 OpenAPI 与 PostgreSQL 结构契约，执行后端、前端、浏览器与 PostgreSQL 集成验证，再停止应用服务取得数据库和 Vault 的安静窗口快照。恢复目标使用 `inkdesk_f01_restore_` 前缀，并在默认情况下删除恢复数据库和恢复 Vault；原有服务状态会在 `finally` 中恢复。

完成后检查 `.local/f01-baseline/<runId>/manifest.json`。该 manifest 记录契约 SHA-256、备份 SHA-256、数据库与 Vault 的组合源指纹、恢复报告、测试输出和实际匹配的已知问题。

## 当前状态

F01 已完成默认 Docker Compose 认证：本机 run `20260711T113950Z` 的 `-Mode all` manifest 为 `PASS`，10 个必需 suite、PostgreSQL + Vault 成对恢复、恢复后只读路径和恢复目标清理均通过。真实证据仍只保存在 `.local/f01-baseline/20260711T113950Z/`；后续契约或运行时行为变更必须重新运行完整采集。
