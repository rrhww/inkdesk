# Dev Run 阶段执行入口实施计划

> **配套设计文档：** [2026-07-09-dev-run-stage-actions-design.md](../specs/2026-07-09-dev-run-stage-actions-design.md)
>
> **执行原则：** 用户授权 Codex 全权执行。每个任务先写失败测试，确认失败原因正确，再实现。
>
> **执行状态：** 2026-07-09 已完成全部 7 个任务。
>
> **目标：** 让 Dev Run 的 6 个阶段从"纯状态机追踪"变成"每阶段有执行入口"，最终跑通 `PRD → context → solution → review → coding(Claude Code) → testing → deposit` 完整闭环。

**技术栈：** FastAPI, SQLAlchemy, Python 3.12, Next.js 16, React 19, TypeScript, pytest, Vitest

---

## 文件清单

### 后端

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `server/inkdesk_server/stage_actions.py` | 阶段执行逻辑（ContextPack 调用、LLM 方案生成、Briefing 组装、Claude Code 子进程） |
| 修改 | `server/inkdesk_server/schemas.py` | 新增请求/响应模型 |
| 修改 | `server/inkdesk_server/main.py` | 新增 7 个 stage action API 路由 |
| 修改 | `server/tests/test_run_api.py` | 新增 stage action 测试 |

### 前端

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `web/components/workbench/stages/context-stage-panel.tsx` | 上下文阶段面板 |
| 新增 | `web/components/workbench/stages/solution-stage-panel.tsx` | 方案阶段面板 |
| 新增 | `web/components/workbench/stages/review-stage-panel.tsx` | 审阅阶段面板 |
| 新增 | `web/components/workbench/stages/coding-stage-panel.tsx` | 编码阶段面板 |
| 新增 | `web/components/workbench/stages/testing-stage-panel.tsx` | 测试阶段面板 |
| 新增 | `web/components/workbench/stages/deposit-stage-panel.tsx` | 沉淀阶段面板 |
| 修改 | `web/app/app/runs/[id]/page.tsx` | 详情页改造：根据当前阶段渲染对应面板 |
| 修改 | `web/lib/research.ts` | 新增 stage action API 调用函数 |
| 修改 | `web/lib/types.ts` | 新增阶段产出类型 |

### 文档

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `README.md` | 更新阶段一完成状态（Dev Run Console 已完成） |
| 修改 | `docs/product/产品路线图.md` | 标注本计划为当前活跃切片 |
| 修改 | `cognitive-map.md` | 任务结束后更新认知地图 |

---

## 任务一：context 阶段 — 生成上下文包

**验证目标：** 用户在 Dev Run 详情页点击"生成上下文"，后端调用 `ContextPackService`，写入事件，前端展示上下文摘要。

### 后端

- [x] **步骤 1：写失败测试**

在 `server/tests/test_run_api.py` 中添加：

```python
def test_context_pack_creates_stage_event(temp_app_env):
    client = owner_client(temp_app_env)
    run = client.post("/api/runs", json={
        "type": "PRD",
        "title": "测试上下文生成",
        "goal": "验证 context 阶段能生成上下文包",
    }).json()

    response = client.post(f"/api/runs/{run['id']}/context-pack")

    assert response.status_code == 200
    run_updated = response.json()
    assert run_updated["currentStage"] == "context"
    assert run_updated["stageStatus"] == "awaiting_review"

    events = run_updated["events"]
    assert any(e["eventType"] == "context_pack_generated" for e in events)
    assert any(e["stage"] == "context" for e in events)
```

- [x] **步骤 2：运行测试，确认失败**

```powershell
cd server
python -m pytest tests/test_run_api.py -k context_pack -x
```

预期：404，`/api/runs/{id}/context-pack` 路由不存在。

- [x] **步骤 3：实现 `StageActionService.generate_context_pack()`**

在 `server/inkdesk_server/stage_actions.py` 中新建：

```python
@dataclass
class StageActionService:
    db: Session
    settings: Settings

    def generate_context_pack(self, run_id: str, workspace_id: str) -> DevRunResponse:
        # 1. 调用 ContextPackService.build()
        # 2. 提取摘要（wiki 页面数、ask 历史条数、待审阅项数）
        # 3. 调用 RunService.add_event(stage="context", event_type="context_pack_generated", payload=摘要)
        # 4. 返回更新后的 run
```

