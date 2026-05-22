# Inkvault

> 一个面向 AI Agent 的个人知识底座：用户只管提问和沉淀，系统负责把有价值回答转成长期可靠知识。

Inkvault 当前的产品主形态已经从“私有 LLM Wiki”继续收敛为：

```text
Ask -> 沉淀 -> 后台知识运行时
```

用户在每个回答之后只需要做一个显性动作：点击“沉淀这次回答”。后续的 topic 路由、claim 提取、证据绑定、冲突检测、wiki patch、质量门控，都由主 Agent 触发专项子 Agent 在后台完成。

对外部 Agent 来说，Inkvault 不是另一个聊天应用，而是可接入的通用知识底座。Claude Code、Codex、Cursor 等工具可以通过 MCP / CLI / 项目级 Skill 调用 Inkvault：任务前获取相关长期上下文，任务后把高价值回答沉淀回知识库。

系统内部仍围绕一条可审计闭环运行：

```text
raw -> ingest -> wiki -> ask
```

- `raw/` 保存网页、PDF 和迁移笔记等原始研究材料。
- `ingest` 是 AI 生成提案、再由人审核的工作流。
- `wiki/` 保存已接受的长期知识页。
- `ask` 先基于 wiki、再基于 raw 进行追问，并在每个回答后提供沉淀入口。

Vault 是事实源。数据库负责索引文件、跟踪工作流状态和缓存读模型，但最终被接受的知识必须始终能从 vault markdown 中恢复出来。

## 产品形态

- 单人私有工作区，通过隐藏的 owner 登录入口访问。
- 登录后进入 Ask-first 研究工作台。
- 每个 Ask 回答都提供“沉淀这次回答”的入口。
- 沉淀动作由主 Agent 编排专项子 Agent 完成，用户不需要理解 claim、health、ingest 等内部协议。
- AI 可以建议新建或补丁 wiki，但不会静默改写正式知识。
- 每一条被接受的 claim 都必须保留回溯到 raw 来源的证据链。
- Inkvault 通过 MCP / CLI / Skill 形态成为外部 Agent 的长期知识底座。

## 产品目标

Inkvault 的目标不是成为更复杂的知识库编辑器，而是成为一层长期可用的 Agent Knowledge Runtime：

- 对用户：把 AI 回答里真正有价值的判断一键沉淀下来。
- 对知识系统：自动完成提取、归档、补证、去重、冲突处理和健康检查。
- 对外部 Agent：提供可查询、可沉淀、可追溯、可迁移的长期知识底座。
- 对项目长期演进：让知识越用越清晰，而不是越问越散、越存越脏。

## 当前项目进度

已完成并推送到 `main` 的阶段性成果：

- 私有 owner 登录与 `/app` 工作区。
- `raw -> ingest -> wiki -> ask` 主闭环。
- raw 文本、网页、PDF 导入与 vault markdown 持久化。
- AI 编译提案、人工接受 / 驳回、wiki 写入。
- Ask-first 工作区、引用回答、追问链与 writeback 提案。
- claim 级证据状态、使用次数、最近验证时间、冲突/过期信号。
- 本地 Docker 全栈：Next.js、FastAPI、PostgreSQL + pgvector。
- 后端 pytest 与前端 TypeScript typecheck 已通过。

下一阶段重点：

- 把“沉淀这次回答”做成每个回答的主操作。
- 将沉淀后的后台流程拆成专项子 Agent：提取、证据绑定、路由、冲突检测、patch、gate。
- 暴露 Inkvault MCP / CLI 接口，让 Claude Code、Codex 等外部 Agent 接入同一知识底座。
- 把 health / ingest / claim 治理继续隐藏在系统层，只在需要用户裁决时轻量打断。

## 当前页面结构

- `/`：根据 owner session 跳转到 `/login` 或 `/app`
- `/login`：隐藏 owner 登录入口
- `/app`：Ask-first 研究入口
- `/app/raw`：vault 中的原始材料
- `/app/ingest`：等待接受 / 驳回的 AI 提案
- `/app/wiki`：已接受的知识页
- `/app/wiki/[id]`：单个 wiki 页面详情，包含 understanding、claims、questions 和 sources
- `/app/ask`：Ask 工作区的兼容别名

像 `/app/inbox`、`/app/review`、`/app/topics`、`/app/sources` 这样的旧路由，当前都不再是正式产品入口。

## 技术栈

- 前端：`Next.js 16`、`React 19`、`TypeScript`、`Tailwind CSS`
- 后端：`FastAPI`、`Python 3.12`、`SQLAlchemy`、`LangGraph`
- 存储：`PostgreSQL + pgvector` 负责索引和工作流状态，挂载的 vault 文件负责 raw/wiki 真相层
- 测试：`node:test`、`Vitest`、`Playwright`、`pytest`

## 快速启动

仓库现在提供一套可直接运行的本地 Docker 栈：

- `inkvault-local-postgres`
- `inkvault-local-server`
- `inkvault-local-web`

先准备环境变量：

```bash
cp infra/.env.example infra/.env
```

然后在 `infra/.env` 里至少填写：

```env
INKVAULT_AUTH_SECRET=换成一个足够长的随机字符串
INKVAULT_AGENT_RUNTIME=langgraph
INKVAULT_AGENT_PROVIDER_PROFILE=openai
OPENAI_API_KEY=sk-xxxx
INKVAULT_AGENT_MODEL=gpt-4.1-mini
INKVAULT_EMBEDDING_PROVIDER_PROFILE=openai
INKVAULT_EMBEDDING_MODEL=text-embedding-3-small
INKVAULT_ENABLE_WEB_ASSIST=true
```

如果你用 DeepSeek，可以改成：

```env
INKVAULT_AGENT_RUNTIME=langgraph
INKVAULT_AGENT_PROVIDER_PROFILE=deepseek
DEEPSEEK_API_KEY=sk-xxxx
INKVAULT_AGENT_MODEL=deepseek-v4-flash
```

克隆并启动：

```bash
git clone <你的仓库地址>
cd inkdesk
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml up -d --build
```

启动后访问：

- 应用入口：`http://localhost:3000/login`
- 后端健康检查：`http://localhost:8080/actuator/health`

默认本地账号：

- 邮箱：`owner@inkvault.local`
- 密码：`inkvault-owner`

停止容器但保留数据：

```bash
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml down
```

重置到干净的本地 demo 状态：

```bash
docker compose --env-file infra/.env -f infra/docker-compose.local-docker.yml down -v
```

## 这个 Demo 包含什么

- 私有 owner 登录
- `/app` 的 Ask-first 工作区
- `raw -> ingest -> wiki -> ask` 研究闭环
- 可直接体验的本地 seed 数据
- 通过 `.env` 注入的真实模型配置
- 已经容器化的前端、后端和 PostgreSQL

## 这个 Demo 不是什么

- 不是公开发布平台
- 不是生产部署方案
- 不是多用户系统
- 不是托管 SaaS

如果要看偏生产部署的说明，见 [docs/ops/deploy-guide.md](docs/ops/deploy-guide.md)。

## 验证

后端：

```powershell
cd server
python -m pytest
```

前端：

```powershell
cd web
npm test
npm run typecheck
npm run lint
npm run build
npm run e2e
npm run e2e:fullstack
```

注意：`npm run e2e` 和 `npm run e2e:fullstack` 需要串行运行，不能并行，因为两者都会触发 Next.js 的 build/start 流程。
