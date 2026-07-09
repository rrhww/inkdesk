# proposal-template

wiki 变更提案的标准格式。ingest-source / deposit-answer / extract-insight 产出的 proposal 应遵循此模板。

## 提案结构

```markdown
# [提案标题] — 一行概括（动词开头的短句）

## 来源
- 原始材料：[文件路径 / 回答记录 / 对话来源]
- 提取时间：[ISO 时间]
- 提议者：[ingest-source | deposit-answer | extract-insight]

## 变更类型
- [ ] new — 新建页面
- [ ] update — 补充/更新已有页面
- [ ] deprecate — 标记过时

## 受影响页面
- `wiki/entities/xxx.md` — [变更说明]
- `wiki/concepts/yyy.md` — [变更说明]

## 变更内容

### 页面 1: [路径]
#### 目标段落
[引用目标段落]

#### 新增/替换内容
[具体内容，用 diff 风格或完整段落]

### 页面 2: [路径]
...

## 冲突标记
- [ ] 无冲突
- [ ] 与现有页面 `wiki/.../xxx.md` 的 [段落] 存在矛盾（原因：...）
- [ ] 待人类审阅确认

## 状态
- [ ] draft — 等待审阅
- [ ] stub — 不完整，仅标记主题
```

## 约束

- 一个 proposal 可以包含多个页面变更，但每次变更必须是单一职责（一个 proposal 不混合 new 和 deprecate 不同主题的页面）
- 冲突标记不能为空——要么显式标记「无冲突」，要么列出具体冲突
- stub proposal 的标题必须注明「[STUB]」前缀
