# Chat-First Research Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the authenticated Inkdesk frontend into a Chinese, chat-first research shell where `/app` becomes the primary `问答` workspace while preserving the vault-first `资料 / 审阅 / 知识库` workflow.

**Architecture:** Keep the existing Next.js App Router and Python-backed API contract, but replace the dashboard-style shell with repo-native chat-shell components inspired by assistant-ui. Use a small localStorage-backed ask-history adapter for the left rail, server-render the workspace pages with thin data-fetching routes, and reuse existing Ask/Raw/Ingest/Wiki server actions so the backend stays untouched.

**Tech Stack:** Next.js 15 App Router, React 19, TypeScript, Tailwind CSS, node:test, Vitest, Playwright

---

## Planned File Map

- Create: `web/lib/app-shell.ts`
  - Central Chinese section metadata, active-route matching, and fallback history builders.
- Create: `web/lib/ask-history.ts`
  - Browser-safe read/write/merge helpers for recent ask threads stored in localStorage.
- Modify: `web/lib/types.ts`
  - Add `ResearchAskHistoryEntry` and shell-oriented view models.
- Modify: `web/lib/mock/research-fixtures.ts`
  - Supply starter history/fallback data aligned with the new shell.
- Create: `web/components/shell/top-section-tabs.tsx`
  - Top Chinese section tabs for `问答 / 资料 / 审阅 / 知识库`.
- Create: `web/components/shell/conversation-history-rail.tsx`
  - Left history-first rail with local history and starter threads.
- Create: `web/components/workbench/ask-workspace.tsx`
  - Main chat-style workspace shared by `/app` and `/app/ask`.
- Create: `web/components/workbench/ask-composer.tsx`
  - Bottom composer with textarea, topic picker, mode switch, and submit button.
- Create: `web/components/workbench/ask-message-list.tsx`
  - Conversation-style renderer for question, answer, follow-up prompts, and citations.
- Create: `web/components/workbench/research-context-panel.tsx`
  - Right research sidebar showing sources, gaps, topic scope, and writeback action.
- Create: `web/components/workbench/ask-history-recorder.tsx`
  - Client-side mount hook that persists the current ask turn into local history.
- Create: `web/components/workbench/raw-workspace.tsx`
  - Chinese object-style `资料` page shell.
- Create: `web/components/workbench/review-workspace.tsx`
  - Chinese object-style `审阅` page shell.
- Create: `web/components/workbench/wiki-workspace.tsx`
  - Chinese object-style `知识库` list page shell.
- Create: `web/components/workbench/wiki-detail-workspace.tsx`
  - Chinese detail view for current understanding, claims, open questions, sources, and thread.
- Modify: `web/components/app-sidebar.tsx`
  - Turn the old nav sidebar into a wrapper around `ConversationHistoryRail`.
- Modify: `web/components/app-header.tsx`
  - Turn the old metric header into the top-tab shell header.
- Modify: `web/app/app/layout.tsx`
  - Mount the new left rail, top tabs, and shared shell frame.
- Modify: `web/app/app/page.tsx`
  - Replace dashboard home with the ask workspace.
- Modify: `web/app/app/ask/page.tsx`
  - Reuse the shared ask workspace instead of the old two-card layout.
- Modify: `web/app/app/raw/page.tsx`
  - Delegate to `RawWorkspace`.
- Modify: `web/app/app/ingest/page.tsx`
  - Delegate to `ReviewWorkspace`.
- Modify: `web/app/app/wiki/page.tsx`
  - Delegate to `WikiWorkspace`.
- Modify: `web/app/app/wiki/[id]/page.tsx`
  - Delegate to `WikiDetailWorkspace` and convert visible labels to Chinese.
- Modify: `web/app/app/loading.tsx`
  - Replace dashboard skeleton with shell/chat skeleton.
- Modify: `web/app/globals.css`
  - Add chat-shell layout, rail, composer, and research-panel styles.
- Delete: `web/components/workbench/research-dashboard.tsx`
  - Old dashboard component no longer used by the main path.
