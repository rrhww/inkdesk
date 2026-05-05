# Inkvault MVP 后端完成门设计

## 1. 目标

在不扩大产品范围的前提下，把 Inkvault 现有 `server/` 收口为一个可支持本地演示的 MVP 后端，并为下一阶段 agent 层开发准备稳定的后端消费边界。

这轮工作的核心不是继续扩新模块，而是把已经存在的后端能力固定成一个明确、可验证、可交接的完成态。

## 2. 当前基线

截至 `2026-04-30`，后端已经具备以下主体能力：

- owner 登录、登出、会话校验
- `GET /api/admin/home` 首页聚合接口
- 知识资产树、详情、创建、编辑、发布、撤回
- 计划列表、创建、更新
- 搜索召回
- 设置读取与更新
- 公开文章列表与详情
- Flyway 迁移、本地 seed、H2 测试环境

当前 `server/` 全量测试已通过，说明后端主体能力已经存在；本轮要解决的是“完成门”而不是“从零建设”。

## 3. 范围

### 3.1 纳入本轮

- 认证与 owner 会话链路
- `home` 聚合接口
- 知识资产读写与发布链路
- 计划读写
- 搜索召回
- 设置
- 公开文章读取
- Flyway 迁移、seed、本地 profile、测试与后端文档

### 3.2 不纳入本轮

- 多用户与权限模型扩展
- 附件上传、MinIO 真实文件链路
- 向量检索、embedding、外部搜索服务
- 真实 agent 编排、异步任务执行器、工具调用总线
- 生产级部署、监控、审计、运维体系

## 4. 设计

### 4.1 完成门定义

当以下条件同时成立时，后端才算“完成，可进入 agent 层”：

- 当前 MVP 主线所需接口都有稳定的请求/响应边界
- 实现、README、架构文档与路线文档不互相冲突
- 本地 profile 能稳定启动并自动准备演示数据
- 测试覆盖能证明关键主线可用
- 下一阶段 agent 会消费的读模型已经固定，不需要在 agent 开发中倒逼后端返工

### 4.2 面向 MVP 的后端边界

本地可演示 MVP 的后端边界固定为：

- 认证：`POST /api/auth/login`、`POST /api/auth/logout`、`GET /api/auth/me`
- 首页：`GET /api/admin/home`
- 知识资产：`GET /api/admin/notes/tree`、`GET /api/admin/notes/{id}`、`POST /api/admin/notes`、`PATCH /api/admin/notes/{id}`
- 发布：`POST /api/admin/notes/{id}/publish`、`POST /api/admin/notes/{id}/unpublish`
- 计划：`GET /api/admin/plans`、`POST /api/admin/plans`、`PATCH /api/admin/plans/{id}`
- 搜索：`GET /api/admin/search`
- 设置：`GET /api/admin/settings`、`PATCH /api/admin/settings`
- 公开输出：`GET /api/public/articles`、`GET /api/public/articles/{slug}`

这组接口之外，不把任何新接口纳入本轮 MVP 完成门。

### 4.3 Agent 层前置边界

下一阶段 agent 层优先消费以下后端入口：

- `GET /api/admin/home`
- `GET /api/admin/search`
- `GET /api/admin/notes/tree`
- `GET /api/admin/notes/{id}`
- `GET /api/admin/plans`

原因是 agent 第一阶段需要的是“上下文读取、知识回看、计划聚焦、召回入口”，而不是新的写模型或异步执行系统。

本轮后端需要为这些入口保证：

- 返回结构稳定
- 空状态受控
- 本地 seed 数据可支撑 demo
- 未命中或关联缺失时返回受控错误，而不是 500

### 4.4 执行工作流

本轮后端完成度收口按四个工作流推进：

#### 4.4.1 接口与文档审计

- 逐条核对 README、`docs/architecture/api-draft.md`、`docs/delivery/mvp-roadmap.md` 与实际控制器
- 标记文档漂移、命名漂移、完成状态漂移
- 只修与 MVP 演示和 agent 接入有关的漂移，不做大规模重命名

#### 4.4.2 本地运行与数据准备审计

- 核对 Flyway 迁移是否覆盖当前模型
- 核对 local seed 是否能准备 owner、知识、计划、设置等演示数据
- 核对 README 的启动步骤是否足以让开发者独立起服

#### 4.4.3 缺口修补

- 若发现缺少测试保护的 MVP 主线接口，补最小测试
- 若发现接口行为与文档或演示目标不一致，补最小实现
- 若发现错误处理、空状态、seed、迁移存在阻塞 demo 的缺口，优先修补这些问题

#### 4.4.4 交付封板

- 统一更新后端文档
- 跑后端完整验证
- 把当前后端正式定义为“可切入 agent 层”的稳定基线

### 4.5 约束

- 不因为“既然已经在改后端”就顺手扩领域模型
- 不为未来 production 预埋复杂基础设施
- 不在本轮引入真实 LLM、队列、调度器或 tool runtime
- 所有修补必须服务于 MVP 本地演示主线或 agent 首轮读取需求

## 5. 验收标准

- `server` 全量测试通过
- 本地 profile 可以稳定启动
- README 与实际启动方式一致
- 文档声明的 MVP 后端能力与代码实现一致
- 支撑主系统演示的核心接口全部可用
- 支撑 agent 第一阶段读取的接口边界明确且稳定

## 6. 结果定义

本轮完成后，Inkvault 后端进入如下状态：

- 作为本地可演示 MVP，后端能力完整可用
- 作为 agent 层前置地基，后端读模型稳定可消费
- 后续开发重点从“补后端主体能力”切换为“围绕 agent 工作流组织现有能力”