- [x] **步骤 4：添加 API 路由**

在 `server/inkdesk_server/main.py` 中添加：

```python
@app.post("/api/runs/{run_id}/context-pack", response_model=DevRunResponse)
def run_context_pack(run_id: str, db: Annotated[Session, Depends(get_db)]):
    workspace = _resolve_workspace(db)
    return StageActionService(db, settings).generate_context_pack(run_id, workspace.id)
```

- [x] **步骤 5：运行测试，确认通过**

```powershell
cd server
python -m pytest tests/test_run_api.py -k context_pack -x
```

### 前端

- [x] **步骤 6：添加类型和 API 函数**

在 `web/lib/types.ts` 中添加：

```typescript
export type ContextPackSummary = {
  wikiPageCount: number;
  askHistoryCount: number;
  pendingReviewCount: number;
  wikiPages: { id: string; title: string }[];
};
```

在 `web/lib/research.ts` 中添加：

```typescript
export async function generateContextPack(runId: string): Promise<DevRun> {
  return postInkdeskJson<DevRun>(`/runs/${runId}/context-pack`, {});
}
```

- [x] **步骤 7：实现 `ContextStagePanel` 组件**

新建 `web/components/workbench/stages/context-stage-panel.tsx`：

- `pending` 状态：显示"生成上下文"按钮，点击调 `generateContextPack()`
- `awaiting_review` 状态：从事件的 payload 中提取上下文摘要并展示（wiki 页面数、ask 历史、待审阅项）
- `completed` 状态：只读展示摘要

- [x] **步骤 8：在详情页接入**

修改 `web/app/app/runs/[id]/page.tsx`：当 `run.currentStage === "context"` 时渲染 `<ContextStagePanel>`。

- [x] **步骤 9：浏览器验证**

启动前后端，创建一个 Dev Run，在详情页点击"生成上下文"，确认：
- 按钮点击后显示 loading
- 生成后展示上下文摘要
- 状态变为"待确认"
- 点击"批准推进"后进入 solution 阶段

---

## 任务二：coding 阶段 — 启动 Claude Code 子进程

**验证目标：** 用户在 coding 阶段点击"启动 Claude Code"，后端组装 Briefing，启动 `claude -p` 子进程，执行完成后自动回写结果。

> **注意：** 此任务需要先完成 solution 和 review 阶段（任务三、四），因为 Briefing 依赖方案和审阅产出。如果想先验证 coding 闭环，可以用硬编码的方案文本作为 placeholder。

### 后端

- [x] **步骤 1：检测 Claude Code CLI 是否可用**

在终端运行：

```powershell
claude --version
```

如果没有安装，先安装并登录。记录 CLI 的版本和输出格式。

- [x] **步骤 2：写失败测试**

在 `server/tests/test_run_api.py` 中添加：

```python
def test_coding_execute_starts_and_completes(temp_app_env):
    client = owner_client(temp_app_env)
    run = client.post("/api/runs", json={
        "type": "PRD",
        "title": "测试 coding 执行",
        "goal": "验证 coding 阶段能启动 Claude Code",
        "repoContext": ".",
    }).json()

    # 手动推进到 coding 阶段（测试中可以跳过中间阶段）
    # 方式：直接 add_event 推进，或用 advance 跳过
    for stage in ["context", "solution", "review"]:
        client.post(f"/api/runs/{run['id']}/events", json={
            "stage": stage, "eventType": "stage_output", "payload": {"skipped": True}
        })
        client.post(f"/api/runs/{run['id']}/advance", json={"action": "approve"})

    response = client.post(f"/api/runs/{run['id']}/coding/execute")

    assert response.status_code == 200
    run_updated = response.json()
    # 执行后应有 briefing_prepared 事件
    events = run_updated["events"]
    assert any(e["eventType"] == "coding_briefing_prepared" for e in events)
```

- [x] **步骤 3：运行测试，确认失败**

```powershell
cd server
python -m pytest tests/test_run_api.py -k coding_execute -x
```

- [x] **步骤 4：实现 `StageActionService.prepare_coding_briefing()`**

在 `stage_actions.py` 中添加：

