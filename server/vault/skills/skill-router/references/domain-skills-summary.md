# domain-skills-summary

skill-router 匹配领域 Skill 时的参考摘要。每个 Skill 概述其触发条件和不触发条件，供路由阶段做快速候选判断。

## 知识管理链

### ingest-source
- **触发**：用户上传文档、导入资料、要求摄入新知识源
- **不触发**：纯查重、不可解析格式
- **下游**：patch-wiki-page

### answer-from-wiki
- **触发**：对已有知识库内容提问、查询、解释
- **不触发**：创作全新内容、执行代码变更、wiki 为空
- **下游**：deposit-answer

### deposit-answer
- **触发**：回答中有可被 wiki 收录的结构化知识时
- **不触发**：纯一次性对话、无长期保留价值
- **下游**：patch-wiki-page

### patch-wiki-page
- **触发**：上游产出了针对特定页面且已审阅的变更提案
- **不触发**：无目标页面或变更内容为空
- **下游**：无

### run-wiki-health
- **触发**：用户询问知识库质量或需要健康报告
- **不触发**：空库
- **下游**：patch-wiki-page

### extract-insight
- **触发**：对话/文档中包含值得存入 wiki 的结构化知识
- **不触发**：纯闲聊
- **下游**：patch-wiki-page

## 研发自动化链

### tech-solution
- **触发**：有明确需求且 KB 已就绪
- **不触发**：无明确需求、KB 空白无法提供上下文
- **下游**：tech-review

### tech-review
- **触发**：存在待审技术方案
- **不触发**：方案为草稿大纲
- **下游**：coding

### coding
- **触发**：tech-review 通过且用户确认进入实现
- **不触发**：方案未确认、有未解决阻塞
- **下游**：test-prep

### test-prep
- **触发**：coding 完成后准备进入测试
- **不触发**：无代码变更或变更范围未明确
- **下游**：test-fix

### test-fix
- **触发**：有真实失败信号（日志、报错、CI 失败记录）
- **不触发**：无失败信号、猜测式修复、测试环境未就绪
- **核心安全约束**：必须有可复现的失败证据才能启动
- **下游**：problem-solve、deposit-answer

### problem-solve
- **触发**：有异常现象需要排查
- **不触发**：现象为空、仅咨询性问题
- **下游**：deposit-answer
