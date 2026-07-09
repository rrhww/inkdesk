# Dev Run 阶段执行入口设计

> **状态：已实施** | 日期：2026-07-09 | 作者：Codex
>
> 实施完成日期：2026-07-09 | 配套计划：../plans/2026-07-09-dev-run-stage-actions-plan.md

## 1. 背景

### 1.1 当前状态

Dev Run Console 已实现为 6 阶段状态机（`context → solution → review → coding → testing → deposit`），支持：

- 创建 Dev Run（PRD / Bug / 改造）
- 阶段轨道可视化
- 事件记录
- 手动"批准推进"和"完成任务"

**缺失的核心环节**：没有任何东西自动执行各阶段的工作。Dev Run 是纯追踪系统，不是执行系统。

### 1.2 问题

用户期望的流程是：

```text
投入 PRD → Inkdesk 生成上下文 → 生成方案 → 调用 Claude Code 执行 coding
```

但当前 Dev Run 的 `context` 阶段不会生成 Context Pack，`coding` 阶段不会调用 Claude Code。用户创建任务后看到的是 6 个 pending 圆点，没有任何可操作的执行入口。

### 1.3 设计目标

采用**路线 B：半自动执行入口**。每个阶段提供明确的用户操作按钮，执行该阶段的工作，产出阶段产物，然后等待用户确认推进。

不追求全自动 Harness，先让完整闭环跑通。

## 2. 已有可复用能力

| 能力 | 后端位置 | API | 说明 |
|------|----------|-----|------|
| Context Pack | `mcp_services.py` → `ContextPackService` | MCP 内部调用 | 已能根据 run_id 组装上下文包 |
| Vault 搜索 | `mcp_services.py` → `VaultSearchService` | MCP 内部调用 | 全文搜索 wiki/raw |
| Context Ask | `research.py` → `ResearchWorkspaceService.ask()` | `POST /api/ask` | 已支持 runId 关联 |
| Deposit | `deposit_service.py` → `DepositService` | `POST /api/deposits` | 已支持 runId + stage |
| 事件记录 | `run_service.py` → `RunService.add_event()` | `POST /api/runs/{id}/events` | 已支持 stage + payload |
| 阶段推进 | `run_service.py` → `RunService.advance_run()` | `POST /api/runs/{id}/advance` | approve / complete |

**关键发现**：后端基础设施已经齐备。缺的是把 Dev Run 详情页的 UI 操作和这些后端能力连起来。

## 3. 设计方案

### 3.1 总体流程

```text
用户创建 Dev Run
  → context 阶段：点击"生成上下文" → 调 ContextPackService → 产出上下文摘要 → awaiting_review
  → 用户确认 → 进入 solution 阶段
  → solution 阶段：点击"生成方案" → 调 Ask API 让 LLM 生成方案草案 → awaiting_review
  → 用户确认 → 进入 review 阶段
  → review 阶段：显示方案审阅清单 → 用户标记通过/需修改 → awaiting_review
  → 用户确认 → 进入 coding 阶段
  → coding 阶段：显示 Claude Code Briefing（可复制） → 用户在终端执行 → 手动粘贴结果 → awaiting_review
  → 用户确认 → 进入 testing 阶段
  → testing 阶段：显示测试检查清单 → 用户标记测试结果 → awaiting_review
  → 用户确认 → 进入 deposit 阶段
  → deposit 阶段：点击"沉淀关键产出" → 调 Deposit API → awaiting_review
  → 用户确认完成 → run completed
```

### 3.2 每个阶段的具体设计

---

#### 阶段 1：context（上下文）

**用户操作**：点击"生成上下文包"

**后端行为**：
1. 调用 `ContextPackService.build(workspace_id, run_id)` 生成上下文包
2. 将上下文包存为 `stage_output` 事件（`add_event`，stage=context，eventType=context_pack_generated，payload 包含上下文摘要）
3. Run 自动变为 `awaiting_review`

**前端展示**：
- 上下文包摘要卡片：任务类型、目标、关联的 wiki 页面列表、历史 Ask 记录、待审阅项
- 如果上下文不足（wiki 为空），提示用户先去 `/app/ask` 提问或导入 raw 材料
- "生成上下文"按钮（pending 状态时显示）
- 生成后显示摘要 + "确认推进"按钮

