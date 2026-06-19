# Vault 运营手册

## 初始化

Vault 是 Inkdesk 的知识库文件系统。每个 Vault 从零开始，通过 API 或前端引导完成初始化。初始化只需一次，后续操作都是增量。

### 两种知识库类型

| 类型 | `vaultType` | wiki 子目录 | 适用场景 |
|------|-------------|-------------|----------|
| 代码项目型 | `"code"` | `entities/`、`concepts/` | 有代码仓库的工程研究 |
| 通用知识型 | `"general"` | `topics/`、`sources/`、`queries/` | 学习笔记、阅读研究、专题探索 |

**设计原理**：类型只决定 wiki 子目录。`raw/`、`schema/`、`skills/`、`evals/`、`runs/` 六类共享目录对两种类型完全一致。类型之间不重叠——代码型的 `entities/` 和 `concepts/` 不会出现在通用型中，反之亦然。类型选择影响 Agent 行为：Agent 读取 wiki 子目录结构来决定如何组织知识。

### 初始化流程

**API 路径**：

```
GET  /api/vault/status      # 查询当前 Vault 状态
POST /api/vault/initialize   # 执行初始化，Body: { "vaultType": "code" | "general" }
```

**前端入口**：未初始化的知识库在 `/app` 展示 `VaultInitCard` 组件，用户选择类型 → 预览结构 → 确认初始化 → 跳转到 `/app/raw` 导入首批材料。

### 初始化行为（幂等）

`ensure_initialized` 的执行逻辑是三重循环：

1. **创建共享目录**（`raw/`、`wiki/`、`schema/`、`skills/`、`evals/`、`runs/`）——`mkdir(parents=True, exist_ok=True)`，已存在则跳过。
2. **创建类型专属 wiki 子目录**——仅当 `vault_type` 非空时执行。
3. **写入默认文件**——检查每个资产文件是否已存在，只补缺失文件，不覆盖已有内容。

```python
# 核心保护逻辑（vault.py）
for asset in SHARED_FILES:
    if not self.exists(asset.relative_path):       # 只在文件不存在时写入
        self.write_vault_file(asset.relative_path, asset.content)
```

**这意味着**：
- 重复调用初始化不会破坏已有文件。
- 用户手动创建或编辑的任何文件不会被覆盖。
- 系统文件（如 AGENTS.md、KB-META.md）只在缺失时补充。

### 初始化生成的默认资产

| 文件 | 位置 | 用途 |
|------|------|------|
| `AGENTS.md` | Vault 根 | Agent 行为准则（raw→ingest→wiki 工作流） |
| `wiki/index.md` | `wiki/` | 知识库目录页，按类型和统计组织 |
| `wiki/log.md` | `wiki/` | 操作日志，记录初始化和后续变更 |
| `KB-META.md` | Vault 根 | 元信息：名称、创建时间、目录结构、关联资源 |
| `schema/vault-layout.md` | `schema/` | 目录职责、文件命名、新增页面规则 |
| `schema/wiki-page-template.md` | `schema/` | 页面类型 frontmatter、章节模板、状态流转 |
| `schema/source-citation-rules.md` | `schema/` | 来源引用强制要求和禁止行为 |
| `schema/ingest-proposal-rules.md` | `schema/` | 提案类型、必须要素、审阅规则 |
| `schema/ask-answer-rules.md` | `schema/` | 查询优先级、回答格式、沉淀建议 |
| `schema/wiki-health-rules.md` | `schema/` | 结构和内容检查项、健康分计算 |

Schema 文件是 Agent 读取的"行为指令"，不是给人逐行执行的。它们定义了什么能做、什么不能做、什么格式。

---

## 目录职责

```
vault/
  raw/        原始材料（只读，不可修改）
  wiki/       LLM 生成和维护的已接受知识页
  schema/     Agent 维护规则（CLAUDE.md 的拆解版）
  skills/     可复用工作流定义
  evals/      评测任务和评分标准
  runs/       Agent 运行记录
```

| 目录 | 谁写 | 谁读 | 修改权限 |
|------|------|------|----------|
| `raw/` | 用户导入 | Agent、用户 | 只读——导入后不可修改原始材料 |
| `wiki/` | Agent 提案，用户审阅接受后写入 | Agent、用户 | 只有已接受的提案才能写入 |
| `schema/` | 系统初始化 + 用户维护 | Agent | 用户可直接编辑，Agent 不可修改 |
| `skills/` | 用户或系统 | Agent | 用户管理 |
| `evals/` | 用户定义 | 评测系统 | 用户管理 |
| `runs/` | Agent 自动记录 | 用户、Agent | Agent 追加，用户可查看 |

