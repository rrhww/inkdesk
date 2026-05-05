# Search And Plans Read Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backend-backed search and plan read flows so `/app/search` and `/app/plans` can render real data while preserving mock fallback.

**Architecture:** Build search on top of existing knowledge entities, and add a minimal `plans` + `plan_notes` read model for the execution console. Keep backend DTOs small and let the Next.js adapter layer derive or supplement low-priority UI-only fields from existing fixtures.

**Tech Stack:** Spring Boot 3, Spring Data JPA, Flyway, H2 tests, Next.js App Router, TypeScript, Node test runner with `tsx`

---

### Task 1: Lock backend search behavior with failing tests

**Files:**
- Modify: `E:\dev\projects\inkvault\server\src\test\java\com\inkvault\server\knowledge\KnowledgeApiIntegrationTest.java`
- Create: `E:\dev\projects\inkvault\server\src\test\java\com\inkvault\server\search\SearchQueryServiceTest.java`
- Modify: `E:\dev\projects\inkvault\server\src\test\resources\testdata\knowledge-fixtures.sql`

- [ ] **Step 1: Write the failing test**

Add tests that assert:
- `/api/admin/search?q=agent` returns note results ordered by score
- `visibility`, `tag`, and `folder` filters narrow the result set
- blank query returns an empty list instead of an error

- [ ] **Step 2: Run test to verify it fails**

Run: `E:\dev\projects\inkvault\server\mvnw.cmd test`
Expected: FAIL because `/api/admin/search` and its service do not exist.

- [ ] **Step 3: Write minimal implementation**

Add:
- search DTOs and controller
- repository query reuse plus in-memory scoring in a dedicated service

- [ ] **Step 4: Run test to verify it passes**

Run: `E:\dev\projects\inkvault\server\mvnw.cmd test`
Expected: PASS for the new search tests.

### Task 2: Lock backend plans read behavior with failing tests

**Files:**
- Create: `E:\dev\projects\inkvault\server\src\test\java\com\inkvault\server\plans\PlanApiIntegrationTest.java`
- Create: `E:\dev\projects\inkvault\server\src\test\java\com\inkvault\server\plans\PlanQueryServiceTest.java`
- Modify: `E:\dev\projects\inkvault\server\src\test\resources\testdata\cleanup.sql`
- Modify: `E:\dev\projects\inkvault\server\src\test\resources\testdata\knowledge-fixtures.sql`

- [ ] **Step 1: Write the failing test**

Add tests that assert:
- `/api/admin/plans` requires the owner cookie
- the list includes active and queued plans
- missing plan-note relations do not raise a 500

- [ ] **Step 2: Run test to verify it fails**

Run: `E:\dev\projects\inkvault\server\mvnw.cmd test`
Expected: FAIL because plan tables, entities, and endpoint do not exist.

- [ ] **Step 3: Write minimal implementation**

Add:
- Flyway migration for `plans` and `plan_notes`
- plan entities, repository, service, controller
- local seed loader support

- [ ] **Step 4: Run test to verify it passes**

Run: `E:\dev\projects\inkvault\server\mvnw.cmd test`
Expected: PASS for the new plans tests.

### Task 3: Switch web search to the backend path

**Files:**
- Modify: `E:\dev\projects\inkvault\web\lib\search.ts`
- Modify: `E:\dev\projects\inkvault\web\app\app\search\page.tsx`
- Create: `E:\dev\projects\inkvault\web\tests\search-api.test.ts`

- [ ] **Step 1: Write the failing test**

Add tests that mock `fetch` and assert:
- search requests go to `/api/admin/search`
- search result notes render backend-backed values
- no API base URL still falls back to mock search

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- tests/search-api.test.ts`
Expected: FAIL because `web/lib/search.ts` still uses the mock source synchronously.

- [ ] **Step 3: Write minimal implementation**

Make the search helper async, forward the owner cookie, and adapt backend hits into existing `SearchResult`.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- tests/search-api.test.ts`
Expected: PASS

### Task 4: Switch web plans to the backend path

**Files:**
- Modify: `E:\dev\projects\inkvault\web\lib\plans.ts`
- Modify: `E:\dev\projects\inkvault\web\app\app\plans\page.tsx`
- Create: `E:\dev\projects\inkvault\web\tests\plans-api.test.tsx`

- [ ] **Step 1: Write the failing test**

Add tests that mock `fetch` and assert:
- plans requests go to `/api/admin/plans`
- linked knowledge comes from real note IDs
- mock fallback still works without API config

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- tests/plans-api.test.tsx`
Expected: FAIL because `web/lib/plans.ts` still uses mock data only.

- [ ] **Step 3: Write minimal implementation**

Make the plans helper async, adapt the backend list into `PlanWorkbenchData`, and resolve related knowledge through the knowledge helper.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- tests/plans-api.test.tsx`
Expected: PASS

### Task 5: Verify the slice end-to-end

**Files:**
- Modify: `E:\dev\projects\inkvault\web\README.md`

- [ ] **Step 1: Document the newly connected pages**

Update the README to note that search and plans now use the backend when configured.

- [ ] **Step 2: Run backend tests**

Run: `E:\dev\projects\inkvault\server\mvnw.cmd test`
Expected: PASS

- [ ] **Step 3: Run web tests**

Run: `npm test`
Expected: PASS

- [ ] **Step 4: Run the web production build**

Run: `npm run build`
Expected: PASS
