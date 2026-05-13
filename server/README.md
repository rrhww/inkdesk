# Server

Inkvault 的 Python 主后端，当前服务于单人私有、Vault-first 的研究工作台。

## 当前能力

- `Python 3.12+ / FastAPI`
- 内嵌 `LangGraph` runtime（Ask / Compile）
- `SQLAlchemy + PostgreSQL`
- `health` 与 `actuator/health`
- 真实 owner 登录 / 登出 / 会话校验
- 研究工作区聚合接口
- raw / ingest / wiki / Ask 研究接口
- `INKVAULT_VAULT_ROOT` 可配置 vault 根目录，默认 `./inkvault-vault`
- 启动和请求时确保 vault 中存在 `raw/`、`wiki/`、`AGENTS.md`
- legacy note 迁移材料自动导入为 raw source，用于迁移期研究编译
- dashboard 请求会轻量 re-index `raw/*.md` 与 `wiki/*.md`，DB 缺索引时可从 vault frontmatter 重建 source/wiki/claim 链接

## 当前产品边界

- 单人私有部署模型
- 只提供私有研究工作流接口
- AI 只能提交可审阅提案，不能静默改写正式知识
- Vault markdown 是长期真相，DB 只做索引、队列和缓存

## 本地运行

推荐直接复用仓库根目录的基础设施模板：

1. 在项目根目录复制 `infra/.env.example` 为 `infra/.env`
2. 设置一个足够长的 `INKVAULT_AUTH_SECRET`
3. 启动 `PostgreSQL + MinIO`

```powershell
docker compose --env-file ..\infra\.env -f ..\infra\docker-compose.yml up -d postgres minio
```

4. 安装依赖并启动后端

```powershell
python -m pip install -e .[dev]
python -m uvicorn inkvault_server.main:app --host 0.0.0.0 --port 8080
```

当数据库为空时，后端会自动回补：

- owner 邮箱：`owner@inkvault.local`
- owner 密码：`inkvault-owner`
- 示例工作区与 legacy note 数据

也可以直接通过环境变量覆盖：

```powershell
$env:INKVAULT_DB_URL='postgresql+psycopg://inkvault:inkvault@localhost:5432/inkvault'
$env:INKVAULT_AUTH_SECRET='replace-with-a-long-random-secret'
$env:INKVAULT_AUTH_SESSION_DURATION='PT8H'
$env:INKVAULT_VAULT_ROOT='C:\path\to\inkvault-vault'
$env:INKVAULT_AGENT_RUNTIME='langgraph'
$env:INKVAULT_AGENT_PROVIDER_PROFILE='openai'
$env:OPENAI_API_KEY='sk-...'
$env:INKVAULT_AGENT_MODEL='gpt-4.1-mini'
$env:INKVAULT_AGENT_CONNECT_TIMEOUT_SECONDS='2'
$env:INKVAULT_AGENT_READ_TIMEOUT_SECONDS='20'
$env:INKVAULT_ENABLE_WEB_ASSIST='true'
python -m uvicorn inkvault_server.main:app --host 0.0.0.0 --port 8080
```

DeepSeek 作为正式 provider profile 时，可以直接这样配：

```powershell
$env:INKVAULT_AGENT_PROVIDER_PROFILE='deepseek'
$env:DEEPSEEK_API_KEY='sk-...'
$env:INKVAULT_AGENT_MODEL='deepseek-v4-flash'
python -m uvicorn inkvault_server.main:app --host 0.0.0.0 --port 8080
```

如果未设置对应 profile 的 API key，或者显式把 `INKVAULT_AGENT_RUNTIME` 设为 `deterministic`，Ask / Compile 会继续走 deterministic fallback，不会尝试调用真实 LLM。

当前 provider profile 约定：

- `openai`：默认走 `https://api.openai.com/v1`，structured output 使用 `json_schema`
- `deepseek`：默认走 `https://api.deepseek.com`，structured output 使用 `json_mode`
- `openai_compatible` / `custom`：允许通过 `INKVAULT_AGENT_BASE_URL` 与 `INKVAULT_AGENT_API_KEY` 显式覆盖

如果 `INKVAULT_ENABLE_WEB_ASSIST='true'`，`vault_plus_web` 模式会在 Ask 初答仍有知识缺口时显式联网补料；如果设为 `false`，Ask 会停留在纯 vault 回答，不会请求外部搜索结果。

测试：

```powershell
python -m pytest
```

## 当前接口

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /actuator/health`
- `GET /api/admin/home`
- `GET /api/raw`
- `POST /api/raw`
- `GET /api/ingest`
- `POST /api/ingest/{id}/accept`
- `POST /api/ingest/{id}/reject`
- `GET /api/wiki`
- `GET /api/wiki/{id}`
- `POST /api/ask`
- `POST /api/ask/{id}/writeback`

## 当前边界

- 会话 Cookie 固定为 `inkvault_owner_session`
- 登录标识固定为邮箱
- legacy note 持久层仍保留，用于迁移到 raw source
- `raw/` 与 `wiki/` markdown 文件由后端写入，路径写入有 vault root 防逃逸校验
- Ask / Compile 已内嵌到主后端；当模型不可用时会回退到 deterministic provider
