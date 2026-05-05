# 环境变量

## 目标

这份文档只记录当前仓库已经落地并正在使用的环境变量，避免继续保留和现状不一致的占位命名。

## 约定

- 所有生产密钥不进入仓库
- 示例值只用于说明格式，不可直接用于生产
- 本地推荐直接从各目录下的 `.example` 模板复制

## 前端变量

### `INKVAULT_API_BASE_URL`

- 用途：Next.js 服务端渲染和 server action 访问 Python 主后端的基础地址
- 示例：`http://localhost:8080`
- 说明：可写成 `http://localhost:8080` 或 `http://localhost:8080/api`

### `NEXT_PUBLIC_API_BASE_URL`

- 用途：浏览器侧访问 Python 主后端的基础地址
- 示例：`http://localhost:8080`
- 说明：可写成 `http://localhost:8080` 或 `http://localhost:8080/api`

### `INKVAULT_E2E_BACKEND_TIMEOUT_MS`

- 用途：控制 `web npm run e2e:fullstack` 在启动 Playwright 前等待真实后端健康检查的最长时间
- 示例：`60000`
- 说明：单位为毫秒；超过该时间仍无法访问后端时，脚本会输出本地后端 / PostgreSQL / Docker 预检提示

## 后端变量

### `INKVAULT_DB_URL`

- 用途：Python 主后端的数据库连接地址
- 示例：`postgresql+psycopg://inkvault:inkvault@localhost:5432/inkvault`

### `INKVAULT_VAULT_ROOT`

- 用途：vault 根目录，后端会在其中维护 `raw/`、`wiki/` 与 `AGENTS.md`
- 示例：`C:\path\to\inkvault-vault`

### `INKVAULT_AUTH_SECRET`

- 用途：owner session token 的签名密钥
- 示例：`replace-with-a-long-random-secret`

### `APP_JWT_SECRET`

- 用途：旧环境变量兼容别名
- 说明：当前仍可读取，但新部署统一使用 `INKVAULT_AUTH_SECRET`

### `INKVAULT_AUTH_SESSION_DURATION`

- 用途：owner session 时长
- 示例：`PT8H`

### `INKVAULT_AGENT_RUNTIME`

- 用途：指定 agent runtime 类型
- 示例：`langgraph`

### `INKVAULT_AGENT_PROVIDER_PROFILE`

- 用途：选择正式 provider profile
- 示例：`openai`、`deepseek`、`openai_compatible`
- 说明：`deepseek` 会自动带入 `https://api.deepseek.com` 和 `json_mode`；`openai` 默认带入 `https://api.openai.com/v1` 和 `json_schema`

### `INKVAULT_AGENT_MODEL`

- 用途：覆盖当前 provider profile 的默认模型名
- 示例：`gpt-4.1-mini`、`deepseek-v4-flash`

### `INKVAULT_AGENT_API_KEY`

- 用途：显式覆盖当前 provider profile 使用的 API key
- 说明：优先级高于 `OPENAI_API_KEY` / `DEEPSEEK_API_KEY`

### `INKVAULT_AGENT_BASE_URL`

- 用途：显式覆盖当前 provider profile 使用的基础地址
- 说明：主要用于 `openai_compatible` / `custom` 场景

### `OPENAI_API_KEY`

- 用途：`openai` profile 的默认模型服务密钥

### `DEEPSEEK_API_KEY`

- 用途：`deepseek` profile 的默认模型服务密钥

### `OPENAI_BASE_URL`

- 用途：兼容旧配置的基础地址别名
- 说明：当未设置 `INKVAULT_AGENT_BASE_URL` 时，`openai` / `openai_compatible` 仍会读取它；`deepseek` profile 未显式覆盖时默认使用 `https://api.deepseek.com`

### `INKVAULT_ENABLE_LOCAL_SEED`

- 用途：控制本地 owner、workspace 与示例 research 数据自动回补
- 示例：`true`

## 基础设施变量

这些变量由 `infra/.env` 消费，用于本地 `docker compose`。

### `POSTGRES_DB`

- 用途：本地 PostgreSQL 数据库名
- 示例：`inkvault`

### `POSTGRES_USER`

- 用途：本地 PostgreSQL 用户名
- 示例：`inkvault`

### `POSTGRES_PASSWORD`

- 用途：本地 PostgreSQL 密码
- 示例：`inkvault`

### `POSTGRES_PORT`

- 用途：本地 PostgreSQL 暴露端口
- 示例：`5432`

### `MINIO_ROOT_USER`

- 用途：本地 MinIO 管理账号
- 示例：`inkvault`

### `MINIO_ROOT_PASSWORD`

- 用途：本地 MinIO 管理密码
- 示例：`inkvaultminio`

### `MINIO_API_PORT`

- 用途：本地 MinIO API 端口
- 示例：`9000`

### `MINIO_CONSOLE_PORT`

- 用途：本地 MinIO Console 端口
- 示例：`9001`

### `INKVAULT_SERVER_PORT`

- 用途：本地 Python 主后端暴露端口
- 示例：`8080`

## 当前边界

- Vault 文件是长期真相，DB 不是唯一真相
- 当前只准备 `MinIO` 基础设施，不接入主路径附件上传
- 如果新增新的运行变量，必须先更新本文件和对应 `.example` 模板
