# MVP Backend Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the Inkdesk MVP backend for local demo delivery by making local seed data idempotent and aligning backend documentation with the implemented API boundary.

**Architecture:** Keep the current Spring Boot domain model and controllers intact, and tighten the backend completion gate in two places: deterministic local seed backfill and documentation/API contract consistency. The code change should stay narrow by extending the existing local seed loaders instead of introducing new bootstrapping services or schema changes.

**Tech Stack:** Java 17, Spring Boot 3, Spring Data JPA, Flyway, H2 integration tests, Markdown docs

---

### Task 1: Make local knowledge seed backfill missing demo data

**Files:**
- Create: `C:\Users\whq\.codex\worktrees\cbe8\inkdesk\server\src\test\java\com\inkdesk\server\knowledge\LocalKnowledgeSeedLoaderIntegrationTest.java`
- Modify: `C:\Users\whq\.codex\worktrees\cbe8\inkdesk\server\src\main\java\com\inkdesk\server\knowledge\service\LocalKnowledgeSeedLoader.java`
- Reuse: `C:\Users\whq\.codex\worktrees\cbe8\inkdesk\server\src\test\resources\testdata\owner-without-settings.sql`

- [ ] **Step 1: Write the failing test**

```java
@SpringBootTest
@ActiveProfiles("test")
@Sql(scripts = {"/testdata/cleanup.sql", "/testdata/owner-without-settings.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
class LocalKnowledgeSeedLoaderIntegrationTest {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private WorkspaceRepository workspaceRepository;

    @Autowired
    private WorkspaceSettingsRepository workspaceSettingsRepository;

    @Autowired
    private TagRepository tagRepository;

    @Autowired
    private ContentNodeRepository contentNodeRepository;

    @Test
    void backfillsSettingsFoldersTagsAndNotesWhenOwnerAlreadyExists() throws Exception {
        LocalKnowledgeSeedLoader loader = new LocalKnowledgeSeedLoader(
                userRepository,
                workspaceRepository,
                workspaceSettingsRepository,
                tagRepository,
                contentNodeRepository
        );

        loader.run(new DefaultApplicationArguments(new String[0]));

        assertThat(userRepository.findByUsername("owner")).isPresent();
        assertThat(workspaceRepository.findBySlug("inkdesk")).isPresent();
        assertThat(workspaceSettingsRepository.findById("workspace-inkdesk")).isPresent();
        assertThat(tagRepository.findById("tag-agent")).isPresent();
        assertThat(contentNodeRepository.findById("folder-system-structure")).isPresent();
        assertThat(contentNodeRepository.findNoteByIdWithRelations("note-001")).isPresent();
        assertThat(contentNodeRepository.findNoteByIdWithRelations("note-002")).isPresent();
        assertThat(contentNodeRepository.findNoteByIdWithRelations("note-003")).isPresent();
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\mvnw.cmd test -Dtest=LocalKnowledgeSeedLoaderIntegrationTest`
Expected: FAIL because `LocalKnowledgeSeedLoader` returns as soon as the owner already exists and never backfills settings, tags, folders, or notes.

- [ ] **Step 3: Write minimal implementation**

