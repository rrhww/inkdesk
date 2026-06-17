# 《AI研发自动化：Wiki知识库+技能包》项目映射

> 原文归档见 [AI研发自动化：Wiki知识库+技能包-原文存档.txt](./AI研发自动化：Wiki知识库+技能包-原文存档.txt)。
>
> 本文档用于把文章方法论映射到 Inkdesk 当前产品和开发计划，避免后续讨论只记结论、不记来源。

## 为什么归档到项目里

- 这是 Inkdesk 当前产品定位与开发顺序的直接来源之一。
- 现有路线图、开发计划、MCP 方向和评测思路都已经明显受这篇文章影响。
- 把原文和映射一起放进仓库，可以减少“口头转述失真”和“计划漂移”。

## 文章方法论的核心骨架

文章的主线可以压缩成下面这条链路：

```text
Sources -> LLM-Wiki -> Schema -> Skills -> Evaluation -> Harness
```

文章的终局目标不是“做一个知识库”，而是：

```text
用户提供 PRD
  -> 系统自动理解需求
  -> 生成技术方案
  -> 完成技术评审
  -> 执行 coding
  -> 准备测试与修复自动化测试
  -> 问题排查与复盘沉淀
  -> 进入下一轮迭代
```

也就是 AI 研发流程全自动化。LLM-Wiki、Skill 包、评测系统和 Harness 都是为了支撑这个终局。

配套的三个高频操作是：

```text
Ingest（摄入）
Query（查询）
Lint（巡检）
```

同时文章强调三件事：

- 知识要在写入时编译，而不是只在查询时临时拼接
- Skill 必须有边界、Hard Gates、清晰输出和下游衔接
- 自动化能力必须建立在评测、门禁和版本化之上

## Inkdesk 的直接映射

| 文章概念 | Inkdesk 对应 |
| --- | --- |
| Sources | `raw/` 原始材料、导入接口、来源索引 |
| LLM-Wiki | `wiki/` 页面、Ask 引用、审阅后写回 |
| Schema | `schema/` 维护规则、页面模板、引用规则 |
| Query | `/app/ask` Context Ask、`/api/ask`、briefing |
| Ingest | `raw -> ingest -> review -> wiki patch` |
| Lint | Wiki Health、结构检查、断链/孤页/缺来源扫描 |
| Skills | `skills/` 文件、Skill Workbench、路由 Skill |
| Evaluation | `evals/`、golden tasks、LLM judge、版本对比 |
| Harness | 受控 run 编排、gates、rollback、外部 Agent 接入、PRD 到交付的流程导演 |

## 对当前开发顺序的启发

文章给的是长期顺序，不是要求所有能力都必须线性串行完成。映射到 Inkdesk 后，当前更合适的顺序是：

```text
1. 做稳 Sources -> LLM-Wiki
   raw -> ingest -> wiki -> ask -> deposit -> review

2. 暴露一个薄 MCP 接入层
   context_pack / search / deposit / health_check

3. 把 schema 初始化和维护协议落到 vault

4. 补强后台异步编译流水线与审阅体验

5. 再进入 Skills / Evaluation / Harness 的完整形态
```

这里的关键判断是：

- Inkdesk 的终局仍然是 AI 研发流程全自动化，而不是停在知识库或问答产品。
- 现在做的 MCP Server 是“阶段一能力的外部入口”，不是文章终局意义上的 Harness。
- 只要 MCP 的写入仍然走 review-first，它就不会破坏文章要求的知识边界。
- 真正高自治的多步骤编排，仍然要等 Evaluation 与 run 记录成熟后再做。

## 对计划文档的具体修正

### 1. Ask deposit 仍然是当前第一优先级

文章强调 Query 的价值不止是答题，还要把高价值结论写回 Wiki。  
所以 Inkdesk 当前最重要的不是多做页面，而是把：

```text
ask answer -> deposit -> ingest proposal -> review -> wiki patch
```

这条链路打磨顺。

### 2. MCP Server 应前置为受控接入层

文章第 3 节的多平台使用方式，以及第 7.2 节“把工具收拢到一个 MCP 服务”的经验，支持 Inkdesk 现在先做：

- `context_pack`
- `search`
- `deposit`
- `health_check`

但边界必须明确：

- 不直接改写正式 wiki
- 不绕过 ingest / review
- 不把它描述成完整 Agent Harness

### 3. Schema 仍然是必要的下一层

文章反复证明：知识库如果没有 agent-facing 维护规则，后续内容越多越容易漂。  
所以 MCP 前置不代表 Schema 可以取消，反而意味着：

- MCP v1 只暴露当前已有稳定能力
- Schema 作为下一层，把维护规则文件化

### 4. Evaluation 不应拖到太晚才开始思考

即使完整评测中心可以晚点做，下面这些准备应该提前：

- Golden Tasks 候选任务来源
- Wiki Health 指标口径
- 盲评与双模型评分原则
- run / proposal / accepted wiki 的版本边界

## 当前可执行的文档结论

如果只看接下来一段时间，项目计划应收敛为：

1. 将 `/app` 从 Ask-first 修正为 Dev Run Console，入口面向 PRD / bug / 改造任务。
2. 保留 `/app/ask`，但定位为 Context Ask，服务当前研发任务的上下文查询。
3. 完成 Ask / Context Ask deposit 的整条回答与选中片段沉淀。
4. 增加基础 Wiki Health 检查与健康入口。
5. 提供一个薄 MCP Server，服务外部 Agent 的 context / search / deposit / health。
6. 落地 vault schema 初始化与维护规则。
7. 在此基础上继续建设异步编译流水线、Skill Workbench、Evaluation 和 Harness。

UI 决策也应服从这个方向：

```text
首页不是问答框。
首页是研发任务运行台。
Ask 是任务执行过程中的上下文查询工具。
```

## 备注

- 原文里不少实现细节来自作者所在团队环境，例如 Obsidian、qmd、企业内部工具和多知识库协作；Inkdesk 吸收的是方法论骨架，不照搬具体工具拼装。
- Inkdesk 的产品化目标意味着：Web 审阅、文件真相层、MCP 接入和评测门禁要一起成立，而不只是做一套聊天里的 Skill 集合。
