# 文档索引

`docs/` 是 Inkvault 项目的正式事实来源。Inkvault 的当前定义已经收敛为：

- 一个单人私有、vault-first、以知识健康为核心的 AI 研究系统
- 一条明确的主闭环：`raw -> ingest -> wiki -> ask -> health -> ingest`

## 分层说明

- `product/`：产品定位、用户故事、长期路线
- `design/`：信息架构、页面规格、视觉与原型流程
- `architecture/`：系统边界、领域模型、接口、数据库与技术决策
- `delivery/`：阶段排期、开发环境、协作与上线检查
- `ops/`：部署、环境变量、备份与恢复
- `superpowers/`：开发期设计稿、执行计划和历史规格归档

## 推荐阅读顺序

### 第一步，理解产品

- `product/product-vision.md`
- `product/mvp-prd.md`
- `product/user-stories.md`
- `product/product-roadmap.md`

### 第二步，理解设计

- `design/information-architecture.md`
- `design/page-briefs.md`

### 第三步，理解技术实现

- `architecture/system-overview.md`
- `architecture/domain-model.md`
- `architecture/api-draft.md`
- `architecture/database-schema.md`
- `architecture/tech-decisions.md`
- `architecture/tooling-and-mcp.md`

### 第四步，理解交付与上线

- `delivery/development-plan.md`
- `delivery/mvp-roadmap.md`
- `delivery/dev-setup.md`
- `delivery/repository-workflow.md`
- `delivery/release-checklist.md`
- `ops/deploy-guide.md`
- `ops/env-vars.md`
- `ops/backup-restore.md`

## 文档维护原则

- 文档全部使用中文，技术名词、接口、路径保留英文
- 当前主叙事以 `product/product-vision.md` 和 `raw -> ingest -> wiki -> ask -> health -> ingest` 为准
- 历史方案、旧路线和设计归档放在历史文档中，不作为当前产品定义
- 同一项决策只能有一个主归属文档，避免重复和冲突
- 文档更新优先于实现更新，聊天记录不作为项目规范
