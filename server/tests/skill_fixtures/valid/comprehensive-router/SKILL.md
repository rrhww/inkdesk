---
name: comprehensive-router
description: 单一宽入口，根据用户意图路由到正确的领域 Skill。不处理具体的研发动作，只做意图识别和分发。如果意图不明确，列出候选 Skill 请用户选择。
---

# Comprehensive Router

## 核心目标与边界

接收用户描述的研发意图，分析后路由到最合适的领域 Skill。

**做什么：**
- 识别用户意图属于哪条链路（知识管理 / 研发自动化）
- 检查当前 Dev Run 状态，判断哪些阶段可进入
- 返回目标 Skill 和进入条件

**不做什么：**
- 不执行领域 Skill 的具体工作
- 不代替用户做关键决策
- 不绕过 Hard Gates 直接进入后续阶段

## Hard Gates

- vault_initialized: Vault 未初始化时停止，提示用户先初始化
- required_input: 用户意图描述不可为空

## 主流程

1. 接收用户意图描述
2. 检查 vault 和当前 Dev Run 状态
3. 匹配领域 Skill（优先完全匹配，其次部分匹配）
4. 若唯一匹配：返回该 Skill 及进入条件
5. 若多个匹配：列出候选，请用户选择
6. 若无匹配：提示无法识别，建议重新描述或手动选择

## 需要读取的资源

- contracts of all active domain skills
- current Dev Run state (if exists)

## 输出验证与下游衔接

- 输出：目标 Skill id + 进入条件
- 下游：由用户或 Harness 启动对应的领域 Skill