---

## 摄入规则

摄入是将 raw 材料转化为 wiki 知识的过程。当前阶段（4.1.1）只完成了初始化，摄入的完整流水线在后续版本实现。以下规则随初始化一并就位，作为 Agent 的行为约束。

### 摄入流程（简化版）

```
raw 导入 → Agent 处理 → 生成审阅提案 → 用户审阅 → 接受/拒绝 → 写入 wiki
```

### 关键约束

- **不直接写 wiki**：Agent 不能跳过审阅直接修改 wiki 文件。所有修改必须经过提案 → 审阅 → 接受。
- **来源必须可追溯**：wiki 中的每个 claim 必须能追溯到 raw 来源文件。
- **被拒绝的提案归档**：保留原因，不重复提出相同提案。

---

## 新增 wiki 页面规则

当 Agent 或用户需要新增 wiki 页面时，遵循以下规则（定义在 `schema/vault-layout.md`）：

1. **去重检查**：先搜索 `wiki/` 目录是否已有同主题页面。
2. **Inbound 链接**：新页面必须至少有一个从已有页面指向它的链接（不能是孤页）。
3. **更新索引**：创建新页面后必须更新 `wiki/index.md`。
4. **完整 frontmatter**：每个页面必须包含 `type`、`created`、`updated`、`tags`、`related`、`source_file`、`status` 字段。

### 页面状态流转

```
stub → draft → stable → outdated
```

| 状态 | 含义 | 何时标记 |
|------|------|----------|
| `stub` | 刚创建，内容不完整 | 初始化或快速记录时 |
| `draft` | 主要内容已填充，待补充细节 | 主体内容完成后 |
| `stable` | 内容完整，所有 claims 有来源 | 审阅确认后 |
| `outdated` | 内容可能过时，待更新 | 来源文件变更或定期复查时 |

---

## 知识更新规则

已有 wiki 页面的更新同样走提案流程：

1. **创建 patch 提案**：指定目标页面、变更内容、来源依据。
2. **列出影响范围**：提案需说明哪些关联页面可能受影响。
3. **审阅后接受**：用户确认后方可写入。
4. **更新 log.md**：每次变更追加操作日志条目。

---

## 设计决策记录

### 为什么类型选择通过文件系统而非数据库标记？

文件系统是 Agent 可直接读取的真实状态。如果类型信息只存在数据库里，Agent 读取 vault 目录时无法判断类型。让 wiki 子目录的存在本身成为类型信号——Agent 看到 `entities/` 和 `concepts/` 就知道这是代码项目型。

### 为什么 Schema 要拆成多个文件？

单文件 CLAUDE.md 需要 Agent 一次加载全部规则。拆成 6 个专题文件后，Agent 按需读取——处理来源引用时读 `source-citation-rules.md`，处理摄入提案时读 `ingest-proposal-rules.md`。减少不必要的上下文消耗。

### 为什么初始化不覆盖已有文件？

`exists()` 检查是增量保护的核心。用户可能在初始化后又手动编辑了 AGENTS.md 或 KB-META.md，覆盖会丢失用户的修改。只补缺失文件确保系统资产完整 + 用户内容安全。

### 为什么 index.md 和 log.md 从初始化就生成？

文章团队的经验教训——事后补建，信息已经丢失。从 Vault 诞生的第一刻就有目录和日志，所有后续操作只需追加。

---

## 常见操作速查

| 操作 | API / 方法 | 说明 |
|------|-----------|------|
| 检查状态 | `GET /api/vault/status` | 返回 `initialized`、`vaultType`、`sharedDirsExist` |
| 初始化 | `POST /api/vault/initialize` | Body: `{ "vaultType": "code" }` |
| 重复初始化 | 同上 | 幂等，只补缺失文件 |
| 导入 raw 材料 | `POST /api/raw` 系列 | 支持 web、text、pdf 三种类型 |
| 查看 wiki | `GET /api/wiki` | 列表 |
| 查看 wiki 详情 | `GET /api/wiki/{topicId}` | 单页详情 |
| 问答 | `POST /api/ask` | 基于知识库回答 |