```python
def prepare_coding_briefing(self, run_id: str, workspace_id: str) -> DevRunResponse:
    # 1. 获取 run
    # 2. 从事件中提取 solution 阶段的方案文本和 review 阶段的审阅清单
    # 3. 组装 Markdown briefing
    # 4. 写入 coding_briefing_prepared 事件
    # 5. 返回更新后的 run
```

- [x] **步骤 5：实现 Claude Code 子进程调用**

在 `stage_actions.py` 中添加：

```python
import asyncio
import subprocess

# 全局进程注册表
_coding_processes: dict[str, asyncio.subprocess.Process] = {}

async def execute_claude_code(self, run_id: str, briefing: str, repo_context: str) -> None:
    # 1. 启动 subprocess: claude -p "{briefing}" --cwd {repo_context}
    # 2. 注册到 _coding_processes
    # 3. 等待完成（带超时 300s）
    # 4. 捕获 stdout/stderr
    # 5. 写入 coding_result_submitted 事件
    # 6. 从 _coding_processes 中移除
```

- [x] **步骤 6：添加 API 路由**

```python
@app.post("/api/runs/{run_id}/coding/execute", response_model=DevRunResponse)
async def run_coding_execute(run_id: str, db: Annotated[Session, Depends(get_db)]):
    workspace = _resolve_workspace(db)
    return await StageActionService(db, settings).execute_coding(run_id, workspace.id)

@app.get("/api/runs/{run_id}/coding/status")
def run_coding_status(run_id: str, db: Annotated[Session, Depends(get_db)]):
    workspace = _resolve_workspace(db)
    return StageActionService(db, settings).get_coding_status(run_id, workspace.id)
```

- [x] **步骤 7：运行测试，确认通过**

```powershell
cd server
python -m pytest tests/test_run_api.py -k coding -x
```

### 前端

- [x] **步骤 8：添加类型和 API 函数**

在 `web/lib/types.ts` 中添加：

```typescript
export type CodingStatus = "idle" | "running" | "completed" | "failed" | "timeout";

export type CodingExecutionState = {
  status: CodingStatus;
  briefing: string | null;
  result: string | null;
  error: string | null;
};
```

在 `web/lib/research.ts` 中添加：

```typescript
export async function executeCoding(runId: string): Promise<DevRun> {
  return postInkdeskJson<DevRun>(`/runs/${runId}/coding/execute`, {});
}

export async function getCodingStatus(runId: string): Promise<CodingExecutionState> {
  return fetchInkdeskJson<CodingExecutionState>(`/runs/${runId}/coding/status`);
}
```

- [x] **步骤 9：实现 `CodingStagePanel` 组件**

新建 `web/components/workbench/stages/coding-stage-panel.tsx`：

- `pending` 状态：显示 Briefing 预览 + "启动 Claude Code"按钮
- `running` 状态：显示 spinner + "Claude Code 执行中…" + 轮询 `getCodingStatus()`
- `awaiting_review` 状态：显示执行结果摘要 + "确认推进"按钮
- `failed` 状态：显示错误信息 + "重试"按钮

- [x] **步骤 10：在详情页接入**

修改 `web/app/app/runs/[id]/page.tsx`：当 `run.currentStage === "coding"` 时渲染 `<CodingStagePanel>`。

- [x] **步骤 11：浏览器验证**

创建 Dev Run，手动推进到 coding 阶段（或跳过中间阶段），点击"启动 Claude Code"，确认：
- Briefing 正确组装
- 子进程启动并执行
- 执行结果自动回写
- 状态变为"待确认"

---

## 任务三：solution 阶段 — LLM 生成方案草案

**验证目标：** 用户在 solution 阶段点击"生成方案"，后端调 LLM 生成方案草案，写入事件，前端展示可编辑的方案。

> **依赖：** 需要 `OPENAI_API_KEY` 或 `DEEPSEEK_API_KEY`。

### 后端

- [x] **步骤 1：写失败测试**

```python
def test_solution_generates_draft(temp_app_env):
    client = owner_client(temp_app_env)
    run = client.post("/api/runs", json={
        "type": "PRD",
        "title": "测试方案生成",
        "goal": "验证 solution 阶段能生成方案草案",
    }).json()
    # 推进到 solution 阶段
    client.post(f"/api/runs/{run['id']}/context-pack")
    client.post(f"/api/runs/{run['id']}/advance", json={"action": "approve"})

    response = client.post(f"/api/runs/{run['id']}/solution")

    assert response.status_code == 200
    events = response.json()["events"]
    assert any(e["eventType"] == "solution_draft_generated" for e in events)
```

