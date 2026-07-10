# Inkdesk UI 重构方案：迁移至 TRAE Work 设计系统

## 0. 背景

Inkdesk 当前的 UI 使用一套自建的 `ink-*` 设计令牌（ teal-green 主色、超大圆角 paper-card、三字体栈），视觉上偏"杂志风笔记工具"。但产品愿景明确指出 Inkdesk 是 **AI 研发自动化控制台**，不是笔记 App。

本方案将 Inkdesk 的视觉层迁移到以 TRAE Work 为基底的自定义 token 体系。品牌色选定为 **石墨靛蓝 `#334155`**（slate-700）——一个几乎中性的深灰蓝，只在主按钮、激活导航和品牌标识上点睛出现。这个选择基于 Inkdesk 的产品定位：控制台不需要用颜色证明自己，排版和层级已经足够。其余表面、排版、圆角、间距均对齐 TRAE Work 的 Light-mode token 规范。

---

## 1. 核心差距分析

### 1.1 色彩系统

| 维度 | 当前 Inkdesk | Inkdesk 新 (基于 TRAE Work) | 变化说明 |
|------|-------------|--------------------------|---------|
| 品牌主色 | `#00685f` teal-green | **`#334155` 石墨靛蓝** | 从自然绿迁移到几乎中性的深灰蓝 |
| 品牌主色 hover | `#00685f` opacity | `#1e293b` (slate-800) | hover 加深 |
| 品牌浅底 | `#e8f6f4` | `#f1f5f9` (slate-100) | 石墨蓝浅底 |
| 品牌文字色 | `#00685f` 文字链接 | `#334155` | 与品牌色一致 |
| 页面背景 | `#f8f9fa` + radial-gradient | `#ffffff` 纯白 | 去掉装饰渐变 |
| 面板/卡片 | 白色 `#ffffff` | `#f5f5f5` (bg-base-secondary) | 面板用浅灰区分层级 |
| 输入/字段 | 白色 | `--bg-overlay-l1` (grey 8%) | 字段区用 overlay 区分 |
| 边框 | `border-black/5` ~ `#bcc9c6` | `--border-neutral-l1` (grey 12%) | 统一到中性灰边框 |
| 文本主色 | `#191c1d` 深墨 | `#171717` (text-default) | 几乎一致 |
| 文本辅助 | `#687573` 绿灰 | `#404040` (text-secondary) | 中性灰 |
| 状态色 | 自建 ink-errorSoft / ink-tertiary | `--status-*` 语义系统 | 迁移到标准 status token |
| 错误色 | `#93000a` | `#e8463a` (status-error-default) | 标准红 |
| 警告色 | `#924628` | `#e27900` (status-warning-default) | 标准橙 |

### 1.1.1 品牌色决策记录

**选定：石墨靛蓝 `#334155` (slate-700)**

选择理由：
- 品牌色在 Inkdesk 中是辅助角色，不是主叙事。产品是控制台，控制台的重点是信息层级和操作效率，不是颜色识别。
- `#334155` 在视觉上几乎是中性色，只在和纯白、纯灰对比时才显现"深蓝灰"身份。这让品牌色出现在按钮、激活态和 logo 上时不抢信息层级的风头。
- 与 TRAE Work 的中性灰阶体系天然兼容。TRAE Work 的 `brand-grey-800` (`#262626`) 和 `brand-grey-700` (`#404040`) 都在同一个灰蓝族里，`#334155` 正好卡在"比 neutral 稍有色彩倾向"的位置。
- "石墨"材质感传递工程工具的可信赖印象，不像亮蓝/紫那样偏消费级。

品牌色使用规则：
- 只出现在：主按钮填充、导航激活态、品牌 logo、关键状态 accent
- 不出现在：hover 行、普通边框、装饰性填充、大面积背景

### 1.2 圆角系统

| 维度 | 当前 | TRAE Work | 变化 |
|------|------|-----------|------|
| 卡片/面板 | `rounded-[28px]` 超大圆角 | `--radius-8` (8px) / `--radius-12` (12px) | 大幅收敛 |
| 按钮 | `rounded-full` (药丸) | `--radius-8` (微圆) | 从药丸改为微圆 |
| 输入框 | `rounded-[18px]` | `--radius-8` | 收敛 |
| 标签/药丸 | `rounded-full` | `--radius-full` (保留) | tag/pill 保留全圆 |
| 内容区块 | `rounded-[22px]` | `--radius-8` | 收敛 |

