# 上线检查清单

## 本轮目标

本轮的放行标准不是“差不多能看”，而是私有 vault-first LLM Wiki 的本地全栈闭环成立。

## 基础设施

- `docker compose` 能拉起 `PostgreSQL + MinIO`
- Python 主后端可连接本地 PostgreSQL
- Next.js 可连接 Python 主后端
- 默认启动会提供 owner 账号与示例 research 数据

## 主系统链路

- `/login` 可访问
- 使用 `owner@inkvault.local / inkvault-owner` 可登录
- 登录后进入 `/app`
- 未登录访问 `/app/*` 会被拦回 `/login`
- `/app` 第一屏是 Today Vault Panel
- `/app/raw`、`/app/ingest`、`/app/wiki`、`/app/ask` 可正常访问
- 退出登录后再次访问 `/app/*` 会被拦回 `/login`

## 研究闭环链路

- 原始材料可以进入 `raw/`
- ingest 提案不会静默写入 wiki
- 接受提案后才会创建或更新 wiki 页面
- wiki 页面能看到 understanding、claims、questions、sources
- Ask 返回 wiki/source citation

## 自动化验证

- `cd server && python -m pytest` 通过
- `cd web && npm test` 通过
- `cd web && npm run typecheck` 通过
- `cd web && npm run lint` 通过
- `cd web && npm run build` 通过
- `cd web && npm run e2e` 通过
- 如果本地全栈环境已启动，`cd web && npm run e2e:fullstack` 通过

## 阻塞项判定

以下任一项不满足，都不能标记为放行：

- 认证链路断开
- raw / ingest / wiki / ask 任一环节失败
- 提案未经确认直接写入 wiki
- Ask 缺少引用来源
- 未登录仍能进入私有页面
- 测试、类型检查、lint 或构建存在失败
