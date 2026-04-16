# 工具链与 MCP

## 目标

这份文档用于统一记录 Inkdesk 项目开发过程中推荐使用的软件、学生可申请的工具权益、MCP 建议，以及这些工具在开发期和生产期的边界。

## 一、开发软件清单

### 必装软件

- `Git`
- `Node.js LTS`
- `pnpm`
- `JDK 21`
- `Maven 3.9+`
- `Docker Desktop`
- `PostgreSQL`
- `IntelliJ IDEA` 或 `VS Code`
- `DBeaver`
- `Figma Desktop`

### 推荐补充软件

- `Postman` 或 `Bruno`
- `TablePlus` 或继续使用 `DBeaver`
- `Typora` 或任意 Markdown 阅读器

## 二、本地服务依赖

本地开发建议准备以下服务：

- PostgreSQL
- MinIO
- 可选的 Mailpit

其中：

- PostgreSQL 用于主数据库
- MinIO 用于模拟生产对象存储
- Mailpit 可作为后续邮件调试工具预留

## 三、学生权益

### Figma Education

可申请原因：

- 你是学生
- 项目需要用 Figma 作为正式设计源

用途：

- 原型设计
- 组件库
- Dev Mode 交付

### JetBrains Student Pack

可申请原因：

- 你以 Java 为主栈
- IntelliJ IDEA 对 Spring Boot 开发体验更好

用途：

- 后端开发
- 调试和数据库工具协作

## 四、MCP 使用建议

### 必备 MCP

- `Figma MCP`
- `GitHub MCP`
- `Playwright MCP`
- `filesystem` / `fetch` 类参考 MCP

### 使用目标

- `Figma MCP`：把设计上下文交给前端实现
- `GitHub MCP`：辅助仓库上下文、PR 和代码协作
- `Playwright MCP`：页面流程检查和回归验证
- `filesystem/fetch`：补充文档与文件上下文

## 五、哪些是开发期依赖

以下属于开发期工具，不是线上运行依赖：

- Figma
- GPT-5
- Google Stitch
- GitHub MCP
- Playwright MCP
- 本地 IDE

这些工具用于：

- 设计探索
- 设计交付
- 代码生成和辅助实现
- 页面验证

## 六、哪些不进入生产

生产环境不需要把以下内容作为线上服务部署：

- MCP 服务
- Figma
- Google Stitch
- GitHub 相关辅助工具
- 本地开发辅助脚本

生产环境只需要承载：

- 前端应用
- 后端应用
- PostgreSQL
- Nginx
- COS

## 七、工具链原则

- 优先使用能减少重复劳动的工具
- 不把开发辅助工具强行带进生产环境
- 工具链服务于文档、设计和实现，不反过来绑架架构

## 后续衔接点

- 本地准备见 `delivery/dev-setup.md`
- 仓库流程见 `delivery/repository-workflow.md`