**设计判断**：当前 28px 圆角让界面偏"文具感"，与研发控制台的专业定位冲突。TRAE Work 的 8px 体系更克制，但 tag/pill 保留 `radius-full` 传递状态信息。

### 1.3 字体系统

| 维度 | 当前 | TRAE Work | 变化 |
|------|------|-----------|------|
| 标题字体 | `var(--font-manrope)` Aptos Display | `font-family-heading` (SF Pro) | 切换到系统原生 |
| 正文字体 | `var(--font-inter)` Aptos | `font-family-default` (SF Pro Text) | 切换到系统原生 |
| 衬线字体 | `var(--font-newsreader)` Iowan Old Style | 无（去掉衬线） | 删除衬线栈 |
| 数据/指标 | 无独立栈 | `font-family-metric` (Inter) | 新增 Inter 用于指标数字 |
| 代码 | 无独立栈 | `font-family-mono` (JetBrains Mono) | 新增 mono 栈 |
| 基线字号 | 14px (一致) | 14px `body-base` | 一致 |
| eyebrow | `text-[11px] uppercase tracking-[0.2em]` | `heading-3xs` 11px/600/16px | 保留但收紧为 token |

### 1.4 阴影与表面

| 维度 | 当前 | TRAE Work | 变化 |
|------|------|-----------|------|
| 卡片阴影 | `shadow-paper` (0 18px 40px rgba 6%) | 无阴影，用边框 + 表面色差 | 去掉阴影，改用表面层级 |
| 页面背景渐变 | radial-gradient teal + linear-gradient | 无 | 去掉装饰渐变 |
| 表面层级 | 纯色白/绿灰 | `--bg-base-default` / `--bg-base-secondary` / `--bg-overlay-l1..4` | 引入 overlay 梯度 |

### 1.5 组件语言

| 维度 | 当前问题 | TRAE Work 方向 |
|------|---------|---------------|
| 卡片泛滥 | 所有内容都包在 `paper-card` 里 | 面板只在交互需要时使用，其余用 layout + 分隔线 |
| 按钮风格 | 全部 `rounded-full` 药丸 | 主按钮 `--radius-8`，ghost/tertiary 用 overlay |
| 标签风格 | `StatusPill` 全圆 + 各种 tone | 迁移到 `--status-*-surface-l1` 语义标签 |
| 输入框 | 超大圆角 + focus ring | `--radius-8` + neutral overlay focus |
| eyebrow 文字 | `text-[11px] uppercase tracking-[0.2em]` 满屏 | 收敛为 `heading-3xs`，只在需要时使用 |
| 装饰图标 | material-symbols-outlined 散布 | 迁移到 TRAE Work 本地 SVG，16px 默认 |

---

## 2. 视觉方向定义

### Visual Thesis

> Inkdesk 的界面应该像一个安静的工程控制台：白色表面、中性灰层级、石墨靛蓝 `#334155` 作为唯一品牌色出现在行动点和身份处，排版和间距承载全部层级关系。

### Design Principles（产品适配版）

1. **控制台优先**：这是 Dev Run Console，不是笔记工具。去掉 paper-card 阴影和超大圆角。
2. **表面即层级**：用 `--bg-base-default` / `--bg-base-secondary` / `--bg-overlay-l1` 三层表面区分层级，不用阴影。
3. **一个品牌色**：石墨靛蓝 `#334155` 只出现在主按钮、激活导航、品牌标识和关键状态。其他全部中性灰。
4. **排版即结构**：用 `heading-*` 和 `body-*` token 承载层级，减少 eyebrow 的使用频率。
5. **克制圆角**：`--radius-8` 作为默认，`--radius-full` 仅用于 tag/pill。
6. **无边框卡片**：面板用表面色差区分，不依赖阴影和粗边框。

---

## 3. 逐层重构计划

### 3.1 Layer 1: Token 基础设施

**改动范围**：`tailwind.config.ts` + `globals.css`

**`tailwind.config.ts`**：
- 将 `ink.*` 全部替换为 TRAE Work 对应 token 的 CSS 变量引用
- 新增 `font-mono`（JetBrains Mono）和 `font-metric`（Inter）配置
- 去掉 `shadow-paper`，新增 `shadow-none` 或依赖 TRAE Work 默认

Token 映射表（核心）：