- Modify: `web/tests/research-pages.test.tsx`
  - Assert the new `/app` ask-first shell, Chinese naming, and chat flow.
- Modify: `web/tests/unit/workbench-components.test.tsx`
  - Replace dashboard assertions with shell and workspace component assertions.
- Create: `web/tests/unit/app-shell.test.ts`
  - Validate shell metadata and local history merge behavior.
- Modify: `web/tests/e2e/local-fullstack.spec.ts`
  - Verify `/app` lands on `问答`, supports follow-up, and keeps the other Chinese workspaces reachable.

### Task 1: Establish shell metadata and local ask-history primitives

**Files:**
- Create: `web/lib/app-shell.ts`
- Create: `web/lib/ask-history.ts`
- Modify: `web/lib/types.ts`
- Modify: `web/lib/mock/research-fixtures.ts`
- Create: `web/tests/unit/app-shell.test.ts`

- [ ] **Step 1: Write the failing unit test for Chinese sections and ask-history merge**

```ts
import { describe, expect, it } from "vitest";

import { PRIMARY_SECTIONS, buildStarterHistory } from "@/lib/app-shell";
import { mergeAskHistoryEntry } from "@/lib/ask-history";

describe("app shell primitives", () => {
  it("exposes Chinese primary sections in product order", () => {
    expect(PRIMARY_SECTIONS.map((item) => item.label)).toEqual(["问答", "资料", "审阅", "知识库"]);
    expect(PRIMARY_SECTIONS.map((item) => item.href)).toEqual(["/app", "/app/raw", "/app/ingest", "/app/wiki"]);
  });

  it("merges current ask turns ahead of starter history and removes duplicates", () => {
    const starter = buildStarterHistory({
      suggestedQuestions: ["raw 和 wiki 的边界是什么？"],
      focusTopicTitle: "Inkdesk repositioning"
    });

    const merged = mergeAskHistoryEntry(starter, {
      id: "ask-topic-001",
      title: "这个主题当前最稳定的理解是什么？",
      href: "/app?q=%E8%BF%99%E4%B8%AA%E4%B8%BB%E9%A2%98%E5%BD%93%E5%89%8D%E6%9C%80%E7%A8%B3%E5%AE%9A%E7%9A%84%E7%90%86%E8%A7%A3%E6%98%AF%E4%BB%80%E4%B9%88%EF%BC%9F&topicId=topic-001",
      topicTitle: "Inkdesk repositioning",
      preview: "当前最稳定的理解是 wiki 是新的核心对象。",
      updatedAt: "2026-05-03T03:00:00Z"
    });

    expect(merged[0]?.id).toBe("ask-topic-001");
    expect(merged[0]?.topicTitle).toBe("Inkdesk repositioning");
    expect(merged).toHaveLength(2);
  });
});
```

- [ ] **Step 2: Run the new unit test to verify it fails**

Run: `npx vitest run tests/unit/app-shell.test.ts`

Expected: FAIL with `Cannot find module '@/lib/app-shell'` and `Cannot find module '@/lib/ask-history'`.

- [ ] **Step 3: Write the minimal shell metadata, history types, and localStorage helpers**

```ts
// web/lib/types.ts
export type ResearchAskHistoryEntry = {
  id: string;
  title: string;
  href: string;
  topicTitle?: string | null;
  preview: string;
  updatedAt: string;
};
```

```ts
// web/lib/app-shell.ts
import type { ResearchAskHistoryEntry } from "@/lib/types";

export const PRIMARY_SECTIONS = [
  { href: "/app", label: "问答", matchers: ["/app", "/app/ask"] },
  { href: "/app/raw", label: "资料", matchers: ["/app/raw", "/app/inbox", "/app/sources"] },
  { href: "/app/ingest", label: "审阅", matchers: ["/app/ingest", "/app/review"] },
  { href: "/app/wiki", label: "知识库", matchers: ["/app/wiki", "/app/topics"] }
] as const;

export function buildStarterHistory(input: {
  suggestedQuestions: string[];
  focusTopicTitle?: string | null;
}): ResearchAskHistoryEntry[] {
  return input.suggestedQuestions.slice(0, 3).map((question, index) => ({
    id: `starter-${index + 1}`,
    title: question,
    href: `/app?q=${encodeURIComponent(question)}`,
    topicTitle: input.focusTopicTitle ?? "研究入口",
    preview: "从这里开始新的研究追问。",
    updatedAt: "2026-05-03T00:00:00Z"
  }));
}
```

