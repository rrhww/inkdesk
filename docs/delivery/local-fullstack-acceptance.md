# 本地全栈验收

## 目标

这份文档用于验收 Inkvault 当前 vault-first LLM Wiki 的本地闭环可用性。

当前闭环定义为：

- 真实 owner 登录
- `raw -> ingest -> wiki -> ask` 主路径可用
- 本地 `PostgreSQL + MinIO + Python 主后端 + Next.js` 协同可用

## 前置条件

1. 已复制环境模板

```powershell
Copy-Item infra/.env.example infra/.env
Copy-Item web/.env.local.example web/.env.local
```

2. 已设置足够长的 `INKVAULT_AUTH_SECRET`
3. 本机已安装 `Docker`、`Python 3.12+`、`Node.js 20+`

## 启动顺序

### 1. 启动基础设施

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

### 2. 启动后端

```powershell
cd server
python -m pip install -e .[dev]
python -m uvicorn inkvault_server.main:app --host 0.0.0.0 --port 8080
```

### 3. 启动前端

```powershell
cd web
npm install
npm run dev
```

## 默认本地 owner 账号

- 邮箱：`owner@inkvault.local`
- 密码：`inkvault-owner`

数据库为空时，后端会自动回补 owner、workspace、legacy note 和示例 research 数据。

## 手动验收步骤

1. 访问 `http://localhost:3000/login`
2. 使用 owner 账号登录并进入 `/app`
3. 在 `/app` 验证 Today Vault Panel 已显示真实统计、最新 raw 与 ingest 队列
4. 打开 `/app/raw`，确认 legacy note 或已导入材料可见
5. 打开 `/app/ingest`，确认存在 AI 编译提案
6. 接受一条提案，并确认它写入目标 wiki 页面
7. 打开 `/app/wiki` 与 `/app/wiki/[id]`，验证 `Current Understanding`、`Key Claims`、`Open Questions`、`Sources` 可见
8. 打开 `/app/ask`，执行一次提问并确认返回引用来源
9. 退出登录，并验证再次访问 `/app/wiki` 会被拦回 `/login`

## 自动化验证

### 后端

```powershell
cd server
python -m pytest
```

### 前端单元 / 集成 / 构建

```powershell
cd web
npm test
npm run typecheck
npm run lint
npm run build
npm run e2e
```

### 真实后端全链路 E2E

```powershell
cd web
npm run e2e:fullstack
```

这个命令会先检查 `.env.local` 中的 API 地址，并等待 Python 后端健康检查就绪，再运行 `tests/e2e/local-fullstack.spec.ts`。

如果当前机器缺少 `Docker`、`PostgreSQL` 未监听，或 Python 后端尚未启动，脚本会输出对应的本地预检提示，帮助定位阻塞点。

## 放行标准

只有以下条件同时满足，才能认为本地全栈闭环达成：

- 后端测试通过
- 前端测试通过
- 前端类型检查通过
- 前端 lint 通过
- 前端构建通过
- 默认 E2E 通过
- 全链路 E2E 通过，或明确记录当前机器的环境阻塞原因
- 手动验收没有发现登录、raw、ingest、wiki、ask、登出链路断点