**新增 API**：
```
POST /api/runs/{run_id}/context-pack
```
调用 `ContextPackService`，写入事件，返回上下文包。

---

#### 阶段 2：solution（方案）

**用户操作**：点击"生成方案草案"

**后端行为**：
1. 基于 context 阶段产出的上下文包，调用 LLM 生成技术方案草案
2. 方案结构：目标复述、约束识别、实现路径、风险点、测试范围
3. 存为 `stage_output` 事件（stage=solution，eventType=solution_draft_generated，payload 包含方案文本）
4. Run 自动变为 `awaiting_review`

**前端展示**：
- 方案草案卡片（Markdown 渲染）
- 可编辑文本区域（用户可修改方案）
- "重新生成"按钮
- "确认推进"按钮

**新增 API**：
```
POST /api/runs/{run_id}/solution
```
调用 LLM 生成方案，写入事件，返回方案文本。

**实现方式**：
复用现有 LangGraph runtime + `ResearchWorkspaceService` 中已封装的 OpenAI/DeepSeek provider。新建一个轻量的 prompt 模板，不依赖完整 Skill 执行框架。

---

#### 阶段 3：review（审阅）

**用户操作**：查看方案审阅清单，标记通过或需修改

**后端行为**：
1. LLM 基于方案草案生成审阅清单（边界检查、风险确认、依赖确认、测试范围确认）
2. 存为 `stage_output` 事件
3. Run 变为 `awaiting_review`

**前端展示**：
- 审阅清单（每项可勾选"通过" / "需修改"）
- 审阅意见文本区域
- "确认推进"按钮（所有必查项通过后才可点击）

**新增 API**：
```
POST /api/runs/{run_id}/review
```
生成审阅清单，写入事件。

---

#### 阶段 4：coding（编码）

> **产品决策（2026-07-09）**：Inkdesk 直接启动 Claude Code CLI 子进程执行 coding，不采用人工复制 briefing 方案。这是产品的最终形态——Inkdesk 作为控制面，Claude Code 作为执行面，由 Inkdesk 自动拉起。

**用户操作**：
1. 在 coding 阶段点击"启动 Claude Code"
2. 等待 Claude Code 执行完成（前端轮询状态）
3. 查看自动回写的执行结果
4. 确认推进

**后端行为**：
1. 组装 Briefing：任务目标 + 方案 + 审阅意见 + 仓库路径 + 约束
2. 存为 `stage_output` 事件（eventType=coding_briefing_prepared）
3. 启动 Claude Code CLI 子进程，传入 Briefing 作为 prompt
4. 子进程在 `run.repoContext` 指定的仓库目录中运行
5. 捕获子进程 stdout/stderr，解析执行结果
6. 子进程完成后，自动回写结果为事件（eventType=coding_result_submitted，payload 包含执行摘要）
7. Run 自动变为 `awaiting_review`

**子进程调用方式**：
```python
await asyncio.create_subprocess_exec(
    "claude", "-p", briefing, "--output-format", "text",
    cwd=run.repoContext or ".",
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
```

-- 使用 `claude -p`（非交互模式）传入完整 prompt
-- `--output-format text` 获取纯文本输出
-- 通过 `cwd=` 参数指定工作目录为 `run.repoContext`（Claude CLI 无 `--cwd` 参数）
- 设置合理的超时（如 300s），超时后终止子进程并标记 blocked
- 捕获 stdout 作为执行结果
- 捕获 stderr 作为错误信息

:**前端展示**：
- Briefing 预览（只读，展示将传给 Claude Code 的内容）
- "启动 Claude Code"按钮（pending 状态时显示）
- "跳过，手动批准"按钮（pending 状态时显示；当用户未安装/不想调用 CLI 时，写入 `stage_output` 使阶段进入 `awaiting_review`）
- 执行中状态指示器（spinner + "Claude Code 执行中…"）
-- 执行完成后显示结果摘要
-- 如果失败，显示错误信息 + "重试"按钮
-- "确认推进"按钮

**新增 API**：
```
POST /api/runs/{run_id}/coding/execute    # 组装 Briefing + 启动 Claude Code 子进程
GET  /api/runs/{run_id}/coding/status     # 轮询执行状态
```

