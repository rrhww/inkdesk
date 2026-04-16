# 仓库流程

## 目标

这份文档用于固定 Inkdesk 的 GitHub 仓库信息、本地仓库规则和单人开发阶段的提交流程。

## 仓库信息

- GitHub 仓库：`https://github.com/rrhww/inkdesk.git`
- 远程名称：`origin`
- 默认分支：`main`
- 当前可见性：`Private`

## 项目根目录

- 本地仓库根目录固定为 `E:\dev\projects\inkdesk`

## 当前开发策略

MVP 阶段采用单人开发简化流程：

- 默认直接在 `main` 分支推进
- 不强制引入 `dev` 分支
- 不强制引入复杂 Git Flow

这样做的原因是：

- 当前只有你自己开发
- 项目还处于 0 到 1 阶段
- 先把流程压简单，比练习复杂分支模型更重要

## 建议的提交流程

### 日常步骤

1. 拉起最新本地代码
2. 修改文档或代码
3. 本地自检
4. `git add .`
5. `git commit -m "..." `
6. `git push origin main`

### 提交原则

- 一次提交只解决一组相对集中的变更
- 文档变更和代码变更可以分开提交
- 正式决策变更要优先更新文档

## 建议的提交信息风格

- `docs: 补齐 MVP 产品与设计文档`
- `feat: 初始化前端项目骨架`
- `feat: 实现笔记编辑接口`
- `chore: 增加本地 docker compose 配置`
- `fix: 修复公开文章页 slug 解析问题`

## 什么时候再引入分支策略

满足以下任一条件后，再考虑引入 `feature` 分支或 `dev` 分支：

- 项目开始频繁上线
- 你希望练习更规范的协作流程
- 引入第二位协作者

## 敏感信息规则

- 密钥和密码不进入仓库
- `.env` 文件不提交
- 生产环境变量只保存在服务器或 CI 配置中

## 文档优先规则

- 重要产品决策先改文档，再改代码
- 技术选型变化先改 `docs/architecture`
- 部署方式变化先改 `docs/ops`

## 后续衔接点

- 本地环境见 `delivery/dev-setup.md`
- 上线前检查见 `delivery/release-checklist.md`
