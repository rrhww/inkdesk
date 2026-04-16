# Knowledge Read Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the public article and knowledge read-only pages in `web/` to the new Spring Boot backend while preserving a mock fallback for unimplemented domains.

**Architecture:** Add a small server-facing fetch layer plus adapter functions in `web/lib`, then switch only the public home, public article, knowledge hub, and note detail routes to consume those helpers. Keep plans, search, publish, and settings on the existing mock data path so this remains a narrow integration slice.

**Tech Stack:** Next.js App Router, React 19, TypeScript, Node test runner with `tsx`, Spring Boot JSON APIs

---

### Task 1: Add failing tests for backend-backed knowledge helpers

**Files:**
- Create: `E:\dev\projects\inkdesk\web\tests\knowledge-api.test.ts`
- Modify: `E:\dev\projects\inkdesk\web\package.json`

- [ ] **Step 1: Write the failing test**

Add tests that mock `globalThis.fetch` and assert:
- `getPublicHomeData()` prefers backend article data when an API base URL exists
- `getKnowledgeHubData("published")` restores folder names from `/api/admin/notes/tree`
- `getKnowledgeNoteById("note-001")` returns markdown content split into paragraphs plus published metadata

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- tests/knowledge-api.test.ts`
Expected: FAIL because the helper layer does not yet call the backend.

- [ ] **Step 3: Write minimal implementation**

Create backend fetch and adapter helpers under `web/lib` that:
- read the API base URL from environment
- request the public and admin knowledge endpoints
- fall back to the mock source when no base URL is configured

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- tests/knowledge-api.test.ts`
Expected: PASS

### Task 2: Switch the public pages to the new helpers

**Files:**
- Modify: `E:\dev\projects\inkdesk\web\app\page.tsx`
- Modify: `E:\dev\projects\inkdesk\web\components\public-home-view.tsx`
- Modify: `E:\dev\projects\inkdesk\web\app\articles\[slug]\page.tsx`
- Test: `E:\dev\projects\inkdesk\web\tests\repositioning.test.tsx`

- [ ] **Step 1: Add a failing page-level test**

Update the page tests to assert the public home and public article pages render data returned by the new helper layer rather than importing `mock-data.ts` directly.

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- tests/repositioning.test.tsx`
Expected: FAIL because the pages still read from `mock-data.ts`.

- [ ] **Step 3: Write minimal implementation**

Refactor the public pages so the route files fetch data from `web/lib/public.ts` and pass it into presentational components.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- tests/repositioning.test.tsx`
Expected: PASS

### Task 3: Switch the knowledge pages to the new helpers

**Files:**
- Modify: `E:\dev\projects\inkdesk\web\app\app\library\page.tsx`
- Modify: `E:\dev\projects\inkdesk\web\app\app\notes\[id]\page.tsx`
- Modify: `E:\dev\projects\inkdesk\web\components\editor-view.tsx`
- Modify: `E:\dev\projects\inkdesk\web\lib\knowledge.ts`
- Test: `E:\dev\projects\inkdesk\web\tests\repositioning.test.tsx`

- [ ] **Step 1: Add a failing page-level test**

Extend the existing tests so the library page and note page render values supplied by `web/lib/knowledge.ts`, including knowledge summary counts and note metadata.

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- tests/repositioning.test.tsx`
Expected: FAIL because the pages still resolve note data from `mock-data.ts`.

- [ ] **Step 3: Write minimal implementation**

Refactor the knowledge pages to:
- load hub/detail data through async helpers
- pass fully adapted note data into `EditorView`
- preserve current placeholder states like `blank` and `loading`

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- tests/repositioning.test.tsx`
Expected: PASS

### Task 4: Verify fallback behavior and build health

**Files:**
- Modify: `E:\dev\projects\inkdesk\web\README.md`

- [ ] **Step 1: Document the new API base URL**

Update the web README with the environment variable used to connect to the backend and note that mock fallback remains available.

- [ ] **Step 2: Run the full web test suite**

Run: `npm test`
Expected: PASS

- [ ] **Step 3: Run the production build**

Run: `npm run build`
Expected: PASS with the public and knowledge routes compiling successfully.