```
ink-bg          -> var(--bg-base-default)         #ffffff     页面背景
ink-surface     -> var(--bg-base-secondary)       #f5f5f5     面板/卡片表面
ink-low         -> var(--bg-base-secondary)       #f5f5f5     大面积结构背景（侧栏、按钮底色、区块填充）
ink-low:hover   -> var(--bg-overlay-l2)           grey 12%    ink-low 元素的 hover 态
ink-high        -> var(--bg-base-tertiary)        #e5e5e5     分隔条、disabled 表面
ink-text        -> var(--text-default)            #171717     主文本
ink-muted       -> var(--text-tertiary)           #737373     辅助文本
ink-primary     -> #334155                        石墨靛蓝    品牌主色（覆盖 --bg-brand）
ink-primary/90  -> #1e293b                        slate-800   品牌 hover 态
ink-primarySoft -> #f1f5f9                        slate-100   品牌浅底（选中态、软标签）
ink-tertiary    -> var(--status-warning-default)  #e27900     警告色
ink-errorSoft   -> var(--status-error-surface-l1) rgba(232,70,58,0.12)  错误浅底
ink-errorText   -> var(--status-error-default)    #e8463a     错误文字
ink-line        -> var(--border-neutral-l1)       rgba(115,115,115,0.12)  边框（默认）
```

> **`ink-low` 拆分说明**：当前 `ink-low` (`#f3f4f5`) 在代码中有两种用法——大面积结构背景（侧栏、区块填充）和轻微交互底色（hover、按钮底色）。映射时拆为两层：结构背景用 `--bg-base-secondary`（实色 `#f5f5f5`，不透明），交互底色用 `--bg-overlay-l1`（透明灰）。详见各组件的 Layer 改动说明。

#### 品牌色完整变体

Inkdesk 的自定义品牌色需要完整的变体链（对标 TRAE Work `--bg-brand` 的变体体系）：

```
--ink-brand:              #334155   (主色，对标 --bg-brand)
--ink-brand-hover:       #1e293b   (hover，对标 --bg-brand-hover)
--ink-brand-active:      #0f172a   (active/pressed，对标 --bg-brand-active)
--ink-brand-disabled:     rgba(51,65,85,0.22)   (disabled，对标 --bg-brand-disabled)
--ink-brand-onbrand:      #ffffff   (品牌色上的文字，对标 --text-onbrand)
--ink-brand-popup:        #f1f5f9   (浅底/选中态，对标 --bg-brand-popup)
--ink-brand-border:       #334155   (品牌色边框，对标 --border-brand)
```

> 注：品牌色 `#334155` 不使用 TRAE Work 的 `--bg-brand` (`#4b3fe3`)。Inkdesk 在 TRAE Work 的表面、排版、圆角、间距 token 基础上，仅覆盖品牌色为自定义石墨靛蓝。

**`globals.css`**：
- 去掉 `radial-gradient` 装饰背景，改为纯白 `var(--bg-base-default)`
- 去掉 `--font-newsreader`（衬线栈）
- 导入 TRAE Work `colors_and_type.css` 作为 CSS 变量源，再覆盖 `--ink-brand-*` 自定义变量
- 导入 TRAE Work `components.css`，使 `ds-*` 组件类全局可用（见下方组件复用策略）
- 去掉 `.paper-card` 工具类
- 去掉 `--font-inter` / `--font-manrope`（被 TRAE Work `--font-family-default` / `--font-family-heading` 替代）

#### 组件复用策略：`ds-*` 类 vs Tailwind 工具类

TRAE Work 提供了完整的 `ds-btn`、`ds-input`、`ds-select`、`ds-card`、`ds-tabs`、`ds-tag`、`ds-notif`、`ds-dialog` 等组件类。Inkdesk 应直接引入 `components.css` 并在组件中复用这些类，而不是在 Tailwind 中重新定义等效样式。

**复用原则**：
- **直接用 `ds-*` 类**：按钮（`ds-btn`）、输入框（`ds-input`）、选择器（`ds-select`）、标签（`ds-tag`）、面包屑（`ds-breadcrumb`）、空状态（`ds-empty`）、通知条（`ds-notif`）、对话框（`ds-dialog`）
- **Tailwind 辅助**：页面布局、间距、flex/grid、响应式断点仍用 Tailwind 工具类
- **不混用**：同一个元素不要同时用 `ds-*` 类和 Tailwind 覆盖同名属性（如不要在 `ds-btn` 上再加 `rounded-full`）

