# 本地全栈验收

## 目标

这份文档用于验收 Inkvault 当前 Ask-first、vault-first 研究工作台的本地闭环可用性。

当前闭环定义为：

- 真实 owner 登录
- `/app` 作为 Ask-first 主入口可用
- `raw -> ingest -> wiki -> ask` 主路径可用
- Ask 前后都能看到当前知识缺口与下一步动作
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
3. 在 `/app` 验证 Ask-first 首屏可见，并能在 5 秒内看懂 briefing summary、建议提问、知识缺口与下一步动作
4. 打开 `/app/raw`，确认 legacy note 或已导入材料可见
5. 打开 `/app/ingest`，确认存在 AI 编译提案
6. 接受一条提案，并确认它写入目标 wiki 页面
7. 打开 `/app/wiki` 与 `/app/wiki/[id]`，验证 `Current Understanding`、`Key Claims`、`Open Questions`、`Sources` 可见
8. 在 wiki 详情页确认 claim 治理信息可见，包括 `supported / partial / unsupported`、`最近验证`、`证据 N 条`
9. 打开 `/app/ask`，确认它仍可作为兼容别名访问同一 Ask-first 工作区
10. 在 `/app` 或 `/app/ask` 执行一次提问，并确认返回引用来源，且右侧判断面板刷新为问后判断
11. 确认判断面板或支撑线索里能看到当前可用的知识健康信号，至少覆盖 `raw backlog / review backlog / open questions` 中的三类之一；如果当前真实数据已产生 unsupported claim，再额外确认“缺少直接证据”提示可见
12. 继续追问一轮，并确认页面显示正在延续上一轮问答
13. 点击“沉淀到 wiki”，确认跳转到 `/app/ingest?created=...` 并看到成功提示
14. 退出登录，并验证再次访问 `/app/wiki` 会被拦回 `/login`

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

如果当前机器没有完整本地全栈环境，这一项应记录为环境阻塞，而不是产品失败。

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
- Ask-first 首屏与问后判断都能明确展示当前缺口和下一步动作
- claim 治理信息能在 wiki / ingest / Ask-first 判断面板中被直接识别；unsupported / stale / conflicting claim 若当前数据尚未产生，不应作为首轮全链路失败条件
