# F02 迁移证据

F02 建立 Alembic 作为唯一数据库 DDL 权威。提交到 Git 的是 migration、测试和操作文档；真实 dump、Vault archive、连接地址和 manifest 仅保留在 `.local/f02-migrations/`。

完成门禁：

- F01 manifest 必须为 `PASS` 且校验通过。
- 空 PostgreSQL 只能通过 Alembic 到达 `f02_0001`，并匹配 F01 schema digest。
- F01 restore 的接管前后 application schema digest、row count 和 row fingerprint 一致。
- unknown/partial/drift/revision 异常 fail closed，migration lock 超时和 DDL 权限失败均不写 version。
- Docker 先 migration 后启动，后端全量测试、pgvector integration 和全栈 E2E 通过。

最近一次本地 F02 verifier PASS run 为 `20260714T151606Z`，引用 F01 run `20260711T113950Z`。该 run 的本地 manifest 包含 fresh upgrade、strict adoption、7 条只读 API、unsupported schema、DDL 权限失败与 lock 验证结果。