- [x] **步骤 2：运行测试，确认失败**

- [x] **步骤 3：实现 `StageActionService.generate_solution()`**

```python
def generate_solution(self, run_id: str, workspace_id: str) -> DevRunResponse:
    # 1. 获取 run + context 阶段产出
    # 2. 构建 prompt：任务目标 + 上下文摘要 + "请生成技术方案草案"
    # 3. 调用 LLM（复用 ResearchWorkspaceService 的 agent provider）
    # 4. 写入 solution_draft_generated 事件
    # 5. 返回更新后的 run
```

- [x] **步骤 4：添加 API 路由**

- [x] **步骤 5：运行测试，确认通过**

### 前端

- [x] **步骤 6：实现 `SolutionStagePanel` 组件**

- `pending`：显示"生成方案"按钮
- `awaiting_review`：显示方案草案（Markdown 渲染）+ 可编辑 textarea + "重新生成" + "确认推进"
- `completed`：只读方案

- [x] **步骤 7：在详情页接入**

- [x] **步骤 8：浏览器验证**

---

## 任务四：review 阶段 — LLM 生成审阅清单

**验证目标：** 用户在 review 阶段看到 LLM 基于方案生成的审阅清单，可逐项标记。

### 后端

- [x] **步骤 1：写失败测试**

- [x] **步骤 2：运行测试，确认失败**

- [x] **步骤 3：实现 `StageActionService.generate_review_checklist()`**

```python
def generate_review_checklist(self, run_id: str, workspace_id: str) -> DevRunResponse:
    # 1. 获取 solution 阶段的方案文本
    # 2. 构建 prompt："请基于以下方案生成审阅清单"
    # 3. 调用 LLM
    # 4. 写入 review_checklist_generated 事件
    # 5. 返回更新后的 run
```

- [x] **步骤 4：添加 API 路由**

- [x] **步骤 5：运行测试，确认通过**

### 前端

- [x] **步骤 6：实现 `ReviewStagePanel` 组件**

- 审阅清单（每项可勾选 通过 / 需修改）
- 审阅意见 textarea
- "确认推进"按钮

- [x] **步骤 7：在详情页接入**

- [x] **步骤 8：浏览器验证**

---

## 任务五：testing 阶段 — 测试检查清单

**验证目标：** 用户在 testing 阶段看到测试清单，标记测试结果。

### 后端

- [x] **步骤 1：写失败测试**

- [x] **步骤 2：运行测试，确认失败**

- [x] **步骤 3：实现 `StageActionService.generate_testing_checklist()`**

- [x] **步骤 4：添加 API 路由**

- [x] **步骤 5：运行测试，确认通过**

### 前端

- [x] **步骤 6：实现 `TestingStagePanel` 组件**

- [x] **步骤 7：在详情页接入**

- [x] **步骤 8：浏览器验证**

---

## 任务六：deposit 阶段 — 沉淀关键产出

**验证目标：** 用户在 deposit 阶段点击"沉淀"，调用 DepositService 创建提案，进入 ingest 队列。

### 后端

- [x] **步骤 1：写失败测试**

```python
def test_deposit_creates_review_proposal(temp_app_env):
    client = owner_client(temp_app_env)
    run = client.post("/api/runs", json={
        "type": "PRD",
        "title": "测试沉淀",
        "goal": "验证 deposit 阶段能创建提案",
    }).json()
    # 推进到 deposit 阶段（跳过中间阶段）
    for stage in ["context", "solution", "review", "coding", "testing"]:
        client.post(f"/api/runs/{run['id']}/events", json={
            "stage": stage, "eventType": "stage_output", "payload": {"skipped": True}
        })
        client.post(f"/api/runs/{run['id']}/advance", json={"action": "approve"})

    response = client.post(f"/api/runs/{run['id']}/deposit")

    assert response.status_code == 200
    # 验证 ingest 队列中有新提案
    reviews = client.get("/api/ingest").json()
    assert any(r.get("title", "").startswith(run["title"]) for r in reviews)
```

