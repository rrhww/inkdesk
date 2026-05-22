# 用户故事

## 1. owner 登录与私有入口

### 1.1 进入私有工作区

作为 owner，我希望通过 `/login` 登录并进入私有系统，这样我的研究资料不会暴露给访客。

验收标准：

- 访问 `/login` 可进入登录页
- 登录成功后进入 `/app`
- 未登录访问 `/app/*` 会被拦回 `/login`
- 已登录访问 `/` 会自动进入 `/app`

## 2. raw 原始材料导入

### 2.1 导入网页、PDF 与文本

作为 owner，我希望把网页、PDF 和手动文本统一导入到 `raw/`，这样研究材料先有稳定落点，再决定如何沉淀。

验收标准：

- `/app/raw` 可访问
- 支持网页导入
- 支持 PDF 上传导入
- 支持文本来源创建
- 导入后来源能看到 locator、excerpt 和 vault path

## 3. ingest 提案审阅

### 3.1 审阅 AI 生成的知识提案

作为 owner，我希望 AI 先生成待审阅提案，而不是直接改 wiki，这样我能控制正式知识的边界。

验收标准：

- `/app/ingest` 可访问
- 可以查看提案解释、归属 topic 和证据来源
- 可以接受或拒绝提案
- 拒绝提案不会写 wiki

## 4. wiki 知识沉淀

### 4.1 维护长期知识页

作为 owner，我希望把被接受的研究结论沉淀到 `wiki/`，这样我可以长期复用这些知识，而不是每次重新看原始材料。

验收标准：

- `/app/wiki` 可访问
- `/app/wiki/[id]` 可查看单页详情
- 页面展示 current understanding、key claims、open questions、sources
- wiki 内容可回溯到 raw 来源

## 5. ask 研究问答

### 5.1 在已有知识上继续追问

作为 owner，我希望先基于已有 wiki 和 raw 提问，再决定是否补充更多资料，这样系统更像研究助手，而不是一次性聊天机器人。

验收标准：

- `/app/ask` 可访问
- 回答包含引用来源
- 可以看到知识缺口和 follow-up questions
- 支持 `vault` 和 `vault_plus_web` 两种模式

### 5.2 把有价值的回答变成提案

作为 owner，我希望把 Ask 的结果转成新的 ingest 提案，这样好的回答可以进入正式沉淀流程，但不会被自动写进 wiki。

验收标准：

- Ask 结果可以触发 writeback
- writeback 只会创建 review item
- 如果用了外部网页补料，写回前要先保存到 raw