```java
@Override
@Transactional
public void run(ApplicationArguments args) {
    Instant now = Instant.parse("2026-04-12T08:00:00Z");

    UserEntity owner = userRepository.findByUsername("owner")
            .orElseGet(() -> userRepository.save(buildOwner(now)));

    WorkspaceEntity workspace = workspaceRepository.findBySlug("inkdesk")
            .orElseGet(() -> workspaceRepository.save(buildWorkspace(owner, now)));

    if (workspaceSettingsRepository.findById(workspace.getId()).isEmpty()) {
        workspaceSettingsRepository.save(buildSettings(workspace, now));
    }

    TagEntity positioning = ensureTag("tag-positioning", workspace, "定位", "positioning", now);
    TagEntity superWorkbench = ensureTag("tag-super-workbench", workspace, "超级个人工作台", "super-workbench", now);
    TagEntity agent = ensureTag("tag-agent", workspace, "Agent", "agent", now);
    TagEntity homepage = ensureTag("tag-homepage", workspace, "首页", "homepage", now);
    TagEntity systemDesign = ensureTag("tag-system-design", workspace, "系统设计", "system-design", now);
    TagEntity publicSurface = ensureTag("tag-public", workspace, "公共面", "public-surface", now);
    TagEntity blog = ensureTag("tag-blog", workspace, "博客", "blog", now);
    TagEntity authorPortal = ensureTag("tag-author-portal", workspace, "作者门户", "author-portal", now);

    ContentNodeEntity folderProduct = ensureFolder("folder-product-reframe", workspace, "产品重构", 100, now);
    ContentNodeEntity folderSystem = ensureFolder("folder-system-structure", workspace, "主系统结构", 200, now);
    ContentNodeEntity folderPublic = ensureFolder("folder-public-design", workspace, "公共面设计", 300, now);

    ensureNote(
            "note-001",
            workspace,
            folderProduct,
            "把 Inkdesk 从知识库改造成超级个人工作台",
            110,
            Instant.parse("2026-04-12T08:10:00Z"),
            "重新定义公共面、主系统、Agent 控制台和任务计划在整个产品中的位置。",
            "# 把 Inkdesk 从知识库改造成超级个人工作台\n\n新的 Inkdesk 不再只是个人知识库加发布站，而是一个双面系统。",
            1120,
            Set.of(positioning, superWorkbench, agent),
            buildPublication("pub-001", "super-personal-workbench-reframe", PublicationStatus.PUBLISHED, Instant.parse("2026-04-12T08:20:00Z"), Instant.parse("2026-04-12T08:20:00Z"))
    );
    ensureNote(
            "note-002",
            workspace,
            folderSystem,
            "为什么主系统首页必须先看到 Agent",
            210,
            Instant.parse("2026-04-12T07:42:00Z"),
            "记录 Agent 控制台为何要成为主人进入系统后的第一屏，而不是笔记列表或发布页。",
            "# 为什么主系统首页必须先看到 Agent\n\n如果首页先看到的只是文档列表，系统会退化成存储工具。",
            860,
            Set.of(agent, homepage, systemDesign),
            buildPublication("pub-002", "why-agent-first", PublicationStatus.DRAFT, null, Instant.parse("2026-04-12T07:50:00Z"))
    );
    ensureNote(
            "note-003",
            workspace,
            folderPublic,
            "公共博客页作为作者门户的结构草案",
            310,
            Instant.parse("2026-04-12T06:58:00Z"),
            "公共面应该同时承载公开文章、作者介绍和长期项目入口，而不是产品官网式 landing page。",
            "# 公共博客页作为作者门户的结构草案\n\n公共面是别人理解作者与公开内容的入口，而不是进入私有系统的入口。",
            640,
            Set.of(publicSurface, blog, authorPortal),
            buildPublication("pub-003", "public-blog-author-portal", PublicationStatus.PUBLISHED, Instant.parse("2026-04-12T07:05:00Z"), Instant.parse("2026-04-12T07:05:00Z"))
    );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\mvnw.cmd test -Dtest=LocalKnowledgeSeedLoaderIntegrationTest`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/src/main/java/com/inkdesk/server/knowledge/service/LocalKnowledgeSeedLoader.java server/src/test/java/com/inkdesk/server/knowledge/LocalKnowledgeSeedLoaderIntegrationTest.java