**引入方式**：在 `globals.css` 中 `@import` TRAE Work 的 `colors_and_type.css` 和 `components.css`，或在 `layout.tsx` 中通过 `<link>` 引入。

### 3.2 Layer 2: App Shell（导航骨架）

**改动范围**：`app-header.tsx` / `app-sidebar.tsx` / `app-chrome.tsx`

**AppHeader**：
- 导航 tab 从 `rounded-full` 药丸改为 TRAE Work `.ds-tabs` 风格：`--radius-8` 底部或填充态
- 激活态：`bg-[#334155] text-white`，非激活：`text-secondary`，hover 用 `bg-overlay-l1`
- 去掉 `shadow-paper`
- 标题区域用 `heading-md` token，去掉 eyebrow

**AppSidebar**：
- 侧栏背景从 `bg-ink-low` 改为 `bg-[var(--bg-base-secondary)]`（实色 `#f5f5f5`，不是 `--bg-overlay-l1` 透明层，因为侧栏是大面积结构背景需要不透明）
- Logo 区域保持品牌色标识，但 logo icon 迁移到 TRAE Work SVG
- 历史条目从圆角卡片改为 list item + 左侧 border accent（当前激活态）
- "新建任务"按钮保持品牌色，但改为 `--radius-8`

**AppChrome**：
- 结构不变，只调整表面色和间距 token

### 3.3 Layer 3: 共享 UI 原子组件

**`panel-card.tsx`**：
- 从 `paper-card` (28px radius + shadow) 改为直接使用 TRAE Work `ds-card` 类（`radius-12` + `border-neutral-l1` + `bg-base-secondary` + `p-20`）
- `PanelCard` 组件内部实现从 `paper-card` class 改为 `ds-card` class，对外 props 接口不变
- 大面积内容区域不再包 PanelCard，改用 layout + dividers

**`section-heading.tsx`**：
- eyebrow 从 `text-[11px] uppercase tracking-[0.2em]` 改为 `heading-3xs` (11px/600/16px)
- 标题从 `text-4xl font-extrabold` 改为 `heading-2xl` (28px/600/36px)
- 描述保持 `body-base`

**`stat-card.tsx`**：
- 去掉 panel-card 包裹，改为 inline metric layout
- 数值用 `font-family-metric` (Inter)
- 标签用 `body-sm` (11px)

