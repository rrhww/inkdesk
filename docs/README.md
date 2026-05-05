# 文档索引

`docs/` 是 Inkvault 项目的唯一正式事实来源。Inkvault 的长期定义已经收敛为“围绕长期项目运转的个人主系统”，当前 MVP 仍保留公开入口与主系统入口：

- 对外是公开输出与分享层
- 对内是主人登录后进入的私有主系统

## 分层说明

- `product/`：产品定位、用户故事、长期路线
- `design/`：信息架构、页面规格、视觉与原型流程
- `architecture/`：系统边界、领域模型、接口、数据库与技术决策
- `delivery/`：阶段排期、开发环境、协作与上线检查
- `ops/`：部署、环境变量、备份与恢复

## 推荐阅读顺序

### 第一步，理解产品

- `product/mvp-prd.md`
- `product/user-stories.md`
- `product/product-roadmap.md`

### 第二步，理解设计

- `design/information-architecture.md`
- `design/page-briefs.md`
- `design/page-inventory.md`
- `design/editor-interactions.md`
- `design/design-workflow.md`
- `design/prototype-plan.md`
- `design/html-direction-review.md`
- `design/stitch-prompts.md`
- `design/stitch-review-checklist.md`

### 第三步，理解技术实现

- `architecture/system-overview.md`
- `architecture/domain-model.md`
- `architecture/api-draft.md`
- `architecture/database-schema.md`
- `architecture/tech-decisions.md`
- `architecture/tooling-and-mcp.md`

### 第四步，理解交付与上线

- `delivery/growth-engineer-training-manual.md`
- `delivery/fullstack-mentorship-plan.md`
- `delivery/mentorship-progress-log.md`
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
- 同一项决策只能有一个主归属文档，避免重复和冲突
- 文档更新优先于实现更新，聊天记录不作为项目规范