- [x] **步骤 2：运行测试，确认失败**

- [x] **步骤 3：实现 `StageActionService.create_deposit()`**

```python
def create_deposit(self, run_id: str, workspace_id: str) -> DevRunResponse:
    # 1. 收集各阶段产出
    # 2. 调用 DepositService.create(source="stage_output", runId=run_id, stage="deposit", payload=产出)
    # 3. 写入 deposit_created 事件
    # 4. 返回更新后的 run
```

- [x] **步骤 4：添加 API 路由**

- [x] **步骤 5：运行测试，确认通过**

### 前端

- [x] **步骤 6：实现 `DepositStagePanel` 组件**

- 沉淀摘要预览
- "沉淀"按钮
- 沉淀成功后显示"完成任务"按钮
- 链接到 `/app/ingest`

- [x] **步骤 7：在详情页接入**

- [x] **步骤 8：浏览器验证**

---

## 任务七：全流程集成验证

- [x] **步骤 1：端到端跑通**

创建一个真实的 Dev Run（如"给 /app 添加 Dev Run 搜索功能"），完整走完 6 个阶段。

- [x] **步骤 2：确认已完成阶段的产出可只读查看**

在详情页，点击已完成的阶段，确认能看到历史产出。

- [x] **步骤 3：更新文档**

- `README.md`：更新阶段一完成状态
- `docs/product/产品路线图.md`：标注本计划完成
- `cognitive-map.md`：更新认知地图

---

## 执行节奏

| 任务 | 优先级 | 依赖 | 可验证产出 |
|------|--------|------|-----------|
| 一：context | P0 | 无 | 上下文包生成并展示 |
| 三：solution | P1 | 任务一 | LLM 方案草案 |
| 四：review | P1 | 任务三 | 审阅清单 |
| 二：coding | P0 | 任务三、四（或用 placeholder） | Claude Code 子进程执行 |
| 五：testing | P2 | 任务二 | 测试清单 |
| 六：deposit | P1 | 无 | 沉淀提案进入 ingest |
| 七：集成验证 | P0 | 全部 | 完整 dogfooding 闭环 |

建议从任务一和任务六开始（不依赖 LLM，能最快验证骨架），然后做任务三、四（需要 LLM），最后做任务二（需要 Claude Code CLI）。

每个任务完成后，在 `cognitive-map.md` 追加一条认知记录。

---

## 执行调整与验收记录（2026-07-09）

### 实际执行顺序

1. 任务一 context：搭建 `StageActionService` 骨架与上下文包生成。
2. 任务六 deposit：验证 deposit 服务集成，建立端到端闭环信心。
3. 任务三 solution + 任务四 review：LLM/deterministic 双路径生成方案与审阅清单。
4. 任务二 coding：Claude Code CLI 子进程调用 + `coding/status` 轮询。
5. 任务五 testing：测试清单生成（本轮新增）。
6. 任务七 集成验证：浏览器走完 6 阶段完整闭环（本轮完成）。

### 关键调整

- **任务二 coding 支持跳过：** 浏览器验收发现 coding 阶段仅有「启动 Claude Code」按钮时，未安装/不想调用 CLI 的用户无法继续流程。在 `CodingStagePanel` 中新增「跳过，手动批准」按钮，调用 `/api/runs/{run_id}/events` 写入 `stage_output`（`skipped: true`），使阶段进入 `awaiting_review`，后续可正常推进到 testing。
- **任务五 testing 消费 coding 产出：** `generate_testing_checklist` 的 prompt 会读取 `coding_result_submitted` 事件中的结果文本，生成回归/边界/异常路径等测试项。
- **coding 子进程 cwd：** 使用 `asyncio.create_subprocess_exec(..., cwd=run.repoContext)`，不使用不存在的 `--cwd` CLI 参数。

### 验收数据

- 后端测试：`tests/test_run_api.py` 26 passed；完整套件 247 passed, 1 skipped。
- 前端构建：`npm run typecheck` 通过；`npm run lint` 0 errors（3 个 pre-existing warnings）。
- 服务健康：后端 `/actuator/health` UP；前端 `/api/health` PASSED。
- 浏览器验证：新建 run `run-4909ec4ded06` 在浏览器中完成 context → solution → review → coding（跳过） → testing → deposit 全部 6 阶段。
