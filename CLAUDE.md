# CLAUDE.md

## 提交规范

本项目使用 Conventional Commits 规范编写 commit message。

格式：

```
<type>(<scope>): <description>
```

常用 type：

| type | 说明 |
|------|------|
| feat | 新功能 |
| fix | 修复 bug |
| docs | 文档变更 |
| refactor | 重构（不改变功能） |
| test | 测试相关 |
| chore | 构建/工具/依赖 |
| style | 代码格式（不影响逻辑） |

scope 为可选的变更范围，description 使用中文。

示例：

```
feat(mcp): 新增 context_pack 工具
fix(api): 处理用户查询的空响应
docs(readme): 更新产品定位说明
refactor(auth): 简化 token 校验逻辑
```

## 结对编程指导规范

当用户要求"指导实现"或"手把手指导"时，每一步必须按以下结构展开：

### 每步必须包含四层

1. **做什么**（具体操作：打开哪个文件、加什么代码、怎么改）
2. **为什么这样做**（理由：设计原则、架构决策、设计文档的哪一条要求）
3. **原理是什么**（机制解释：这段代码如何运作、为什么有效、边界条件是什么。必须包含语法解释——每个新引入的 TS/JS 语法、React Hook、Next.js API、Tailwind 变体、Python 标准库调用、FastAPI 装饰器等都要说明其语义和作用，不允许假设用户已经知道某个语法点）
4. **具体做了什么**（改动摘要：改了几个文件、每个文件改了什么、几行代码）

### 禁止行为

- 不得只说"加这段代码"而不解释原理
- 不得跳过设计理由直接跳到操作
- 不得用"显然""当然""毫无疑问"替代推理过程
- 不得绕过架构决策（为什么放这个文件不放那个文件、为什么用这种方法不用那种方法）

### 节奏

- 每步只做 1-2 个小改动
- 每步结束必须等待用户确认并告知结果后再进行下一步
- 改动文件前先确认用户已打开正确的文件

### 原理层必须包含的语法与实现解释

指导中说"原理"时，必须解释代码中每个关键语法的语义，不得假设用户已知：

- **TypeScript/JavaScript**：泛型参数做什么、`useState` 初始值与类型推断的关系、`Promise<T>` 如何约束返回值、`??` vs `||` 的差异、短路求值在 JSX 中的行为
- **React/Next.js**：`"use client"` 指令的边界效应（哪些依赖会被客户端打包）、`useState`/`useEffect` 的调度模型、`router.refresh()` vs `router.push()` 的区别、Server Component 与 Client Component 的数据传递限制
- **Tailwind CSS**：每个变体前缀（`hover:`、`disabled:`、`lg:`）对应的 CSS 伪类/媒体查询、任意值语法 `text-[11px]` 的生成方式
- **Python**：`str | None` 联合类型的语义（Python 3.10+）、`@dataclass(frozen=True)` 的不可变性保证、`Path.mkdir(parents=True, exist_ok=True)` 中两个参数各自的作用、`Annotated[Type, Depends(callable)]` 如何被 FastAPI 依赖注入系统解析
