# 技术决策

## 1. 仓库结构

- 继续采用单仓库结构
- `web/` 承担私有研究工作区前端
- `server/` 承担认证、raw / ingest / wiki / ask 接口

## 2. 前端框架

- 继续使用 `Next.js App Router`
- 原因：便于处理 owner session、私有路由守卫和研究工作区服务端渲染

## 3. 主系统路由前缀

- 私有主系统固定为 `/app`
- 原因：复用现有工程结构，降低重构成本

## 4. 根路由入口

- `/` 根据登录态决定跳转 `/login` 或 `/app`
- 原因：当前不提供公开阅读面，产品只服务单主人研究工作流

## 5. 登录模型

- 当前阶段使用真实 single-owner auth + `inkvault_owner_session` Cookie
- 登录标识固定为邮箱
- 原因：本地全栈闭环必须覆盖真实登录、登出与会话校验

## 6. 首页策略

- `/app` 固定为问答型研究入口
- 原因：让 Ask 成为进入系统后的第一感知，而不是后台聚合页

## 7. 知识存储策略

- Vault Markdown 是长期真相来源
- PostgreSQL 负责索引、队列、缓存和工作流状态
- 原因：保证长期可迁移、可重建、可追溯

## 8. Ask 策略

- Ask 优先基于 wiki，其次使用 raw
- `vault` 模式绝不联网
- `vault_plus_web` 只有在证据不足时才显式联网补料
- 原因：控制噪音来源，保持研究过程可解释

## 9. 写操作策略

- AI 只能生成 ingest proposal
- 正式 wiki 写入必须经过人工 accept
- 原因：避免静默改写正式知识

## 10. 写入边界

- 写操作统一走后端 REST 接口
- 前端统一通过 Next.js server action 或服务端 helper 调用
- 不在浏览器直接拼接 owner 写请求
