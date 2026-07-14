# Flyway 历史目录

`V1` 到 `V8` 是 Inkdesk 早期 Flyway SQL 的历史参考，不再由任何运行路径执行。

从 F02 起，Python 后端的数据库 DDL 唯一权威是 `server/alembic/`。不得在此目录新增 revision、继续编号或把 SQL 接回应用启动流程。后续 schema 变化必须新增 Alembic revision，并在变更计划中说明验证和恢复策略。
