# Inkdesk 搜索与计划只读联调设计

## 1. 目标

在已经完成知识资产只读联调的基础上，继续接通主系统里剩余最关键的两条读链路：

- `/app/search` 的真实知识召回
- `/app/plans` 的真实计划执行视图

这轮仍然只做只读，不引入计划写接口、复杂调度或真实 Agent 聚合。

## 2. 范围

- 新增后端 `GET /api/admin/search`
- 新增后端 `GET /api/admin/plans`
- 为后端补最小 `plans` 与 `plan_notes` 表
- 本地和测试环境补计划 seed
- 前端 `search` / `plans` 数据层优先走后端，未配置 API 地址时继续回退 mock

## 3. 设计

### 3.1 搜索

- 搜索基于现有知识表实现，不新增独立搜索引擎
- 搜索范围包括标题、标签、摘要、文件夹名和 Markdown 正文
- 返回结果保持面向前端的“召回结果”结构：
  - `note`
  - `score`
  - `hitLabels`
  - `matchedTerms`
- 查询参数支持：
  - `q`
  - `visibility`
  - `tag`
  - `folder`

### 3.2 计划

- 新增最小计划读模型：
  - `plans`
  - `plan_notes`
- `plans` 只存当前执行台所需核心字段：
  - 标题、摘要、状态、时间范围、优先级
  - 焦点标签、下一步动作、按钮跳转
  - Agent 提示、最近更新时间
- 计划与知识资产关系通过 `plan_notes` 管理
- 前端继续允许通过现有 fixture 补 `relatedTagIds`、`milestones` 等非核心展示字段，避免本轮过度扩表

### 3.3 前端适配

- `web/lib/search.ts` 改为异步，可请求后端搜索接口
- `web/lib/plans.ts` 改为异步，获取计划列表并在前端组装 `PlanWorkbenchData`
- `/app/search` 与 `/app/plans` 服务器组件转发 owner cookie 到 admin 接口
- 搜索建议和部分非关键文案仍可复用现有 mock 补充数据

## 4. 不做的事

- 不实现 `POST/PATCH /api/admin/plans`
- 不实现搜索索引、embedding 或外部搜索服务
- 不实现首页聚合接口 `/api/admin/home`
- 不把整个计划领域一次性扩成完整写模型

## 5. 验收标准

- `/api/admin/search` 可按关键词返回排序后的知识召回结果
- `/api/admin/plans` 可返回执行台所需的计划列表和关联笔记 ID
- `/app/search` 在配置后端地址时读取真实搜索结果
- `/app/plans` 在配置后端地址时读取真实计划和真实关联知识
- 未配置后端地址时，搜索和计划页面继续可用
