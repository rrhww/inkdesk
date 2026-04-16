# 本地全栈验收

## 目标

这份文档用于验收 Inkdesk 当前 MVP 的“本地全栈可用闭环”。

当前闭环定义为：

- 真实 owner 登录
- 知识资产创建 / 编辑 / 发布 / 撤回
- 计划创建 / 更新
- 设置持久化
- 本地 `PostgreSQL + MinIO + Spring Boot + Next.js` 协同可用

## 前置条件

1. 已复制环境模板

```powershell
Copy-Item infra/.env.example infra/.env
Copy-Item web/.env.local.example web/.env.local
Copy-Item server/src/main/resources/application-local.yml.example server/src/main/resources/application-local.yml
```

2. 已在 `server/src/main/resources/application-local.yml` 中设置 `inkdesk.auth.secret`
3. 本机已安装 `Docker`、`Java 17`、`Node.js 20+`

## 启动顺序

### 1. 启动基础设施

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

### 2. 启动后端

```powershell
cd server
.\mvnw.cmd spring-boot:run -Dspring-boot.run.profiles=local
```

### 3. 启动前端

```powershell
cd web
npm install
npm run dev
```

## 默认本地 owner 账号

- 邮箱：`owner@inkdesk.local`
- 密码：`inkdesk-owner`

`local` profile 下，如果数据库里还没有 owner 数据，后端会自动写入 owner、工作区、示例知识资产、示例计划和默认设置。

## 手动验收步骤

1. 访问 `http://localhost:3000/login`
2. 使用 owner 账号登录并进入 `/app`
3. 创建一篇新的知识资产并保存
4. 进入 `/app/publish`，将该知识资产发布到公开输出
5. 在 `/` 和 `/articles/[slug]` 验证该内容可见
6. 撤回该知识资产，并验证公共面消失
7. 创建一条计划并关联到这篇知识资产
8. 将该计划状态更新为 `done`
9. 打开 `/app/settings` 修改作者信息和工作台偏好
10. 刷新页面，验证设置继续回显
11. 退出登录，并验证访问 `/app/plans` 会被拦回 `/login`

## 自动化验证

### 后端

```powershell
cd server
.\mvnw.cmd test
```

### 前端单元 / 集成 / 构建

```powershell
cd web
npm test
npm run build
npm run e2e
```

### 真实后端全链路 E2E

```powershell
cd web
npm run e2e:fullstack
```

这个命令会先检查 `.env.local` 中的 API 地址，并等待 Spring Boot 健康检查就绪，再运行 `tests/e2e/local-fullstack.spec.ts`。

如果当前机器缺少 `Docker`、`PostgreSQL` 未监听，或 Spring Boot 尚未启动，脚本会直接输出对应的本地预检提示，帮助定位阻塞点。

## 放行标准

只有以下条件同时满足，才能认为本地全栈闭环达成：

- 后端测试通过
- 前端测试通过
- 前端构建通过
- 默认 E2E 通过
- 全链路 E2E 通过，或明确记录当前机器的环境阻塞原因
- 手动验收没有发现认证、知识、发布、计划、设置、登出链路断点
