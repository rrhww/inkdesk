# Web

Inkvault 的 Next.js 前端应用，当前只服务于单人私有、Vault-first 的 LLM Wiki。

## 当前页面模型

- `/`：根据 owner session 重定向到 `/login` 或 `/app`
- `/login`：隐藏 owner 登录入口
- `/app`：Today Vault Panel
- `/app/raw`：raw 原始材料 vault
- `/app/ingest`：AI 提案审阅队列
- `/app/wiki`：已接受的 wiki 页面
- `/app/wiki/[id]`：单个 wiki 页面详情
- `/app/ask`：基于 wiki 优先、raw 补充的问答

兼容路由：

- `/app/inbox` -> `/app/raw`
- `/app/review` -> `/app/ingest`
- `/app/topics` -> `/app/wiki`
- `/app/sources` -> `/app/raw`

## 入口规则

- 未登录访问 `/`：跳转到 `/login`
- 已登录访问 `/`：跳转到 `/app`
- 未登录访问 `/app/*`：自动跳转 `/login`

## 当前产品边界

- 没有公开阅读面
- 没有 plans 模块
- 没有 publish 模块
- 没有旧的 note editor 工作流
- raw / ingest / wiki 是主产品语言，legacy note 只作为迁移来源存在

## 本地启动

1. 在 `web/` 目录安装依赖：`npm install`
2. 复制 `web/.env.local.example` 为 `web/.env.local`
3. 如需接入真实后端，设置 `INKVAULT_API_BASE_URL` 或 `NEXT_PUBLIC_API_BASE_URL`
4. 启动开发环境：`npm run dev`
5. 浏览器访问：`http://localhost:3000`

## 数据来源

默认情况下，前端会回退到本地 research fixtures。

如果配置以下任一变量，前端会优先读取 Python 主后端：

- `NEXT_PUBLIC_API_BASE_URL`
- `INKVAULT_API_BASE_URL`

变量既可以写成 `http://localhost:8080`，也可以直接写成 `http://localhost:8080/api`。

当前接入后端的页面与动作包括：

- `/app`
- `/app/raw`
- `/app/ingest`
- `/app/wiki`
- `/app/wiki/[id]`
- `/app/ask`
- owner 登录 / 登出 / session 校验

这些页面会在服务端渲染时自动转发 `inkvault_owner_session` cookie 给后端私有接口。未配置后端地址时，会自动回退到本地 research fixtures。

隐藏登录入口的默认凭证固定为：

- 邮箱：`owner@inkvault.local`
- 密码：`inkvault-owner`

## 测试

```powershell
npm test
npm run typecheck
npm run lint
npm run build
npm run e2e
```

如果本地 `PostgreSQL + MinIO + Python 主后端` 已启动，可以额外执行真实后端闭环验收：

```powershell
npm run e2e:fullstack
```

这个命令会走一遍 login -> ingest -> wiki -> ask -> raw 的 LLM Wiki 闭环。