```ts
// web/lib/ask-history.ts
import type { ResearchAskHistoryEntry } from "@/lib/types";

export const ASK_HISTORY_STORAGE_KEY = "inkdesk.askHistory";

export function readAskHistory(): ResearchAskHistoryEntry[] {
  if (typeof window === "undefined") {
    return [];
  }

  const raw = window.localStorage.getItem(ASK_HISTORY_STORAGE_KEY);
  if (!raw) {
    return [];
  }

  try {
    return JSON.parse(raw) as ResearchAskHistoryEntry[];
  } catch {
    return [];
  }
}

export function writeAskHistory(entries: ResearchAskHistoryEntry[]) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(ASK_HISTORY_STORAGE_KEY, JSON.stringify(entries));
}

export function mergeAskHistoryEntry(
  current: ResearchAskHistoryEntry[],
  next: ResearchAskHistoryEntry
): ResearchAskHistoryEntry[] {
  const deduped = current.filter((item) => item.id !== next.id && item.href !== next.href);
  return [next, ...deduped].slice(0, 12);
}
```

- [ ] **Step 4: Run the unit test again to verify it passes**

Run: `npx vitest run tests/unit/app-shell.test.ts`

Expected: PASS with `2 passed`.

- [ ] **Step 5: Commit the primitive layer**

```bash
git add web/lib/types.ts web/lib/app-shell.ts web/lib/ask-history.ts web/lib/mock/research-fixtures.ts web/tests/unit/app-shell.test.ts
git commit -m "feat: add chat shell primitives"
```

### Task 2: Replace the dashboard shell with a history-first app frame

**Files:**
- Create: `web/components/shell/top-section-tabs.tsx`
- Create: `web/components/shell/conversation-history-rail.tsx`
- Modify: `web/components/app-sidebar.tsx`
- Modify: `web/components/app-header.tsx`
- Modify: `web/app/app/layout.tsx`
- Modify: `web/tests/unit/workbench-components.test.tsx`

- [ ] **Step 1: Write the failing component test for the new shell frame**

```tsx
import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppSidebarContent } from "@/components/app-sidebar";
import { AppHeader } from "@/components/app-header";
import { researchDashboardFixture } from "@/lib/mock/research-fixtures";

describe("chat-first shell", () => {
  it("renders Chinese top tabs and history-first rail", () => {
    render(
      <>
        <AppHeader
          title="问答"
          contextItems={[
            { label: "当前模式", value: "仅基于知识库" },
            { label: "待审阅", value: "3 条" }
          ]}
        />
        <AppSidebarContent pathname="/app" snapshot={researchDashboardFixture} />
      </>
    );

    expect(screen.getByRole("link", { name: "问答" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "资料" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "审阅" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "知识库" })).toBeInTheDocument();
    expect(screen.getByText("最近对话")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "新建对话" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the component test to verify it fails**

Run: `npx vitest run tests/unit/workbench-components.test.tsx`

Expected: FAIL because `snapshot` is not a valid prop on `AppSidebarContent` and the new labels are missing.

- [ ] **Step 3: Implement the shell components and wire them into the layout**

```tsx
// web/components/shell/top-section-tabs.tsx
import Link from "next/link";
import { PRIMARY_SECTIONS } from "@/lib/app-shell";

