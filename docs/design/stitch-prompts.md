# Stitch 提示词

## 通用背景

产品名称：Inkvault  
官方定位：单人私有、vault-first、可追溯的研究记忆系统  
当前实现形态：私有研究工作区

产品模型：

- `raw` 保存原始材料
- `ingest` 承担 AI 提案审阅
- `wiki` 保存正式知识
- `ask` 围绕已有知识继续研究

统一禁用项：

- 不要做成企业 SaaS 管理台
- 不要加入多人协作、审批流、团队成员、消息中心
- 不要做成公开官网或内容发布首页
- 不要引入 plans、publish、settings 作为主叙事

## 1. 登录页 `/login`

请为 Inkvault 设计隐藏登录页。

页面目标：

- 只服务主人进入系统
- 显得私有、克制、可信

必须模块：

- 品牌信息
- 登录表单
- 错误反馈

## 2. 问答 `/app`

请为 Inkvault 设计登录后看到的首页，它必须是研究型问答入口。

页面目标：

- 让用户立刻开始提问
- 看见引用来源和知识缺口
- 理解可以继续追问和沉淀到知识库

必须模块：

- 主输入区
- 连续回答区
- 来源摘要
- 知识缺口
- 沉淀动作

视觉关键词：

- 研究
- 可信
- 连续思考
- 不像传统 dashboard

## 3. 资料 `/app/raw`

请为 Inkvault 设计“资料”页面。

页面目标：

- 展示原始材料入口
- 强调所有知识都从 raw 开始

必须模块：

- 导入网页
- 导入文本
- 导入 PDF
- 来源列表
- vault 规则说明

## 4. 审阅 `/app/ingest`

请为 Inkvault 设计“审阅”页面。

页面目标：

- 展示 AI 提案等待人工确认
- 让用户一眼看懂提案影响哪个知识主题

必须模块：

- 提案列表
- topic 决策
- claims
- evidence
- accept / reject 动作

## 5. 知识库 `/app/wiki`

请为 Inkvault 设计“知识库”页面。

页面目标：

- 展示已经确认沉淀的知识页
- 强调它们是长期可复用记忆

必须模块：

- 标题
- 摘要
- 来源数
- 开放问题数
- 详情入口

## 6. 知识页详情 `/app/wiki/[id]`

请为 Inkvault 设计单个知识页详情。

页面目标：

- 让用户理解一页 wiki 由什么构成
- 清晰展示 understanding、claims、questions、sources

必须模块：

- 标题
- current understanding
- key claims
- open questions
- sources
