# 设计令牌

## 目标

这份文档定义 Inkvault 当前私有研究工作区的基础视觉规则，保证页面实现使用同一套颜色、间距、字体和组件尺度。

## 视觉方向

Inkvault 的视觉方向固定为：

- 安静
- 专业
- 清晰
- 偏知识系统，而不是社交产品

整体基调使用浅底和深色文本，强调色以绿色和青色系为主，避免紫色系通用模板感。

## 颜色令牌

### 中性色

- `color-bg-page`：页面主背景，偏浅暖灰
- `color-bg-panel`：卡片和面板背景，略深于页面背景
- `color-text-primary`：主文本色，深墨色
- `color-text-secondary`：辅助文本色，中灰
- `color-border-default`：默认边框色，低对比灰

### 品牌强调色

- `color-brand-primary`：主强调色，用于主按钮、激活态、链接强调
- `color-brand-primary-hover`：主强调色 hover
- `color-brand-soft`：浅强调背景，用于标签、提示区块

### 状态色

- `color-success`：成功状态
- `color-warning`：警告状态
- `color-danger`：错误状态
- `color-info`：信息状态

## 字体令牌

### 字体策略

- 中文正文优先选择适合长文阅读的无衬线或人文黑体
- 英文与代码采用独立代码字体
- 不使用系统默认视觉风格作为最终方案

### 字号层级

- `font-size-display`：首页主卡片或重要标题
- `font-size-h1`：模块页主标题
- `font-size-h2`
- `font-size-h3`
- `font-size-body-lg`
- `font-size-body`
- `font-size-caption`
- `font-size-code`

## 间距令牌

采用 4 的倍数体系，核心节奏如下：

- `space-1`：4
- `space-2`：8
- `space-3`：12
- `space-4`：16
- `space-5`：20
- `space-6`：24
- `space-8`：32
- `space-10`：40
- `space-12`：48

## 圆角令牌

- `radius-sm`：输入框、小标签
- `radius-md`：卡片、按钮
- `radius-lg`：面板、大卡片

MVP 不追求过大的圆角，整体风格偏克制。

## 阴影与边框

- 阴影只用于卡片层级区分，不用于制造夸张悬浮感
- 边框优先承担分层作用，阴影作为辅助手段
- 输入框、卡片、面板统一采用低对比边框

## 动效原则

- 动效服务于层级切换和状态反馈，不做花哨微动效堆叠
- 页面进入、侧栏切换、下拉菜单、保存状态提示允许存在轻量过渡
- 编辑器输入过程不引入干扰性动画

## 前端映射原则

前端主题变量建议至少映射以下分组：

- `--color-*`
- `--space-*`
- `--radius-*`
- `--shadow-*`
- `--font-size-*`

若前端采用 Tailwind CSS，应通过主题变量或 design token 文件统一映射，而不是在页面里散写颜色值。

## 后续衔接点

- 页面细节由 `design/page-inventory.md` 约束
- 路由与页面职责见 `design/information-architecture.md`
