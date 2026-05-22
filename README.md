# Inkvault

> 一个单人使用、私有、vault-first 的研究记忆系统。

Inkvault 围绕一条核心闭环展开：

```text
raw -> ingest -> wiki -> ask
```

- `raw/` 保存网页、PDF 和迁移笔记等原始研究材料。
- `ingest` 是 AI 生成提案、再由人审核的工作流。
- `wiki/` 保存已接受的长期知识页。
- `ask` 先基于 wiki、再基于 raw 进行追问，并可把当前回答回写成新的审阅提案。

Vault 是事实源。数据库负责索引文件、跟踪工作流状态和缓存读模型，但最终被接受的知识必须始终能从 vault markdown 中恢复出来。

## 产品形态

- 单人私有工作区，通过隐藏的 owner 登录入口访问。
- 登录后进入 Ask-first 研究工作台。
- AI 可以建议新建或补丁 wiki，但不会静默改写正式知识。
- 每一条被接受的 claim 都必须保留回溯到 raw 来源的证据链。

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
