# 工具链与 MCP

## 目标

统一记录 Inkdesk 当前研发期推荐的软件、MCP 与它们在开发期和生产期的边界。

## 一、开发软件清单

### 必装软件

- `Git`
- `Node.js LTS`
- `npm`
- `Python 3.12+`
- `Docker Desktop`
- `PostgreSQL`
- `VS Code`、`PyCharm` 或 `IntelliJ IDEA`
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

其中：

- PostgreSQL 用于主数据库、索引和提案状态
- MinIO 仅作为对象存储形态占位，当前主路径不依赖附件上传

## 三、学生权益

### Figma Education

用途：

- 原型设计
- 组件库
- Dev Mode 交付

### JetBrains Student Pack

用途：

- Python 主后端开发
- 数据库调试
- 前后端联调

## 四、Inkdesk 作为 Agent 知识底座

Inkdesk 的长期形态不是只在自己的 Web App 里回答问题，而是作为 Claude Code、Codex、Cursor 等外部 Agent 的通用知识底座。

外部 Agent 接入 Inkdesk 时，只需要理解两个动作：

```text
context_pack -> 任务前获取相关长期知识
deposit -> 任务后把高价值回答或片段交给 Inkdesk 沉淀
```

外部 Agent 不应该直接写 `wiki/`，也不需要理解 `claim / ingest / health / lint` 的完整内部协议。它们只把上下文和沉淀请求交给 Inkdesk，由 Inkdesk 的主 Agent 和专项子 Agent 完成后续逻辑。

### 对外接口草案

第一版建议同时提供 CLI 与 MCP server。

CLI：

```bash
inkdesk context --task "<当前任务>" --repo "<仓库路径>" --max-tokens 3000
inkdesk deposit --question "<用户问题>" --answer-file answer.md --repo "<仓库路径>"
inkdesk deposit-selection --text-file selection.md --reason "<为什么值得沉淀>"
```

MCP tools：

- `inkdesk.context_pack(task, repo, files, max_tokens)`：返回外部 Agent 可直接阅读的短上下文包。
- `inkdesk.search(query, scope, limit)`：搜索长期知识。
- `inkdesk.deposit_answer(question, answer, citations, source_context)`：沉淀一段完整回答。
- `inkdesk.deposit_selection(text, reason, source_context)`：沉淀用户选中的片段。
- `inkdesk.open_questions(scope)`：返回相关未解决问题。
- `inkdesk.decision_history(topic)`：返回某个主题的稳定判断和变更记录。

### 外部 Agent 使用协议

外部 Agent 在任务开始时：

1. 判断任务是否依赖长期知识、产品方向、历史决策或仓库约定。
2. 调用 `context_pack` 获取短上下文。
3. 只把返回结果作为上下文，不自行改写 Inkdesk 长期知识。

外部 Agent 在任务结束时：

1. 如果回答中有可长期复用的判断、方案、设计取舍或复盘，提示用户是否沉淀。
2. 用户确认后调用 `deposit_answer` 或 `deposit_selection`。
3. Inkdesk 后台完成提取、证据绑定、topic 路由、冲突检测和质量门控。

### Codex 接入形态

Codex 推荐三层接入：

- MCP server：提供 `context_pack` 和 `deposit` 工具。
- Codex Skill：说明什么时候调用 Inkdesk，什么时候建议用户沉淀。
- 项目 `AGENTS.md`：声明本项目长期知识由 Inkdesk 管理。

项目级提示建议：

```text
When the task depends on product memory, project history, or durable decisions, call Inkdesk for a context pack before proposing changes.
After producing durable product, architecture, or workflow decisions, ask the user whether to deposit the answer into Inkdesk.
Never write long-term knowledge directly to repo docs unless the user explicitly asks; use Inkdesk deposit first.
```

### Claude Code 接入形态

Claude Code 推荐通过 MCP server 和 slash command 接入：

- `/inkdesk-context`：获取当前任务相关上下文。
- `/deposit`：把当前回答或选中内容提交给 Inkdesk 沉淀。

用户体验应该保持简单：

```text
Claude Code 完成回答
用户输入 /deposit
Inkdesk 后台沉淀
必要时返回轻量冲突裁决卡片
```

## 五、开发期 MCP 使用建议

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

## 六、哪些是开发期依赖

以下属于开发期工具，不是线上运行依赖：

- Figma
- GPT-5
- GitHub MCP
- Playwright MCP
- 本地 IDE

这些工具用于：

- 设计探索
- 设计交付
- 代码生成和辅助实现
- 页面验证

## 七、哪些不进入生产

生产环境不需要把以下内容作为线上服务部署：

- MCP 服务
- Figma
- GitHub 相关辅助工具
- 本地开发辅助脚本

生产环境只需要承载：

- 前端应用
- Python 主后端
- PostgreSQL
- Nginx
- Vault 存储目录

注意：Inkdesk 自己未来提供的 MCP server / CLI bridge 属于产品接入层，不等同于开发期 MCP 工具。开发期 MCP 不进生产；产品化 Inkdesk connector 可以作为独立本地服务或桌面侧桥接器交付。

## 八、工具链原则

- 优先选择能服务 `raw -> ingest -> wiki -> ask` 主路径的工具
- 不把开发辅助工具强行带进生产环境
- 工具链服务于产品边界，不反过来绑架架构
- 外部 Agent 接入只暴露简单协议：取上下文、沉淀结果
- 复杂知识治理保留在 Inkdesk 内部，不泄漏给外部 Agent

## 后续衔接点

- 本地准备见 `delivery/dev-setup.md`
- 仓库流程见 `delivery/repository-workflow.md`
