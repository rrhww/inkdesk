# Figma 管理与交付规范

## 目标

这份文档用于规范 Inkdesk 的 Figma 文件如何创建、如何命名、如何交付给前端，以及正式链接应该记录在哪里。

## 设计工具结论

- Figma 是 Inkdesk 的唯一正式设计源
- Google Stitch 只用于前期探索方向，不用于替代 Figma
- 最终交付给前端的页面、组件、交互说明都以 Figma 为准

## Figma 文件建议结构

建议至少建立以下页面分区：

- `00-cover`：项目封面和说明
- `01-ia`：信息架构和页面关系
- `02-wireframes`：低保真线框
- `03-foundations`：设计令牌和基础样式
- `04-components`：组件库
- `05-pages`：高保真页面
- `06-handoff`：开发交付页
- `07-prototype`：关键流程原型

## 命名规范

- 页面 frame 命名格式：`页面名 / 状态 / 端类型`
- 示例：
  - `登录页 / 默认 / desktop`
  - `笔记编辑页 / 保存中 / desktop`
  - `公开文章页 / 默认 / mobile`

## 开发交付要求

在 `06-handoff` 页面中，每个需要开发的页面至少包含：

- 页面最终稿
- 组件引用关系
- 交互说明
- 空状态和异常状态
- 尺寸和间距
- 响应式说明

## 本地归档路径

- Stitch 中间图归档：`assets/wireframes/stitch/`
- Figma 导出图归档：`assets/wireframes/figma/`

## 正式链接登记区

当前状态：待创建。

创建 Figma 文件后，把以下链接登记到本文件：

- 产品线框稿链接：
- 高保真设计稿链接：
- 开发交付页链接：
- 原型流程链接：

## 后续衔接点

- 设计链路说明见 `design/design-workflow.md`
- 第一阶段执行见 `design/prototype-plan.md`
- 页面级设计范围见 `design/page-inventory.md`
- 设计令牌规范见 `design/design-tokens.md`
