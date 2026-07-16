# F04 迁移证据

F04 新增默认 Organization、Membership、Capability Space 与 Workspace binding 四张派生表。真实验证只能使用新的 F01 PASS evidence，并运行 `scripts/f04/verify-space-migration.ps1`；产物必须保留在 `.local/`，不得提交真实数据库、Vault 或连接信息。

`rollback-f04` 只允许纯默认拓扑回退到 `f02_0001`；任何额外组织、成员或 Space 都会被拒绝。