**Briefing 格式**（Markdown，作为 claude -p 的 prompt）：
```markdown
# Dev Run Coding Briefing

## 任务
{run.title}

## 目标
{run.goal}

## 仓库
{run.repoContext}

## 技术方案
{solution_draft}

## 审阅要点
{review_checklist}

## 约束
- 只修改与目标直接相关的文件
- 不做无关重构
- 遵循现有代码风格和命名约定
- 修改后运行测试确认不破坏已有功能

## 执行完成后
请输出：改了哪些文件、核心逻辑、测试结果。
```

**子进程管理**：
- 在后端维护一个 `subprocess.Task`，存储 run_id → process 映射
- 支持超时终止和手动取消
- 前端通过轮询 `GET /coding/status` 获取执行状态
- 进程结束后自动写入 `coding_result_submitted` 事件

**待解决问题**（实施时确认）：
- Claude Code CLI 是否已安装并登录（检测 `claude` 命令是否存在）
- 非交互模式的输出格式（纯文本 / JSON）
- 长时间执行的超时策略
- 子进程异常终止的清理

---

#### 阶段 5：testing（测试）

:**用户操作**：点击"生成测试清单"，查看并勾选测试项，确认推进

**后端行为**：
1. 读取 coding 阶段的 `coding_result_submitted` 事件结果文本
2. 构建 prompt：任务目标 + coding 产出 → 生成测试检查清单（单元测试、集成测试、边界条件、回归测试）
3. 调用 LLM 或 deterministic fallback 生成清单
4. 写入 `testing_checklist_generated` 事件
5. Run 自动变为 `awaiting_review`

**前端展示**：
- "生成测试清单"按钮（pending 状态时显示）
- 测试检查清单（每项可勾选）
- "重新生成"按钮（awaiting_review 状态时显示）
- "确认推进"按钮（在父页面操作区）

**新增 API**：
```
POST /api/runs/{run_id}/testing
```
生成测试清单，写入事件。

---

#### 阶段 6：deposit（沉淀）

**用户操作**：点击"沉淀关键产出"

**后端行为**：
1. 收集本次 Dev Run 的关键产出（方案、审阅意见、coding 结果、测试结果）
2. 调用 `DepositService.create()` 创建沉淀提案
3. 提案进入 ingest 审阅队列（review-first 原则）
4. 存为 `stage_output` 事件

**前端展示**：
- 沉淀摘要预览（将沉淀什么、关联到哪个 run）
- "沉淀"按钮
- 沉淀成功后显示"完成任务"按钮
- 链接到 `/app/ingest` 查看提案状态

**新增 API**：
```
POST /api/runs/{run_id}/deposit
```
调用 `DepositService`，写入事件。

