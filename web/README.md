# Web

这里是 Inkdesk 的 Next.js 前端应用。

## 当前页面模型

- `/`：公共博客首页 / 作者展示页
- `/login`：主人隐藏登录入口
- `/app`：Agent 控制台首页
- `/app/library`：笔记与知识库
- `/app/plans`：任务 / 计划
- `/app/search`：全局检索 / 知识召回
- `/app/publish`：次级发布模块
- `/app/notes/[id]`：知识资产编辑页
- `/articles/[slug]`：公开文章页

## 入口规则

- 未登录访问 `/`：看到公共博客页
- 已登录访问 `/`：自动重定向到 `/app`
- 未登录访问 `/app/*`：自动跳转 `/login`

## 当前真实闭环

- `/login` 已接到真实 owner 登录接口
- `/app/notes/[id]` 支持真实创建 / 保存知识资产
- `/app/publish` 支持真实发布 / 撤回
- `/app/plans` 支持真实创建 / 更新计划
- `/app/settings` 支持真实设置持久化

如果需要保留演示态，编辑页仍兼容部分查询参数切换：

- `/app/notes/note-002?state=blank`
- `/app/notes/note-001?state=loading`
- `/app/notes/note-002?state=draft`
- `/app/notes/note-002?state=saving`
- `/app/notes/note-002?state=error`
- `/app/notes/note-001?state=published`

## 本地启动

1. 在 `web/` 目录安装依赖：`npm install`
2. 复制 `web/.env.local.example` 为 `web/.env.local`
3. 如需接入真实后端，保持 `INKDESK_API_BASE_URL` / `NEXT_PUBLIC_API_BASE_URL` 指向 Spring Boot
4. 启动开发环境：`npm run dev`
5. 浏览器访问：`http://localhost:3000`

## 数据来源

默认情况下，前端会继续使用本地 mock 数据。

如果配置以下任一变量，公开文章、知识资产、搜索、计划和发布模块只读链路会优先读取后端：

- `NEXT_PUBLIC_API_BASE_URL`
- `INKDESK_API_BASE_URL`

变量既可以写成 `http://localhost:8080`，也可以直接写成 `http://localhost:8080/api`。当前已接入的真实数据页面包括：

- `/app`
- `/`
- `/articles/[slug]`
- `/app/library`
- `/app/notes/[id]`
- `/app/search`
- `/app/plans`
- `/app/publish`
- `/app/settings`

其中 `/app`、`/app/library`、`/app/notes/[id]`、`/app/search`、`/app/plans` 和 `/app/publish` 会在服务端渲染时自动转发 `inkdesk_owner_session` cookie 给 Spring Boot 的 `/api/admin/*` 接口。`/app` 当前复用 `/api/admin/home`，`/app/publish` 当前复用 `/api/admin/notes/tree` 来重建发布控制台。未配置后端地址时，这些页面会自动回退到 mock 数据。

隐藏登录入口的 mock 凭证固定为：

- 邮箱：`owner@inkdesk.local`
- 密码：`inkdesk-owner`

当前主系统壳层已经包含桌面侧边栏和移动端导航，`/app` 首页会优先展示 Agent 控制台与工作台摘要。

## 测试

```powershell
npm test
npm run build
npm run e2e
```

如果本地 `PostgreSQL + MinIO + Spring Boot` 已经启动，可以额外执行真实后端闭环验收：

```powershell
npm run e2e:fullstack
```

这个命令会先等待真实后端健康检查，并在后端、`PostgreSQL` 或 `Docker` 未就绪时直接打印本地预检提示。