**`status-pill.tsx`**：
- 迁移到 TRAE Work status token 系统
- `tone="primary"` -> `--ink-brand-popup` (#f1f5f9) surface + `--ink-brand` (#334155) text（石墨靛蓝浅底，不是 TRAE Work 原生 brand-300）
- `tone="soft"` -> `--ink-brand-popup` (#f1f5f9) surface + `--ink-brand` (#334155) text（同 primary，因为品牌色已从靛蓝改为石墨靛蓝，不再有独立的"浅靛蓝"语义）
- `tone="warm"` -> `--status-warning-surface-l1` + `--status-warning-default` text
- `tone="neutral"` -> `--bg-overlay-l1` + `--text-secondary` text
- 保留 `rounded-full`（pill 语义合理）

**`empty-state.tsx`**：
- 从 panel-card 包裹改为直接使用 TRAE Work `ds-empty` 类（居中 flex + dashed border + `radius-12`）
- CTA 按钮改用 `ds-btn ds-btn--primary`（`--radius-8`，高度 28px）
- 图标迁移到 TRAE Work SVG

**`ink-select.tsx`**：
- 输入框从 `rounded-[18px]` 改为使用 `ds-select` 类（`--radius-8` + `--border-neutral-l1` + 32px 高度）
- focus 态由 `ds-select:focus` 处理（`border-contrast`），不再需要自定义 focus ring
- 下拉面板从 shadow-paper 改为 `ds-menu` 类

### 3.4 Layer 4: 工作台组件

**`dev-run-console.tsx`**（首页，改动最大）：
- **去掉 `paper-card` 包裹列表项**：任务列表改为纯 layout，用行分隔线或行 hover 区分
- **新建任务表单**：从 paper-card 改为 bg-base-secondary 容器，输入框 rounded-lg
- **任务概览统计**：从 5 列 paper-card 改为 inline metric strip
- **空状态**：保持但去掉 paper-card，改为居中排版
- **HealthDigest**：迁移 status token
- **statusBadge / typeBadge**：迁移到 TRAE Work status-pill

**`vault-init-card.tsx`**：
- 选择卡片从 `rounded-2xl border-2` 改为 `rounded-lg border` + `bg-overlay-l1` 选中态
- 结构预览区保持 `bg-base-secondary`

**`wiki-card.tsx` / `source-card.tsx`**：
- 去掉 panel-card 包裹，改为 surface container
- 状态标签迁移到 status token

**`review-card.tsx`**：
- 保持结构，但内部区块从 `rounded-[22px] bg-ink-low` 改为 `rounded-lg bg-overlay-l1`
- Claim 卡片同理收敛圆角

**`ask-workspace.tsx` / `ask-answer-panel.tsx` / `ask-answer-card.tsx`**：
- 提问表单从 paper-card 改为 bg-base-secondary
- 知识缺口区块从 `bg-[#fff5e9]` 改为 `status-warning-surface-l1`
- follow-up 链接从 `bg-ink-low rounded-[22px]` 改为 `bg-overlay-l1 rounded-lg`
- 外部来源区块同理

**`raw-import-panel.tsx`**：
- Tab 切换从药丸按钮改为 TRAE Work `.ds-tabs` 风格
- 表单输入框收敛圆角

**`conversation-history-rail.tsx`**：
- 卡片从 `rounded-[28px] bg-white shadow-paper` 改为 `rounded-lg bg-base-secondary border border-neutral-l1`
- 历史条目从 `rounded-[24px] border` 改为 `rounded-md` + 左侧 border accent

**`selection-deposit.tsx`**：
- 浮层从 `bg-ink-text text-white rounded-2xl` 改为 TRAE Work tooltip/menu 风格
- 错误提示迁移到 status-error-surface

### 3.5 Layer 5: 剩余页面

以下页面的改动模式与 Layer 4 一致，核心是：
1. `paper-card` -> bg-base-secondary rounded-lg
2. `ink-*` -> TRAE Work token
3. `rounded-[18~28px]` -> rounded-lg (8px)
4. 状态色 -> status token

涉及的页面：
- `app/ask/page.tsx`
- `app/raw/page.tsx`
- `app/ingest/page.tsx`
- `app/wiki/page.tsx` + `app/wiki/[id]/page.tsx`
- `app/runs/page.tsx` + `app/runs/[id]/page.tsx`
- `app/compile/page.tsx` + `app/compile/[id]/page.tsx`
- `app/health/page.tsx`

---

## 4. 前端技能路由对照

根据 TRAE Work 的 frontend-skill 规范，Inkdesk 属于 **App UI** 类型，适用以下约束：

| frontend-skill 规则 | Inkdesk 适配 |
|---------------------|-------------|
| calm surface hierarchy | 用 bg-base-default / secondary / overlay-l1 三层，去掉阴影 |
| strong typography and spacing | heading-* + body-* token 承载层级 |
| few colors | 石墨靛蓝品牌色 + 中性灰 + status 语义色 |
| dense but readable | 保持 14px 基线，信息密集处用 body-sm |
| minimal chrome | 去掉装饰渐变、阴影、超大圆角 |
| cards only when the card is the interaction | 任务行、表单面板保留卡片；列表项、统计区去掉 |
| no decorative gradients behind routine product UI | 去掉 radial-gradient 背景 |
| no ornamental icons | 图标只在功能需要时出现 |

---

## 5. 不改动的部分

| 项目 | 原因 |
|------|------|
| 业务逻辑 / 状态管理 | 纯视觉层重构 |
| 路由结构 | 信息架构不变 |
| 组件 props 接口 | 内部实现改，对外 API 不变 |
| 服务端 API 调用 | 不涉及 |
| Material Symbols 图标（短期） | 短期保留，后续逐步迁移到 TRAE Work SVG |
| 响应式断点 | 保持现有 lg/md 断点 |

---

## 6. 执行顺序

| 步骤 | 内容 | 影响范围 |
|------|------|---------|
| 1 | `tailwind.config.ts` token 重映射 | 全局 |
| 2 | `globals.css` 变量重定义 | 全局 |
| 3 | App Shell 组件 (header/sidebar/chrome) | 全局布局 |
| 4 | 共享 UI 原子 (panel-card/heading/stat-card/pill/empty-state) | 所有页面 |
| 5 | 工作台组件 (dev-run-console/vault-init/wiki-card 等) | 首页及子页面 |
| 6 | 剩余页面 (ask/raw/ingest/wiki/runs/compile/health) | 各独立页面 |

每步完成后在本地验证页面渲染正常再进入下一步。
