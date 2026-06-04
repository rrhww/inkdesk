# 开发环境准备

## 目标

统一 Inkdesk 当前本地开发环境，保证前端、Python 主后端、数据库与 vault 存储的启动方式一致。

## 软件准备

### 必装软件

- `Git`
- `Node.js 20+`
- `npm`
- `Python 3.12+`
- `Docker Desktop`
- `VS Code`、`PyCharm` 或 `IntelliJ IDEA`

### 建议顺序

1. 安装 Git
2. 安装 Node.js 和 npm
3. 安装 Python 3.12+
4. 安装 Docker Desktop
5. 安装常用 IDE

## 本地服务组成

### 必需服务

- PostgreSQL
- MinIO

## 本地运行原则

- 前端和后端优先本地直接启动，便于热更新
- PostgreSQL 和 MinIO 通过 Docker Compose 托管
- Vault 数据默认写入 `server/inkdesk-vault`，也可以通过环境变量改为外部目录
- 后端启动时会自动回补 owner、workspace 与示例 research 数据

## 版本建议

- Node.js：当前 LTS 版本
- Python：`3.12+`
- PostgreSQL：`16+`

## 建议的本地端口分配

- 前端：`3000`
- 后端：`8080`
- PostgreSQL：`5432`
- MinIO API：`9000`
- MinIO Console：`9001`

## 开发前检查项

- `docs/` 中产品、设计、架构文档已经可读
- `git remote -v` 指向正确仓库
- 本地能正常使用 Git
- Node.js、npm、Python 都已安装
- Docker Desktop 可正常启动
- `docker compose` 可正常运行

## 推荐启动顺序

1. 复制环境模板

```powershell
Copy-Item infra/.env.example infra/.env
Copy-Item web/.env.local.example web/.env.local
```

`web/.env.local` 在只看本地 fixtures 时可以留空；如果要跑真实后端或 `npm run e2e:fullstack`，至少填一个 API 基地址。

2. 设置后端关键变量

```powershell
$env:INKDESK_AUTH_SECRET='replace-with-a-long-random-secret'
$env:INKDESK_VAULT_ROOT='C:\path\to\inkdesk-vault'
$env:INKDESK_AGENT_PROVIDER_PROFILE='openai' # 或 deepseek
```

3. 启动基础设施

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

4. 启动后端

```powershell
cd server
python -m pip install -e .[dev]
python -m uvicorn inkdesk_server.main:app --host 0.0.0.0 --port 8080
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

- PostgreSQL：索引、提案、session、问答记录
- MinIO：对象存储形态占位，当前主路径不依赖附件上传
- Vault 目录：`raw/` 与 `wiki/` 长期真相
- Docker Compose：基础设施启动入口

## 后续衔接点

- 环境变量见 `ops/env-vars.md`
- 部署方式见 `ops/deploy-guide.md`
