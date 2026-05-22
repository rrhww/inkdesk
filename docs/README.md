# 文档索引

`docs/` 用来解释当前代码已经实现、正在维护、仍值得继续扩展的内容。

当前产品边界已经收敛为：

- 单人私有
- vault-first
- 围绕 `raw -> ingest -> wiki -> ask` 的 LLM Wiki

旧的“公开输出层 / plans / note editor”方向已经退出主路径；相关过时文档已删除或收缩，不再作为项目规范来源。

## 分层说明

- `product/`：当前产品定位、用户故事、阶段路线
- `design/`：当前路由结构、页面清单、视觉令牌
- `architecture/`：系统边界、领域模型、接口、数据库与技术决策
- `delivery/`：本地开发、协作方式、验收与提交流程
- `ops/`：环境变量、部署、备份恢复
- `superpowers/`：仍有参考价值的实现计划与设计稿，只作研发归档，不作为产品主规范

## 推荐阅读顺序

### 第一步，理解当前产品

- `product/mvp-prd.md`
- `product/user-stories.md`
- `product/product-roadmap.md`

### 第二步，理解当前界面与路由

- `design/information-architecture.md`
- `design/page-inventory.md`
- `design/design-tokens.md`

### 第三步，理解实现边界

- `architecture/system-overview.md`
- `architecture/domain-model.md`
- `architecture/api-draft.md`
- `architecture/database-schema.md`
- `architecture/tech-decisions.md`
- `architecture/tooling-and-mcp.md`

### 第四步，理解如何跑起来

- `delivery/dev-setup.md`
- `delivery/local-fullstack-acceptance.md`
- `delivery/release-checklist.md`
- `ops/env-vars.md`
- `ops/deploy-guide.md`
- `ops/backup-restore.md`

### 第五步，理解协作约定

- `delivery/repository-workflow.md`
- `delivery/fullstack-mentorship-plan.md`
- `delivery/growth-engineer-training-manual.md`
- `delivery/mentorship-progress-log.md`

## 文档维护原则

- 文档全部使用中文，接口、路径、命令保留英文
- 同一项事实只保留一个主归属文档，避免复制粘贴式维护
- 当前代码与运行方式优先于历史方案；过时方案应删除或显式归档
- 聊天记录不是规范，真正生效的是仓库里的文档和代码
