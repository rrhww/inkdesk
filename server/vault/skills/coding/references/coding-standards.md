# coding-standards

coding 执行代码实现时的代码规范参照。这是 Inkdesk 项目内的约定——当项目已有 linter/formatter 配置时，以项目配置为准。

## 通用原则

### 明确性
- 代码的意图应能从命名中直接理解——不依赖注释解释「做什么」
- 变量/函数名优先使用领域术语而非技术黑话

### 最小化
- 每次 commit 只做一件事
- 不顺手重构无关代码
- 不引入未在方案中声明的依赖

### 可追溯
- 每个代码变更可关联到 tech-solution 中的设计决策
- 偏差记录在 coding-log 中

## 具体约定

### 函数设计
- 不超过 30 行——超过则考虑拆分
- 返回值类型显式声明（Python 用 type hints）
- 副作用函数在命名中体现（如 `fetch_and_cache`）

### 错误处理
- 不要空 catch / except pass
- 异常消息包含足够的上下文用于排查（输入值、操作名称）
- 不在内部吞掉不可恢复的错误

### 安全
- 不在代码中硬编码密钥、token、连接字符串
- 用户输入不做裸拼接（SQL / shell / HTML）
- 涉及 schema change 或 API breaking change 必须获得用户确认

## 违反处理

- 与方案一致性的偏差：记录到 coding-log
- 安全违规：停止执行
- 风格违规：标记但不阻塞

## 不做

- 不替代项目的 linter/formatter 配置
- 不在实现阶段重新讨论方案设计
