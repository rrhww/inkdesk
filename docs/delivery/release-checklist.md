# 上线检查清单

## 本轮目标

本轮的放行标准不是“差不多能看”，而是本地全栈闭环成立。

## 基础设施

- `docker compose` 能拉起 `PostgreSQL + MinIO`
- Spring Boot 可连接本地 PostgreSQL
- Next.js 可连接 Spring Boot
- `local` profile 会自动提供 owner 账号和示例数据

## 主系统链路

- `/login` 可访问
- 使用 `owner@inkdesk.local / inkdesk-owner` 可登录
- 登录后进入 `/app`
- 未登录访问 `/app/*` 会被拦回 `/login`
- `/app` 第一屏是 Agent 控制台
- `/app/settings` 可读取并保存设置
- 退出登录后再次访问 `/app/*` 会被拦回 `/login`

## 知识与发布链路

- 可以创建一篇新的知识资产
- 可以再次打开并保存该知识资产
- 可以从 `/app/publish` 发布该知识资产
- 发布后 `/` 与 `/articles/[slug]` 可见
- 可以撤回该知识资产
- 撤回后公共面不可见

## 计划链路

- 可以创建新计划
- 可以将计划关联到知识资产
- 可以更新计划状态
- 更新后页面可立即回显真实值

## 自动化验证

- `server\\mvnw.cmd test` 通过
- `web\\npm test` 通过
- `web\\npm run build` 通过
- `web\\npm run e2e` 通过
- 如果本地全栈环境已启动，`web\\npm run e2e:fullstack` 通过

## 阻塞项判定

以下任一项不满足，都不能标记为放行：

- 认证链路断开
- 知识创建 / 保存 / 发布 / 撤回任一环节失败
- 计划创建 / 更新失败
- 设置刷新后无法回显
- 未登录仍能进入私有页面
- 测试或构建存在失败
