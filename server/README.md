# Server

Inkdesk 的 Spring Boot 后端应用。

## 当前能力

- `Java 17+ / Spring Boot 3`
- `Flyway + PostgreSQL`
- `Actuator health`
- 真实 owner 登录 / 登出 / 会话校验
- 主系统首页聚合接口
- 设置持久化接口
- 知识资产创建 / 编辑 / 发布 / 撤回接口
- 计划读取 / 创建 / 更新接口
- 搜索召回接口
- 公开文章列表与详情接口

## 本地运行

推荐直接复用仓库根目录的基础设施模板：

1. 在项目根目录复制 `infra/.env.example` 为 `infra/.env`
2. 复制 `server/src/main/resources/application-local.yml.example` 为 `server/src/main/resources/application-local.yml`
3. 在 `application-local.yml` 中设置一个足够长的 `inkdesk.auth.secret`
4. 启动 `PostgreSQL + MinIO`

```powershell
docker compose --env-file ..\infra\.env -f ..\infra\docker-compose.yml up -d
```

5. 启动后端本地 profile

```powershell
.\mvnw.cmd spring-boot:run -Dspring-boot.run.profiles=local
```

`local` profile 会在数据库里缺少 owner 或演示数据时自动回补：

- owner 邮箱：`owner@inkdesk.local`
- owner 密码：`inkdesk-owner`
- 示例工作区、知识资产、计划和设置

如果你不使用 `application-local.yml` 文件，也可以直接通过环境变量覆盖：

```powershell
$env:INKDESK_DB_URL='jdbc:postgresql://localhost:5432/inkdesk'
$env:INKDESK_DB_USERNAME='inkdesk'
$env:INKDESK_DB_PASSWORD='inkdesk'
$env:APP_JWT_SECRET='replace-with-a-long-random-secret'
$env:INKDESK_AUTH_SESSION_DURATION='PT8H'
.\mvnw.cmd spring-boot:run
```

测试：

```powershell
.\mvnw.cmd test
```

## 当前接口

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /actuator/health`
- `GET /api/admin/home`
- `GET /api/admin/settings`
- `PATCH /api/admin/settings`
- `GET /api/admin/notes/tree`
- `POST /api/admin/notes`
- `GET /api/admin/notes/{id}`
- `PATCH /api/admin/notes/{id}`
- `POST /api/admin/notes/{id}/publish`
- `POST /api/admin/notes/{id}/unpublish`
- `GET /api/admin/plans`
- `POST /api/admin/plans`
- `PATCH /api/admin/plans/{id}`
- `GET /api/admin/search`
- `GET /api/public/articles`
- `GET /api/public/articles/{slug}`

## 当前边界

- 会话 Cookie 固定为 `inkdesk_owner_session`
- 登录标识固定为邮箱
- 设置持久化到 `workspace_settings`
- 本轮只准备好 `MinIO` 基础设施，不接入附件上传