## 4. API 汇总

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/runs/{run_id}/context-pack` | 生成上下文包 |
| POST | `/api/runs/{run_id}/solution` | 生成方案草案 |
| POST | `/api/runs/{run_id}/review` | 生成审阅清单 |
| POST | `/api/runs/{run_id}/coding/execute` | 组装 Briefing + 启动 Claude Code 子进程 |
| GET | `/api/runs/{run_id}/coding/status` | 轮询 Claude Code 执行状态 |
| POST | `/api/runs/{run_id}/testing` | 生成测试清单 |
| POST | `/api/runs/{run_id}/deposit` | 沉淀关键产出 |

所有 API：
- 调用后通过 `RunService.add_event()` 写入事件
- 自动将 run 状态变为 `awaiting_review`
- 返回更新后的 `DevRunResponse`

## 5. 前端改动

### 5.1 Dev Run 详情页改造

当前 [runs/[id]/page.tsx](file:///e:/dev/projects/inkdesk/web/app/app/runs/[id]/page.tsx) 只有阶段轨道 + 事件记录 + 操作按钮。

改为**阶段工作区**布局：

```text
┌─────────────────────────────────────────────┐
│ ← 返回任务列表                                │
│ [PRD] 测试任务：验证 Dev Run 流程              │
├─────────────────────────────────────────────┤
│ ● 上下文 → ● 方案 → ○ 审阅 → ○ 编码 → ○ 测试 → ○ 沉淀 │
├─────────────────────────────────────────────┤
│                                             │
│  当前阶段：上下文                             │
│                                             │
│  [阶段工作区内容 — 根据阶段动态渲染]            │
│                                             │
│  pending → 显示执行按钮                      │
│  awaiting_review → 显示产出 + 确认推进按钮     │
│  completed → 显示产出摘要（只读）             │
│                                             │
├─────────────────────────────────────────────┤
│ 事件记录（折叠）                              │
└─────────────────────────────────────────────┘
```

### 5.2 阶段组件

每个阶段一个独立组件：

| 组件 | 文件 | 职责 |
|------|------|------|
| `ContextStagePanel` | `components/workbench/stages/context-stage-panel.tsx` | 生成和展示上下文包 |
| `SolutionStagePanel` | `components/workbench/stages/solution-stage-panel.tsx` | 生成和展示方案草案 |
| `ReviewStagePanel` | `components/workbench/stages/review-stage-panel.tsx` | 审阅清单 |
| `CodingStagePanel` | `components/workbench/stages/coding-stage-panel.tsx` | Briefing + 结果提交 |
| `TestingStagePanel` | `components/workbench/stages/testing-stage-panel.tsx` | 测试清单 |
| `DepositStagePanel` | `components/workbench/stages/deposit-stage-panel.tsx` | 沉淀入口 |

详情页根据 `run.currentStage` 和 `run.stageStatus` 渲染对应组件。

## 6. 后端改动

### 6.1 新增文件

```
server/inkdesk_server/
├── stage_actions.py    # 各阶段的执行逻辑（调 LLM、组装 briefing 等）
```

### 6.2 修改文件

| 文件 | 改动 |
|------|------|
| `main.py` | 新增 7 个 stage action API 路由 |
| `schemas.py` | 新增请求/响应模型 |

### 6.3 LLM 调用策略

方案草案和审阅清单的生成复用 `ResearchWorkspaceService` 中已封装的 agent provider。新建 `stage_actions.py`：

```python
@dataclass
class StageActionService:
    db: Session
    settings: Settings

    def generate_context_pack(self, run_id, workspace_id) -> DevRunResponse:
        # 调 ContextPackService.build()
        # 写事件
        # 返回更新后的 run

    def generate_solution(self, run_id, workspace_id) -> DevRunResponse:
        # 取 context 阶段产出
        # 调 LLM 生成方案
        # 写事件

    def prepare_coding_briefing(self, run_id, workspace_id) -> DevRunResponse:
        # 取 solution + review 阶段产出
        # 组装 Markdown briefing
        # 写事件

    # ... 其他阶段
```

## 7. 不做的事情

- ~~**不自动调用 Claude Code CLI**：用户手动在终端执行~~ → 已改为自动调用（见阶段 4 产品决策）
- **不实现 Skill 执行框架**：阶段动作直接调 LLM，不走 Skill 协议
- **不做 Harness 编排**：阶段间仍需用户手动确认推进
- **不做自动回滚**：失败后用户手动取消或重试
- **不修改 Dev Run 状态机**：6 阶段不变，只是每阶段多了执行入口

## 8. 实施顺序

按阶段逐个实现，每完成一个阶段就能验证：

1. **context 阶段**（最小验证：能生成上下文包并展示）
2. **coding 阶段**（最核心：Briefing 组装 + 启动 Claude Code CLI 子进程 + 结果自动回写）
3. **solution 阶段**（LLM 方案生成）
4. **review 阶段**（LLM 审阅清单）
5. **testing 阶段**（测试清单）
6. **deposit 阶段**（沉淀闭环）

先做 1 和 2，因为它们能最快验证 dogfooding 闭环。3-6 是增强。

## 9. 验收标准

- [ ] 用户创建 Dev Run 后，context 阶段显示"生成上下文"按钮
- [ ] 点击后生成上下文包，展示摘要，状态变为 awaiting_review
- [ ] 确认推进后进入 solution 阶段，显示"生成方案"按钮
- [ ] coding 阶段显示可复制的 Briefing 和结果提交区域
- [ ] deposit 阶段能创建沉淀提案，进入 ingest 队列
- [ ] 全流程走完后 run 状态为 completed
- [ ] 已完成阶段的产出可只读查看

## 10. 风险

| 风险 | 应对 |
|------|------|
| LLM 未配置 API key | context 和 coding 阶段不依赖 LLM，可先跑通；solution/review/testing 阶段需要 key |
| 方案质量不稳定 | 方案可编辑，用户可修改后再推进 |
| Briefing 格式不适合 Claude Code | 先用 Markdown，实测后调整 |
| 阶段产物存储膨胀 | 事件 payload 控制在合理大小，大文本截断存储 |