export function TopSectionTabs({ pathname }: { pathname: string }) {
  return (
    <nav aria-label="主导航" className="flex flex-wrap gap-2">
      {PRIMARY_SECTIONS.map((item) => {
        const active = item.matchers.some((matcher) => pathname === matcher || pathname.startsWith(`${matcher}/`));
        return (
          <Link
            key={item.href}
            aria-current={active ? "page" : undefined}
            className={active ? "rounded-full bg-ink-primary px-4 py-2 text-white" : "rounded-full bg-white px-4 py-2 text-ink-muted"}
            href={item.href}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
```

```tsx
// web/components/shell/conversation-history-rail.tsx
"use client";

import { useMemo } from "react";
import Link from "next/link";
import { buildStarterHistory } from "@/lib/app-shell";
import { readAskHistory } from "@/lib/ask-history";
import type { ResearchDashboard } from "@/lib/types";

export function ConversationHistoryRail({ pathname, snapshot }: { pathname: string; snapshot: ResearchDashboard }) {
  const entries = useMemo(() => {
    const stored = readAskHistory();
    return stored.length
      ? stored
      : buildStarterHistory({
          suggestedQuestions: snapshot.suggestedQuestions,
          focusTopicTitle: snapshot.focusTopic?.title
        });
  }, [snapshot.focusTopic?.title, snapshot.suggestedQuestions]);

  return (
    <aside className="flex h-full flex-col gap-6">
      <button className="rounded-full bg-ink-primary px-4 py-3 text-sm font-semibold text-white" type="button">
        新建对话
      </button>
      <div>
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">最近对话</div>
        <div className="mt-3 space-y-2">
          {entries.map((entry) => (
            <Link key={entry.id} className={pathname === "/app" ? "block rounded-[18px] bg-white px-4 py-3" : "block rounded-[18px] bg-ink-low px-4 py-3"} href={entry.href}>
              <div className="text-sm font-semibold text-ink-text">{entry.title}</div>
              <div className="mt-1 text-xs text-ink-muted">{entry.topicTitle}</div>
            </Link>
          ))}
        </div>
      </div>
    </aside>
  );
}
```

```tsx
// web/components/app-header.tsx
import { TopSectionTabs } from "@/components/shell/top-section-tabs";

export function AppHeader({ title, subtitle, contextItems, action }: AppHeaderProps) {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-30 border-b border-black/5 bg-white/80 backdrop-blur-lg">
      <div className="flex min-h-16 items-center justify-between gap-6 px-6 py-4 lg:px-8">
        <div>
          <h1 className="font-headline text-xl font-extrabold tracking-tight text-ink-text">{title}</h1>
          {subtitle ? <p className="mt-1 text-sm text-ink-muted">{subtitle}</p> : null}
        </div>
        {action}
      </div>
      <div className="border-t border-black/5 px-6 py-3 lg:px-8">
        <TopSectionTabs pathname={pathname} />
      </div>
      {contextItems?.length ? (
        <div className="border-t border-black/5 px-6 py-3 lg:px-8">
          <div className="flex flex-wrap gap-3">
            {contextItems.map((item) => (
              <div key={item.label} className="rounded-full bg-ink-low px-4 py-2 text-sm text-ink-muted">
                <span className="font-semibold text-ink-text">{item.value}</span>
                <span className="ml-2">{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </header>
  );
}
```

```tsx
// web/app/app/layout.tsx
<div className="min-h-screen bg-ink-bg shell-grid">
  <AppSidebar snapshot={snapshot} />
  <div className="min-w-0">
    <AppHeader
      title="问答"
      subtitle="围绕私人研究记忆提问、追问与沉淀"
      contextItems={[
        { label: "当前模式", value: "Vault-first" },
        { label: "知识页", value: `${snapshot.summary.activeTopics} 个` },
        { label: "待审阅", value: `${snapshot.summary.pendingReviews} 条` }
      ]}
      action={<form action={logoutAction}><button className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-ink-text">退出</button></form>}
    />
    {children}
  </div>
</div>
```

- [ ] **Step 4: Run the component test again to verify it passes**

Run: `npx vitest run tests/unit/workbench-components.test.tsx`

Expected: PASS with the new shell assertions succeeding.

- [ ] **Step 5: Commit the shell frame**

```bash
git add web/components/shell/top-section-tabs.tsx web/components/shell/conversation-history-rail.tsx web/components/app-sidebar.tsx web/components/app-header.tsx web/app/app/layout.tsx web/tests/unit/workbench-components.test.tsx
git commit -m "feat: add chat-first app shell"
```

### Task 3: Promote `/app` into the shared ask workspace

**Files:**
- Create: `web/components/workbench/ask-workspace.tsx`
- Create: `web/components/workbench/ask-composer.tsx`
- Create: `web/components/workbench/ask-message-list.tsx`
- Create: `web/components/workbench/research-context-panel.tsx`
- Create: `web/components/workbench/ask-history-recorder.tsx`
- Modify: `web/app/app/page.tsx`
- Modify: `web/app/app/ask/page.tsx`
- Modify: `web/tests/research-pages.test.tsx`
- Delete: `web/components/workbench/research-dashboard.tsx`

- [ ] **Step 1: Write the failing page test for `/app` as the ask homepage**

```ts
test("/app becomes the chat-first ask homepage", async () => {
  const module = await import("../app/app/page");
  const html = compact(renderToStaticMarkup(await module.default()));

  assert.match(html, /问答/);
  assert.match(html, /继续提问或开始新的研究问题/);
  assert.match(html, /本轮来源/);
  assert.match(html, /知识缺口/);
  assert.match(html, /沉淀到知识库/);
  assert.doesNotMatch(html, /Today Vault Panel/);
  assert.doesNotMatch(html, /下一步路径/);
});
```

- [ ] **Step 2: Run the page test to verify it fails**

Run: `node --import tsx --test tests/research-pages.test.tsx`

Expected: FAIL because `/app` still renders `ResearchDashboardView`.

- [ ] **Step 3: Implement the shared ask workspace and repoint `/app` to it**

```tsx
// web/components/workbench/ask-workspace.tsx
import { AskComposer } from "@/components/workbench/ask-composer";
import { AskMessageList } from "@/components/workbench/ask-message-list";
import { AskHistoryRecorder } from "@/components/workbench/ask-history-recorder";
import { ResearchContextPanel } from "@/components/workbench/research-context-panel";
import type { ResearchAskResponse, ResearchDashboard, ResearchTopicSummary } from "@/lib/types";

export function AskWorkspace({
  dashboard,
  wikiPages,
  answer,
  question,
  topicId,
  mode,
  continueFromAskTurnId
}: {
  dashboard: ResearchDashboard;
  wikiPages: ResearchTopicSummary[];
  answer: ResearchAskResponse | null;
  question?: string;
  topicId?: string;
  mode: "vault" | "vault_plus_web";
  continueFromAskTurnId?: string;
}) {
  return (
    <main className="chat-workspace px-6 py-6 lg:px-8">
      <AskHistoryRecorder answer={answer} question={question} topicTitle={dashboard.focusTopic?.title} />
      <section className="min-w-0 rounded-[32px] bg-white p-6 shadow-paper">
        <AskMessageList answer={answer} dashboard={dashboard} question={question} />
        <AskComposer continueFromAskTurnId={continueFromAskTurnId} mode={mode} question={question} topicId={topicId} wikiPages={wikiPages} />
      </section>
      <ResearchContextPanel answer={answer} dashboard={dashboard} />
    </main>
  );
}
```

```tsx
// web/components/workbench/ask-history-recorder.tsx
"use client";

import { useEffect } from "react";
import { mergeAskHistoryEntry, readAskHistory, writeAskHistory } from "@/lib/ask-history";
import type { ResearchAskResponse } from "@/lib/types";

export function AskHistoryRecorder({
  answer,
  question,
  topicTitle
}: {
  answer: ResearchAskResponse | null;
  question?: string;
  topicTitle?: string | null;
}) {
  useEffect(() => {
    if (!answer || !question) {
      return;
    }

    writeAskHistory(
      mergeAskHistoryEntry(readAskHistory(), {
        id: answer.id,
        title: question,
        href: `/app?q=${encodeURIComponent(question)}${answer.topicId ? `&topicId=${answer.topicId}` : ""}`,
        topicTitle: topicTitle ?? null,
        preview: answer.answer,
        updatedAt: answer.createdAt
      })
    );
  }, [answer, question, topicTitle]);

  return null;
}
```

```tsx
// web/app/app/page.tsx
import { AskWorkspace } from "@/components/workbench/ask-workspace";
import { askResearch, getResearchDashboard, getWikiPages } from "@/lib/research";
import { getRequestOwnerSession } from "@/lib/request-owner-session";

export default async function WorkbenchPage({ searchParams }: { searchParams?: Promise<Record<string, string | undefined>> }) {
  const ownerSession = await getRequestOwnerSession();
  const dashboard = await getResearchDashboard(ownerSession);
  const wikiPages = await getWikiPages(ownerSession);
  const resolved = searchParams ? await searchParams : {};
  const question = resolved.q?.trim();
  const answer = question ? await askResearch({ question, topicId: resolved.topicId, mode: resolved.mode as "vault" | "vault_plus_web" | undefined, continueFromAskTurnId: resolved.continueFromAskTurnId }, ownerSession) : null;

  return <AskWorkspace answer={answer} continueFromAskTurnId={resolved.continueFromAskTurnId} dashboard={dashboard} mode={resolved.mode === "vault_plus_web" ? "vault_plus_web" : "vault"} question={question} topicId={resolved.topicId} wikiPages={wikiPages} />;
}
```

```tsx
// web/app/app/ask/page.tsx
export { default } from "@/app/app/page";
```

- [ ] **Step 4: Run the page test again to verify it passes**

Run: `node --import tsx --test tests/research-pages.test.tsx`

Expected: PASS with `/app` now matching the ask-first shell and `/app/ask` still rendering the same workspace.

- [ ] **Step 5: Commit the ask homepage pivot**

```bash
git add web/components/workbench/ask-workspace.tsx web/components/workbench/ask-composer.tsx web/components/workbench/ask-message-list.tsx web/components/workbench/research-context-panel.tsx web/components/workbench/ask-history-recorder.tsx web/app/app/page.tsx web/app/app/ask/page.tsx web/tests/research-pages.test.tsx
git rm web/components/workbench/research-dashboard.tsx
git commit -m "feat: make ask the authenticated home"
```

### Task 4: Convert `资料 / 审阅 / 知识库` into Chinese object-style workspaces

**Files:**
- Create: `web/components/workbench/raw-workspace.tsx`
- Create: `web/components/workbench/review-workspace.tsx`
- Create: `web/components/workbench/wiki-workspace.tsx`
- Create: `web/components/workbench/wiki-detail-workspace.tsx`
- Modify: `web/app/app/raw/page.tsx`
- Modify: `web/app/app/ingest/page.tsx`
- Modify: `web/app/app/wiki/page.tsx`
- Modify: `web/app/app/wiki/[id]/page.tsx`
- Modify: `web/app/app/review/page.tsx`
- Modify: `web/app/app/topics/page.tsx`
- Modify: `web/tests/research-pages.test.tsx`

- [ ] **Step 1: Write the failing page assertions for Chinese workspace naming**

```ts
test("raw, ingest, and wiki pages use Chinese object-style naming", async () => {
  const rawPage = await import("../app/app/raw/page");
  const ingestPage = await import("../app/app/ingest/page");
  const wikiDetailPage = await import("../app/app/wiki/[id]/page");

  const rawHtml = compact(renderToStaticMarkup(await rawPage.default()));
  const ingestHtml = compact(renderToStaticMarkup(await ingestPage.default({})));
  const detailHtml = compact(renderToStaticMarkup(await wikiDetailPage.default({ params: Promise.resolve({ id: "topic-001" }) })));

  assert.match(rawHtml, /资料/);
  assert.match(rawHtml, /导入原始材料/);
  assert.match(ingestHtml, /审阅/);
  assert.match(ingestHtml, /待你确认的 AI 提案/);
  assert.match(detailHtml, /当前理解/);
  assert.match(detailHtml, /关键论点/);
  assert.match(detailHtml, /开放问题/);
  assert.match(detailHtml, /来源/);
  assert.doesNotMatch(detailHtml, /Current Understanding/);
});
```

- [ ] **Step 2: Run the page test to verify it fails**

Run: `node --import tsx --test tests/research-pages.test.tsx`

Expected: FAIL because the pages still expose `raw`, `ingest`, `Current Understanding`, `Key Claims`, and other English labels.

- [ ] **Step 3: Extract workspace components and switch visible labels to Chinese**

```tsx
// web/components/workbench/raw-workspace.tsx
import { PanelCard } from "@/components/ui/panel-card";
import type { ResearchSourceRecord } from "@/lib/types";

export function RawWorkspace({ sources, pendingCount }: { sources: ResearchSourceRecord[]; pendingCount: number }) {
  return (
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">资料</div>
      <h1 className="mt-3 font-headline text-4xl font-extrabold tracking-tight text-ink-text">导入原始材料</h1>
      <p className="mt-4 text-sm leading-7 text-ink-muted">网页、PDF 和迁移笔记都会先进入 raw，再决定是否编译进知识库。</p>
      <PanelCard className="mt-8 p-6">当前待编译材料 {pendingCount} 条</PanelCard>
    </main>
  );
}
```

```tsx
// web/components/workbench/review-workspace.tsx
import { PanelCard } from "@/components/ui/panel-card";
import type { ResearchReviewItem } from "@/lib/types";

export function ReviewWorkspace({ reviews }: { reviews: ResearchReviewItem[] }) {
  return (
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">审阅</div>
      <h1 className="mt-3 font-headline text-4xl font-extrabold tracking-tight text-ink-text">待你确认的 AI 提案</h1>
      <div className="mt-8 space-y-4">{reviews.map((review) => <PanelCard key={review.id} className="p-6">{review.title}</PanelCard>)}</div>
    </main>
  );
}
```

```tsx
// web/components/workbench/wiki-detail-workspace.tsx
import { PanelCard } from "@/components/ui/panel-card";
import type { ResearchTopicDetail } from "@/lib/types";

export function WikiDetailWorkspace({ topic }: { topic: ResearchTopicDetail }) {
  return (
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">知识库页面</div>
      <h1 className="mt-3 font-headline text-4xl font-extrabold tracking-tight text-ink-text">{topic.title}</h1>
      <p className="mt-4 text-sm leading-7 text-ink-muted">{topic.summary}</p>
      <div className="mt-8 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <PanelCard className="p-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">当前理解</div>
        </PanelCard>
        <PanelCard className="p-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">来源</div>
        </PanelCard>
      </div>
      <div className="mt-8 grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <PanelCard className="p-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">关键论点</div>
        </PanelCard>
        <PanelCard className="p-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">研究过程</div>
        </PanelCard>
      </div>
    </main>
  );
}
```

```tsx
// web/app/app/review/page.tsx
import { redirect } from "next/navigation";

export default function ReviewCompatibilityPage() {
  redirect("/app/ingest");
}
```

```tsx
// web/app/app/topics/page.tsx
import { redirect } from "next/navigation";

export default function TopicsCompatibilityPage() {
  redirect("/app/wiki");
}
```

- [ ] **Step 4: Run the page test again to verify it passes**

Run: `node --import tsx --test tests/research-pages.test.tsx`

Expected: PASS with Chinese titles and section labels across `资料 / 审阅 / 知识库`.

- [ ] **Step 5: Commit the workspace rename and layout cleanup**

```bash
git add web/components/workbench/raw-workspace.tsx web/components/workbench/review-workspace.tsx web/components/workbench/wiki-workspace.tsx web/components/workbench/wiki-detail-workspace.tsx web/app/app/raw/page.tsx web/app/app/ingest/page.tsx web/app/app/wiki/page.tsx web/app/app/wiki/[id]/page.tsx web/app/app/review/page.tsx web/app/app/topics/page.tsx web/tests/research-pages.test.tsx
git commit -m "feat: localize research workspaces to chinese"
```

### Task 5: Polish the shell visuals, loading states, and full-stack verification

**Files:**
- Modify: `web/app/globals.css`
- Modify: `web/app/app/loading.tsx`
- Modify: `web/app/app/error.tsx`
- Modify: `web/app/app/not-found.tsx`
- Modify: `web/tests/e2e/local-fullstack.spec.ts`
- Modify: `web/tests/unit/workbench-components.test.tsx`

- [ ] **Step 1: Write the failing end-to-end assertion for the final chat-first flow**

```ts
test("owner lands on 问答 and can move through the core research loop", async ({ page }) => {
  await login(page);

  await expect(page.getByRole("heading", { name: "问答" })).toBeVisible();
  await expect(page.getByText("最近对话")).toBeVisible();
  await expect(page.getByPlaceholder("继续提问或开始新的研究问题")).toBeVisible();

  await page.getByRole("link", { name: "审阅" }).click();
  await expect(page.getByRole("heading", { name: "审阅" })).toBeVisible();

  await page.getByRole("link", { name: "知识库" }).click();
  await expect(page.getByRole("heading", { name: "知识库" })).toBeVisible();

  await page.getByRole("link", { name: "资料" }).click();
  await expect(page.getByRole("heading", { name: "资料" })).toBeVisible();
});
```

- [ ] **Step 2: Run the targeted verification to confirm it fails before the polish pass**

Run: `npx playwright test tests/e2e/local-fullstack.spec.ts --project=chromium`

Expected: FAIL on the first `问答` assertion or the new Chinese nav labels if the shell is not fully polished yet.

- [ ] **Step 3: Apply the visual polish and final empty/loading/error states**

```css
/* web/app/globals.css */
.shell-grid {
  display: grid;
  grid-template-columns: 18rem minmax(0, 1fr);
}

.chat-workspace {
  display: grid;
  gap: 1.5rem;
  grid-template-columns: minmax(0, 1.45fr) minmax(18rem, 0.75fr);
}

.chat-composer {
  position: sticky;
  bottom: 0;
  border-top: 1px solid rgba(25, 28, 29, 0.08);
  background: linear-gradient(180deg, rgba(251, 252, 252, 0.72), #fbfcfc 24%);
}
```

```tsx
// web/app/app/loading.tsx
export default function AppLoading() {
  return (
    <main className="chat-workspace px-6 py-6 lg:px-8">
      <section className="rounded-[32px] bg-white p-6 shadow-paper">
        <div className="h-8 w-40 animate-pulse rounded-full bg-ink-low" />
        <div className="mt-6 h-24 animate-pulse rounded-[28px] bg-ink-low" />
        <div className="mt-4 h-24 animate-pulse rounded-[28px] bg-ink-low" />
      </section>
      <aside className="rounded-[32px] bg-white p-6 shadow-paper">
        <div className="h-6 w-24 animate-pulse rounded-full bg-ink-low" />
        <div className="mt-4 h-20 animate-pulse rounded-[24px] bg-ink-low" />
      </aside>
    </main>
  );
}
```

- [ ] **Step 4: Run the complete frontend verification suite**

Run:

```bash
npx vitest run tests/unit/app-shell.test.ts tests/unit/workbench-components.test.tsx
node --import tsx --test tests/research-pages.test.tsx tests/research-api.test.tsx tests/owner-session.test.ts tests/owner-auth.test.ts
npx playwright test tests/e2e/local-fullstack.spec.ts --project=chromium
npm run lint
npm run typecheck
npm run build
```

Expected:

- `vitest` passes
- `node --test` passes
- Playwright passes or is explicitly skipped when `INKDESK_E2E_FULLSTACK` is not set
- `lint`, `typecheck`, and `build` succeed

- [ ] **Step 5: Commit the polished shell**

```bash
git add web/app/globals.css web/app/app/loading.tsx web/app/app/error.tsx web/app/app/not-found.tsx web/tests/e2e/local-fullstack.spec.ts web/tests/unit/workbench-components.test.tsx
git commit -m "feat: polish chat-first research shell"
```
