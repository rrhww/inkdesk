# Infra

这里用于放置 Docker Compose、Nginx、部署配置和环境模板。

## 本地基础设施

当前默认提供两项本地依赖：

- `PostgreSQL + pgvector`：主业务数据与检索 chunk 向量扩展
- `MinIO`：本地对象存储占位，先把未来生产形态的接口留出来

## 启动方式

1. 复制 `infra/.env.example` 为 `infra/.env`
2. 启动基础设施：

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

3. 查看状态：

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml ps
```

4. 停止并保留数据卷：

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml down
```

## 默认端口

- PostgreSQL：`5432`
- MinIO API：`9000`
- MinIO Console：`9001`

## 检索相关环境变量

- `INKDESK_EMBEDDING_PROVIDER_PROFILE`
- `INKDESK_EMBEDDING_MODEL`
- `INKDESK_EMBEDDING_API_KEY`
- `INKDESK_EMBEDDING_BASE_URL`

应用启动时会自动执行 `CREATE EXTENSION IF NOT EXISTS vector`。如果没有配置 embedding provider，Ask 会回落到 lexical retrieval；配置后会进入 hybrid retrieval。
