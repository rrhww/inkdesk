# 详细开发计划

## 目标

将 Inkvault 推进到一个可稳定使用的私有研究工作台 MVP。

## 项目边界

- 产品形态：单人私有研究系统
- 主闭环：`raw -> ingest -> wiki -> ask`
- 技术栈：`Next.js + FastAPI + PostgreSQL + Vault Markdown + MinIO`

## 阶段顺序

### Phase 1：产品定义与主路径收束

- 重写核心文档
- 收束主路径命名
- 清理旧路线叙事

### Phase 2：研究工作区成型

- 完成 `/login`
- 完成 `问答`
- 完成 `资料`
- 完成 `审阅`
- 完成 `知识库`

### Phase 3：真实数据接入

- 接入真实认证
- 接入 raw / ingest / wiki / ask 接口
- 用真实研究数据替换 mock fallback 主路径

### Phase 4：质量收口

- 测试私有访问拦截
- 测试 raw -> ingest -> wiki 闭环
- 测试 Ask 与 writeback 闭环

### Phase 5：部署与上线

- 部署私有前端与主后端
- 完成 vault、数据库、对象存储和反向代理配置
- 完成备份与恢复演练

## 当前开发优先级

1. 统一产品定义
2. Ask 主入口
3. Raw 导入与来源管理
4. Ingest 审阅
5. Wiki 浏览与详情
6. Ask writeback 闭环
