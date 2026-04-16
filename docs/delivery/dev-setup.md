# 开发环境准备

## 目标

这份文档用于统一 Inkdesk 的本地开发环境，保证后续前端、后端、数据库和对象存储的启动方式一致。

## 目录约定

- 项目根目录固定为 `E:\dev\projects\inkdesk`
- 正式项目资产全部放在当前目录
- 不把正式文档分散到 `learning/`、`notes/`、`sanbox/`

## 软件准备

### 必装软件

- `Git`
- `Node.js 20+`
- `npm`
- `JDK 17`
- `Maven 3.9+`
- `Docker Desktop`
- `IntelliJ IDEA` 或 `VS Code`

### 建议顺序

1. 安装 Git
2. 安装 Node.js 和 npm
3. 安装 JDK 17 和 Maven
4. 安装 Docker Desktop
5. 安装 IntelliJ IDEA 或 VS Code

## 本地服务组成

### 必需服务

- PostgreSQL
- MinIO

### 可选服务

- Mailpit

## 本地运行原则

- 前端和后端优先本地直接启动，便于热更新
- PostgreSQL 和 MinIO 通过 Docker Compose 托管
- 本轮不需要额外安装本地 PostgreSQL 服务
- `local` profile 负责自动种子 owner 账号与示例数据

## 版本建议

- Node.js：使用当前 LTS 版本
- JDK：固定 `17`
- Maven：`3.9+`
- PostgreSQL：`16+`

## 建议的本地端口分配

- 前端：`3000`
- 后端：`8080`
- PostgreSQL：`5432`
- MinIO API：`9000`
- MinIO Console：`9001`

## 开发前检查项

开始工程实现前，至少确认以下事项：

- `docs/` 中产品、设计、架构文档已经可读
- `git remote -v` 指向 `https://github.com/rrhww/inkdesk.git`
- 项目目录在 `E:\dev\projects\inkdesk`
- 本地能正常使用 Git
- Java、Node.js、npm、Maven 都已安装
- Docker Desktop 可正常启动
- `docker compose` 可正常运行

## 推荐启动顺序

1. 复制环境模板

```powershell
Copy-Item infra/.env.example infra/.env
Copy-Item web/.env.local.example web/.env.local
Copy-Item server/src/main/resources/application-local.yml.example server/src/main/resources/application-local.yml
```

2. 在 `server/src/main/resources/application-local.yml` 中设置 `inkdesk.auth.secret`
3. 启动基础设施

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

4. 启动后端

```powershell
cd server
.\mvnw.cmd spring-boot:run -Dspring-boot.run.profiles=local
```

5. 启动前端

```powershell
cd web
npm install
npm run dev
```

6. 使用本地 owner 账号登录

- 邮箱：`owner@inkdesk.local`
- 密码：`inkdesk-owner`

## 推荐的本地服务职责

- PostgreSQL：业务数据
- MinIO：与未来对象存储形态保持一致的本地占位基础设施
- Docker Compose：本地基础设施启动入口

## 后续衔接点

- 具体仓库流程见 `delivery/repository-workflow.md`
- 环境变量见 `ops/env-vars.md`
- 部署方式见 `ops/deploy-guide.md`
