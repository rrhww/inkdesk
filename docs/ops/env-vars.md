# 环境变量

## 目标

这份文档只记录当前仓库已经落地并正在使用的环境变量，避免继续保留和现状不一致的占位命名。

## 约定

- 所有生产密钥不进入仓库
- 示例值只用于说明格式，不可直接用于生产
- 本地推荐直接从各目录下的 `.example` 模板复制

## 前端变量

### `INKDESK_API_BASE_URL`

- 用途：Next.js 服务端渲染和 server action 访问 Spring Boot 的基础地址
- 示例：`http://localhost:8080`
- 说明：可写成 `http://localhost:8080` 或 `http://localhost:8080/api`

### `NEXT_PUBLIC_API_BASE_URL`

- 用途：浏览器侧公开页面访问 Spring Boot 的基础地址
- 示例：`http://localhost:8080`
- 说明：可写成 `http://localhost:8080` 或 `http://localhost:8080/api`

### `INKDESK_E2E_BACKEND_TIMEOUT_MS`

- 用途：控制 `web npm run e2e:fullstack` 在启动 Playwright 前等待真实后端健康检查的最长时间
- 示例：`60000`
- 说明：单位为毫秒；超过该时间仍无法访问后端时，脚本会输出本地后端 / PostgreSQL / Docker 预检提示

## 后端变量

### `INKDESK_DB_URL`

- 用途：Spring Boot 数据源地址
- 示例：`jdbc:postgresql://localhost:5432/inkdesk`

### `INKDESK_DB_USERNAME`

- 用途：数据库用户名
- 示例：`inkdesk`

### `INKDESK_DB_PASSWORD`

- 用途：数据库密码
- 示例：`inkdesk`

### `APP_JWT_SECRET`

- 用途：owner session token 的签名密钥
- 示例：`replace-with-a-long-random-secret`

### `INKDESK_AUTH_SESSION_DURATION`

- 用途：owner session 时长
- 示例：`PT8H`

## 基础设施变量

这些变量由 `infra/.env` 消费，用于本地 `docker compose`。

### `POSTGRES_DB`

- 用途：本地 PostgreSQL 数据库名
- 示例：`inkdesk`

### `POSTGRES_USER`

- 用途：本地 PostgreSQL 用户名
- 示例：`inkdesk`

### `POSTGRES_PASSWORD`

- 用途：本地 PostgreSQL 密码
- 示例：`inkdesk`

### `POSTGRES_PORT`

- 用途：本地 PostgreSQL 暴露端口
- 示例：`5432`

### `MINIO_ROOT_USER`

- 用途：本地 MinIO 管理账号
- 示例：`inkdesk`

### `MINIO_ROOT_PASSWORD`

- 用途：本地 MinIO 管理密码
- 示例：`inkdeskminio`

### `MINIO_API_PORT`

- 用途：本地 MinIO API 端口
- 示例：`9000`

### `MINIO_CONSOLE_PORT`

- 用途：本地 MinIO Console 端口
- 示例：`9001`

## 当前边界

- 本轮只准备 `MinIO` 基础设施，不接入附件上传
- 本地 `local` profile 会自动种子 owner 账号和示例内容，不依赖额外 owner 环境变量
- 如果新增新的运行变量，必须先更新本文件和对应 `.example` 模板
