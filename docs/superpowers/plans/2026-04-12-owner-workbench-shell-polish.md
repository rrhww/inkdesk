# Owner Workbench Shell Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strengthen the private `/app` experience so it feels like a real owner workbench, with a stronger Agent-first landing view and usable mobile navigation.

**Architecture:** Keep the existing route structure and page inventory intact, and concentrate changes in the shell, dashboard composition, and mock data. Reuse current styling tokens and component boundaries so the update stays front-end only and easy to verify with the existing tests plus one build run.

**Tech Stack:** Next.js App Router, React 19, TypeScript, Tailwind CSS, Node test runner with `tsx`

---

### Task 1: Expand mock workbench data

**Files:**
- Modify: `E:\dev\projects\inkvault\web\lib\mock-data.ts`
- Test: `E:\dev\projects\inkvault\web\tests\repositioning.test.tsx`

- [ ] **Step 1: Write the failing test**

Add assertions in `repositioning.test.tsx` that verify the mock data exposes a compact workbench summary for task count, private note count, and published item count.

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test`
Expected: a failing assertion because the new summary export does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add a derived export in `mock-data.ts` that summarizes:
- active plan count
- unpublished note count
- published note count

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test`
Expected: PASS

### Task 2: Polish the private shell

**Files:**
- Modify: `E:\dev\projects\inkvault\web\components\app-sidebar.tsx`
- Modify: `E:\dev\projects\inkvault\web\components\app-header.tsx`
- Modify: `E:\dev\projects\inkvault\web\app\app\layout.tsx`

- [ ] **Step 1: Add a failing UI-oriented test**

Extend `repositioning.test.tsx` to assert the shell renders mobile navigation language and keeps the primary nav order.

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test`
Expected: FAIL because the shell does not yet expose the new workbench navigation copy.

- [ ] **Step 3: Implement the shell update**

Add:
- current nav highlighting in the sidebar
- a lightweight mobile nav strip
- a stronger header context band for the main system

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test`
Expected: PASS

### Task 3: Recompose the Agent console

**Files:**
- Modify: `E:\dev\projects\inkvault\web\app\app\page.tsx`
- Modify: `E:\dev\projects\inkvault\web\app\globals.css`

- [ ] **Step 1: Add a failing UI-oriented test**

Extend `repositioning.test.tsx` to assert the Agent console exposes a workbench summary band and keeps Agent as the first visual section.

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test`
Expected: FAIL because the summary band and stronger first-screen copy do not exist yet.

- [ ] **Step 3: Implement the dashboard update**

Restructure `/app` into:
- a compact workbench summary band
- a larger Agent-first hero block
- clearer action cards for plans and notes

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test`
Expected: PASS

### Task 4: Verify the polished workbench

**Files:**
- Modify: `E:\dev\projects\inkvault\web\README.md`

- [ ] **Step 1: Update the web README**

Note that the private system now includes an Agent-first console and mobile-friendly shell navigation.

- [ ] **Step 2: Run the test suite**

Run: `npm test`
Expected: PASS with all tests green.

- [ ] **Step 3: Run the production build**

Run: `npm run build`
Expected: PASS with Next.js production build output.

- [ ] **Step 4: Re-open the private UI for inspection**

Run: `npm run start -- --port 3200`
Expected: app starts successfully so the updated shell and Agent console can be inspected in the browser.
