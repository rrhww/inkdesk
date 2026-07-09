# health-check-items

run-wiki-health 执行的所有检查项定义。每个检查项包含：检查对象、检测方法、严重度、报告格式。

## 检查项

### HC-01: frontmatter 完整性
- **对象**：所有 wiki 页面
- **检测**：检查是否包含 `name`、`status`、`updated_at` 字段
- **严重度**：缺少 `name` → ERROR；缺少 `updated_at` → WARN；缺少其他 → INFO
- **报告**：`页面路径 + 缺失字段列表`

### HC-02: 断链检测
- **对象**：所有 `[[wikilink]]` 和标准 markdown 链接
- **检测**：解析链接目标，检查目标文件是否存在
- **严重度**：`[[wikilink]]` 断链 → ERROR；外部链接 404 → WARN
- **跳过**：外部 HTTP URL 只做可达性标记，不阻塞

### HC-03: 孤页检测
- **对象**：所有 wiki 页面
- **检测**：没有被任何其他页面引用且不在 index.md 中的页面
- **严重度**：WARN
- **例外**：页面在 `index.md` 中列出 → 不算孤页

### HC-04: 短页检测
- **对象**：所有非 stub 页面
- **检测**：正文（不含 frontmatter）< 200 字
- **严重度**：WARN
- **例外**：`status: stub` 的页面豁免

### HC-05: 缺来源引用
- **对象**：所有 `status: accepted` 的页面
- **检测**：页面中无任何 `source:` 字段或对外部材料/对话的引用
- **严重度**：WARN
- **例外**：`status: draft` 或 `stub` 豁免

### HC-06: 时效性
- **对象**：所有页面
- **检测**：`updated_at` 距今 > 90 天 → stale；显式 `status: outdated` → outdated
- **严重度**：stale → INFO；outdated → WARN

### HC-07: 标题重复
- **对象**：所有页面的 `name` 字段
- **检测**：标题相似度 > 80% 的页面对
- **严重度**：INFO（提示可能重复，不自动判定为重复）

## 不做

- 不修改页面内容
- 不评判内容的正确性
