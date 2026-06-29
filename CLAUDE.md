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

## 学习模式

本项目默认使用 student-driver 学习模式（详见 `~/.claude/skills/student-driver/SKILL.md`）。说「你来」切换全权执行，说「回到学生模式」恢复。

## 认知地图

项目根目录维护 `cognitive-map.md`，每个非平凡任务结束时更新。

## 禁止行为

- 用「显然」「毫无疑问」替代推理
- 在决策点暗示正确答案（除非用户说「跳过这题」）
- 绕过架构决策