git commit -m "test: stabilize local knowledge seed backfill"
```

### Task 2: Make local plan seed backfill missing plans without clobbering existing data

**Files:**
- Create: `C:\Users\whq\.codex\worktrees\cbe8\inkdesk\server\src\test\java\com\inkdesk\server\plans\LocalPlanSeedLoaderIntegrationTest.java`
- Create: `C:\Users\whq\.codex\worktrees\cbe8\inkdesk\server\src\test\resources\testdata\partial-plans.sql`
- Modify: `C:\Users\whq\.codex\worktrees\cbe8\inkdesk\server\src\main\java\com\inkdesk\server\plans\LocalPlanSeedLoader.java`

- [ ] **Step 1: Write the failing test**

```java
@SpringBootTest
@ActiveProfiles("test")
@Sql(
        scripts = {"/testdata/cleanup.sql", "/testdata/knowledge-fixtures.sql", "/testdata/partial-plans.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD
)
class LocalPlanSeedLoaderIntegrationTest {

    @Autowired
    private PlanRepository planRepository;

    @Autowired
    private WorkspaceRepository workspaceRepository;

    @Autowired
    private ContentNodeRepository contentNodeRepository;

    @Test
    void backfillsMissingDefaultPlansWhenDatabaseAlreadyContainsOnePlan() throws Exception {
        LocalPlanSeedLoader loader = new LocalPlanSeedLoader(planRepository, workspaceRepository, contentNodeRepository);

        loader.run(new DefaultApplicationArguments(new String[0]));

        assertThat(planRepository.findById("plan-001")).isPresent();
        assertThat(planRepository.findById("plan-002")).isPresent();
        assertThat(planRepository.findById("plan-003")).isPresent();
        assertThat(planRepository.count()).isEqualTo(3);
    }
}
```

`partial-plans.sql`

```sql
INSERT INTO plans (
  id, workspace_id, title, summary, status, horizon, priority, focus_label,
  next_step, next_action_label, next_action_href, search_term, agent_prompt, created_at, updated_at
) VALUES (
  'plan-001', 'workspace-inkdesk', '重构公共面与主系统的双面入口', '先把公开博客入口、隐藏登录入口和主系统骨架彻底分开。',
  'ACTIVE', 'TODAY', 'CRITICAL', '系统入口', '把访客入口、隐藏登录和主系统跳转链路再检查一轮。',
  '检查入口链路', '/app/search?q=%E5%85%AC%E5%85%B1%E9%9D%A2', '公共面',
  '把双面系统的入口规则压缩成一份可执行检查清单。',
  TIMESTAMP WITH TIME ZONE '2026-04-12 10:30:00+00', TIMESTAMP WITH TIME ZONE '2026-04-12 10:30:00+00'
);
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\mvnw.cmd test -Dtest=LocalPlanSeedLoaderIntegrationTest`
Expected: FAIL because `LocalPlanSeedLoader` exits on `planRepository.count() > 0` and never backfills `plan-002` or `plan-003`.

- [ ] **Step 3: Write minimal implementation**

```java
@Override
@Transactional
public void run(ApplicationArguments args) {
    var workspace = workspaceRepository.findBySlug("inkdesk").orElse(null);
    if (workspace == null) {
        return;
    }

    ensurePlan(
            workspace,
            "plan-001",
            "重构公共面与主系统的双面入口",
            "先把公开博客入口、隐藏登录入口和主系统骨架彻底分开。",
            PlanStatus.ACTIVE,
            PlanHorizon.TODAY,
            PlanPriority.CRITICAL,
            "系统入口",
            "把访客入口、隐藏登录和主系统跳转链路再检查一轮。",
            "检查入口链路",
            "/app/search?q=%E5%85%AC%E5%85%B1%E9%9D%A2",
            "公共面",
            "把双面系统的入口规则压缩成一份可执行检查清单。",
            Instant.parse("2026-04-12T10:30:00Z"),
            Set.of("note-003", "note-001")
    );
    ensurePlan(
            workspace,
            "plan-002",
            "补齐 Agent 控制台的核心模块",
            "让首页真正具备上下文汇总、任务推进和知识召回三个功能面。",
            PlanStatus.ACTIVE,
            PlanHorizon.THIS_WEEK,
            PlanPriority.FOCUS,
            "Agent 首页",
            "把 Agent 首页与任务、知识中枢之间的跳转再压缩成更短的行动路径。",
            "打开 Agent 控制台",
            "/app",
            "Agent",
            "从当前笔记和计划里提炼今天最值得推进的一件事。",
            Instant.parse("2026-04-12T09:56:00Z"),
            Set.of("note-001", "note-002")
    );
    ensurePlan(
            workspace,
            "plan-003",
            "让发布模块退到次级位置",
            "保留公开输出能力，但不再让它主导整个平台的叙事与导航。",
            PlanStatus.QUEUED,
            PlanHorizon.NEXT,
            PlanPriority.STEADY,
            "公共输出",
            "只保留稳定的知识输出路径，把公开文章继续留在次级模块里。",
            "查看发布模块",
            "/app/publish",
            "公开文章",
            "判断哪些知识资产已经成熟到可以同步到公共面。",
            Instant.parse("2026-04-12T09:10:00Z"),
            Set.of("note-003")
    );
}

private void ensurePlan(
        WorkspaceEntity workspace,
        String id,
        String title,
        String summary,
        PlanStatus status,
        PlanHorizon horizon,
        PlanPriority priority,
        String focusLabel,
        String nextStep,
        String nextActionLabel,
        String nextActionHref,
        String searchTerm,
        String agentPrompt,
        Instant updatedAt,
        Set<String> relatedNoteIds
) {
    if (planRepository.existsById(id)) {
        return;
    }

    planRepository.save(buildPlan(
            workspace,
            id,
            title,
            summary,
            status,
            horizon,
            priority,
            focusLabel,
            nextStep,
            nextActionLabel,
            nextActionHref,
            searchTerm,
            agentPrompt,
            updatedAt,
            relatedNoteIds
    ));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\mvnw.cmd test -Dtest=LocalPlanSeedLoaderIntegrationTest`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/src/main/java/com/inkdesk/server/plans/LocalPlanSeedLoader.java server/src/test/java/com/inkdesk/server/plans/LocalPlanSeedLoaderIntegrationTest.java server/src/test/resources/testdata/partial-plans.sql
git commit -m "test: stabilize local plan seed backfill"
```

### Task 3: Align backend documentation with the implemented MVP boundary

**Files:**
- Modify: `C:\Users\whq\.codex\worktrees\cbe8\inkdesk\server\README.md`
- Modify: `C:\Users\whq\.codex\worktrees\cbe8\inkdesk\docs\architecture\api-draft.md`
- Modify: `C:\Users\whq\.codex\worktrees\cbe8\inkdesk\docs\delivery\local-fullstack-acceptance.md`
- Modify: `C:\Users\whq\.codex\worktrees\cbe8\inkdesk\docs\architecture\tooling-and-mcp.md`

- [ ] **Step 1: Capture current drift**

Run:

```powershell
Select-String -Path server\README.md,docs\architecture\api-draft.md,docs\delivery\local-fullstack-acceptance.md,docs\architecture\tooling-and-mcp.md -Pattern "/api/admin/home|/api/admin/search|snapshot|JDK 21|JDK 17"
```

Expected: output shows that `server/README.md` does not list `home/search`, `api-draft.md` still documents `POST /api/admin/notes/{id}/snapshot`, and `tooling-and-mcp.md` still says `JDK 21`.

- [ ] **Step 2: Update the docs**

`server/README.md`

```md
## 当前接口

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /actuator/health`
- `GET /api/admin/home`
- `GET /api/admin/settings`
- `PATCH /api/admin/settings`
- `GET /api/admin/notes/tree`
- `POST /api/admin/notes`
- `GET /api/admin/notes/{id}`
- `PATCH /api/admin/notes/{id}`
- `POST /api/admin/notes/{id}/publish`
- `POST /api/admin/notes/{id}/unpublish`
- `GET /api/admin/plans`
- `POST /api/admin/plans`
- `PATCH /api/admin/plans/{id}`
- `GET /api/admin/search`
- `GET /api/public/articles`
- `GET /api/public/articles/{slug}`
```

`docs/architecture/api-draft.md`

```md
## 三、笔记接口

### `GET /api/admin/notes/tree`
### `GET /api/admin/notes/{id}`
### `POST /api/admin/notes`
### `PATCH /api/admin/notes/{id}`

## 六、设置接口

### `GET /api/admin/settings`
### `PATCH /api/admin/settings`

## 备注

- 当前不做 `POST /api/admin/notes/{id}/snapshot`
```

`docs/delivery/local-fullstack-acceptance.md`

```md
1. 访问 `http://localhost:3000/login`
2. 登录后确认 `/app` 首页可以看到真实 `Agent` 工作台摘要
3. 打开 `/app/search?q=Agent`，确认能返回真实知识结果
4. 打开 `/app/plans`，确认计划与关联知识可见
```

`docs/architecture/tooling-and-mcp.md`

```md
- `JDK 17`
```

- [ ] **Step 3: Re-run the drift check**

Run:

```powershell
Select-String -Path server\README.md,docs\architecture\api-draft.md,docs\delivery\local-fullstack-acceptance.md,docs\architecture\tooling-and-mcp.md -Pattern "/api/admin/home|/api/admin/search|snapshot|JDK 21|JDK 17"
```

Expected: `home/search` are present, `JDK 17` is present, and `snapshot` only appears in an explicit “not in MVP” note.

- [ ] **Step 4: Commit**

```bash
git add server/README.md docs/architecture/api-draft.md docs/delivery/local-fullstack-acceptance.md docs/architecture/tooling-and-mcp.md
git commit -m "docs: align backend mvp boundary"
```

### Task 4: Verify the backend completion slice end-to-end

**Files:**
- Verify only: `C:\Users\whq\.codex\worktrees\cbe8\inkdesk\server`

- [ ] **Step 1: Run the targeted seed loader tests**

Run:

```powershell
cd server
.\mvnw.cmd test -Dtest=LocalKnowledgeSeedLoaderIntegrationTest,LocalPlanSeedLoaderIntegrationTest
```

Expected: PASS

- [ ] **Step 2: Run the full backend test suite**

Run:

```powershell
cd server
.\mvnw.cmd test
```

Expected: PASS

- [ ] **Step 3: Inspect the final diff**

Run:

```powershell
git status --short
git diff --stat
```

Expected: only the seed-loader code, the new tests/fixture, the plan/spec docs, and the backend docs are changed.

- [ ] **Step 4: Commit the remaining work**

```bash
git add server docs
git commit -m "feat: close mvp backend completion gaps"
```
