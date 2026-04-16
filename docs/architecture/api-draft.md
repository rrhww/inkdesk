# API 草图

## 目标

为当前“主系统 + 输出层”MVP 固定一版接口边界，支持隐藏登录、主系统、任务计划与公开输出层。

## 一、认证接口

### `POST /api/auth/login`

- 目标：主人登录
- 用途：`/login`

### `POST /api/auth/logout`

- 目标：退出主系统
- 用途：主系统顶部退出操作

### `GET /api/auth/me`

- 目标：获取当前主人信息
- 用途：主系统初始化

## 二、Agent / 首页接口

### `GET /api/admin/home`

- 目标：聚合主系统首页所需上下文
- 返回：
  - 工作台摘要
  - 焦点计划
  - 焦点知识
  - Agent 建议
  - 快速动作
  - 最近笔记
  - 待发布内容

## 三、笔记接口

### `GET /api/admin/notes/tree`

- 目标：获取笔记与知识库结构

### `POST /api/admin/notes`

- 目标：创建知识资产

### `PATCH /api/admin/notes/{id}`

- 目标：更新知识资产

### `POST /api/admin/notes/{id}/snapshot`

- 目标：创建快照

## 四、任务 / 计划接口

### `GET /api/admin/plans`

- 目标：获取任务与计划列表

### `POST /api/admin/plans`

- 目标：创建任务 / 计划

### `PATCH /api/admin/plans/{id}`

- 目标：更新状态、标题或摘要

## 五、检索接口

### `GET /api/admin/search`

- 目标：跨知识资产做关键词召回

## 六、发布接口

### `POST /api/admin/notes/{id}/publish`

- 目标：将笔记发布到公开输出层

### `POST /api/admin/notes/{id}/unpublish`

- 目标：从公开输出层撤回

## 七、公开输出接口

### `GET /api/public/articles`

- 目标：获取公开输出首页文章列表

### `GET /api/public/articles/{slug}`

- 目标：获取公开文章详情

## 备注

- 当前不做访客登录
- 当前不做公开全文搜索
- 当前不做复杂 Agent 调用接口，首页 Agent 内容先由规则模板聚合接口承接
