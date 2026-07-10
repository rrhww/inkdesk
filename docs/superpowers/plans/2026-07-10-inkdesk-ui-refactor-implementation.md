# Inkdesk Dev Run Console 静态原型实施计划

## 目标

依据已批准的 [UI 重构设计](../specs/2026-07-10-inkdesk-ui-refactor-design.md)，在 `web/preview-dev-run-console/` 交付可通过 localhost 运行的单页静态 HTML 原型。原型覆盖 Overview、Dev Run、Review、Context Ask、Sources、Wiki、Skills、Evaluation 八个视图，并完成桌面、平板和移动端浏览器验收。

## 文件边界

| 文件 | 职责 |
| --- | --- |
| `web/preview-dev-run-console/index.html` | App shell、八视图语义结构、对话框、抽屉和一致的示例数据 |
| `web/preview-dev-run-console/styles.css` | 页面布局、响应式、局部组合样式、焦点与 reduced-motion；不重写 `.ds-*` 原子 |
| `web/preview-dev-run-console/app.js` | 视图路由、选择态、折叠、筛选、对话框、抽屉和表单反馈 |
| `web/preview-dev-run-console/assets/traework/` | TraeWork `colors_and_type.css`、`components.css` 与实际使用的本地图标只读快照 |
| `web/tests/preview-dev-run-console.test.mjs` | 静态契约测试：视图、导航、资源、品牌 CTA、禁用资源和可访问性锚点 |

## 任务 1：建立失败的静态契约测试

1. 新建 `web/tests/preview-dev-run-console.test.mjs`，使用 Node 内置 `node:test` 和 `assert`。
2. 断言目标目录必须包含 `index.html`、`styles.css`、`app.js`、两份 TraeWork CSS 和所需图标。
3. 断言 HTML 包含八个唯一的 `[data-view]`、四组导航、移动抽屉、新建 Run 对话框、skip link 和 live region。
4. 断言没有 Material Symbols、远程关键资源、emoji 结构图标、内联 SVG 或原始十六进制颜色。
5. 断言所有视图只包含一个持续品牌 CTA 语义入口“新建 Dev Run”。
6. 运行 `node --test tests/preview-dev-run-console.test.mjs`，确认因原型尚不存在而失败。

## 任务 2：建立 TraeWork 资源快照

1. 创建 `web/preview-dev-run-console/assets/traework/`。
2. 从 TraeWork 包复制 `colors_and_type.css` 和 `components.css`，保持内容不变。
3. 从 `assets/icons/` 复制导航和交互实际使用的 SVG，保留原文件名与几何结构。
4. 用哈希或逐字节比较验证两份 CSS 与源文件一致。

## 任务 3：实现 App Shell 与共享结构

1. 在 `index.html` 建立固定侧栏、移动顶部栏、主内容区、抽屉、对话框和 toast/live region。
2. 导航严格分为工作流、上下文、自动化、系统四组；Compile 不出现在一级导航。
3. 使用 `.ds-btn`、`.ds-input`、`.ds-select`、`.ds-card`、`.ds-tag`、`.ds-tabs`、`.ds-dialog`、`.ds-menu`、`.ds-table`、`.ds-alert` 等稳定原子。
4. 仅“新建 Dev Run”使用 `.ds-btn--brand`；阶段审批和普通命令使用中性按钮。
5. 所有功能图标来自本地 TraeWork SVG，默认 16px，紧凑 14px，辅助锚点 24px。

## 任务 4：实现八个视图

1. Overview：待确认、进行中 Run、最近完成、阻塞性 Health 摘要；不使用 KPI 卡片墙。
2. Dev Run：任务上下文、六阶段轨道、结构化工程事件流、证据和中性审批动作。
3. Review：跨 Run 过滤、审阅项列表、决策语义、风险和证据详情。
4. Context Ask：Run 作用域、带引用回答、证据充分度、知识缺口和 Deposit Proposal。
5. Sources：来源列表、处理状态、关联 Run、claim 与可追溯详情。
6. Wiki：主题列表、claim、证据、最后验证、使用记录和 open questions。
7. Skills：Skill 版本、状态、阶段、输入输出和关联 Evaluation。
8. Evaluation：明确“规划中 / 示例数据”，展示 Golden Task、rubric、失败样例与晋级门禁，不使用虚构增长图。

八个视图共享同一组 Run、Source、Claim、Skill 和 Evaluation 示例对象，界面文案使用中文并保留产品术语。

## 任务 5：实现交互和响应式

1. `app.js` 使用事件委托实现导航切换、`aria-current`、route hash 和路由后焦点移动。
2. 实现 Run 阶段切换、事件展开、Review 筛选、列表详情切换、引用展开和 Deposit Proposal 状态。
3. 实现移动抽屉的打开、Escape 关闭、焦点恢复和遮罩关闭。
4. 实现新建 Run 对话框的焦点循环、字段校验、取消、提交反馈和焦点恢复。
5. CSS 使用 1440 / 1024 / 768 / 375 响应式约束；移动端命中区域至少 44px，页面无横向滚动。
6. 动效限定为 120 / 200 / 300ms 和最多 4px 位移，reduced-motion 下关闭非必要动效。

## 任务 6：自动化与浏览器验收

1. 运行 `node --test tests/preview-dev-run-console.test.mjs`，所有静态契约通过。
2. 启动独立 localhost 静态服务，不占用现有 Next.js 服务端口。
3. 使用真实浏览器逐项验证八视图导航、Run 阶段、Review 筛选、Ask 引用、列表详情、抽屉和对话框。
4. 在 375、768、1024、1440 宽度截图并检查横向溢出、文本遮挡、资源缺失和布局跳动。
5. 检查控制台错误、失败请求、键盘可达性和 reduced-motion。
6. 对照 Spec 十项验收标准逐条记录证据；存在偏差时修正并重复测试。

## 完成证据

- 静态契约测试输出为零失败。
- TraeWork CSS 与源文件哈希一致，图标均来自本地设计库。
- 浏览器控制台零错误、关键资源零失败。
- 四个目标宽度的截图及 DOM 溢出检查通过。
- 八视图和规定交互均能通过键盘与鼠标操作。
- 工作树只新增计划、原型和测试，不覆盖现有未跟踪预览文件。
