# MVP 路线图

## 总目标

把 Inkvault 做成一个围绕 `raw -> ingest -> wiki -> ask` 运转的私有研究工作台 MVP。

## Phase 0：文档与产品模型

- 完成重定位文档
- 固定私有研究工作台结构

## Phase 1：私有入口与主路径骨架

- 隐藏登录入口
- `/` 到 `/login` / `/app` 的会话跳转逻辑
- `问答 / 资料 / 审阅 / 知识库` 主导航

## Phase 2：研究闭环骨架

- raw 材料导入
- ingest 提案队列
- wiki 页面列表与详情
- Ask 主入口

## Phase 3：真实数据接入

- 真实认证
- 真实 raw 数据
- 真实 ingest 数据
- 真实 wiki 数据
- 真实 Ask 与 writeback 链路

## Phase 4：质量与联调

- 主系统私有访问验证
- raw -> ingest -> wiki 验证
- Ask -> writeback -> ingest 验证

## Phase 5：上线

- 私有入口可访问
- 主系统可登录
- 研究闭环可稳定运行
