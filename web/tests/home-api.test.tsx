import assert from "node:assert/strict";
import test from "node:test";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

function compact(html: string) {
  return html.replace(/\s+/g, " ");
}

type FetchCall = {
  input: RequestInfo | URL;
  init?: RequestInit;
};

function createJsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "content-type": "application/json"
    }
  });
}

async function withMockedFetch(
  responder: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response> | Response,
  run: (calls: FetchCall[]) => Promise<void>
) {
  const originalFetch = globalThis.fetch;
  const calls: FetchCall[] = [];

  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    return responder(input, init);
  }) as typeof fetch;

  try {
    await run(calls);
  } finally {
    globalThis.fetch = originalFetch;
  }
}

(globalThis as typeof globalThis & { React: typeof React }).React = React;

test("home helper calls backend home snapshot and adapts it to the current workbench shape", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input, init) => {
    const url = new URL(String(input));

    if (url.pathname === "/api/admin/home") {
      assert.equal((init?.headers as Record<string, string> | undefined)?.Cookie, "inkdesk_owner_session=owner");

      return createJsonResponse({
        summary: {
          activePlans: 2,
          privateNotes: 1,
          publishedNotes: 2,
          linkedNotes: 3
        },
        focusPlan: {
          id: "plan-001",
          title: "来自后端的焦点计划",
          statusLabel: "进行中",
          horizonLabel: "今天",
          priorityLabel: "最高优先级",
          nextStep: "把首页入口和上下文重新排好。",
          nextActionLabel: "继续这个计划",
          nextActionHref: "/app/plans",
          searchTerm: "公开输出"
        },
        focusNote: {
          id: "note-002",
          title: "来自后端的焦点知识",
          excerpt: "后端焦点知识摘要",
          folder: "主系统结构",
          updatedAt: "2026-04-13T09:30:00Z",
          published: false,
          visibility: "private",
          visibilityLabel: "仅主系统"
        },
        suggestions: [
          {
            id: "agent-001",
            category: "今日建议",
            title: "先回到焦点计划",
            summary: "围绕首页把行动路径收短。",
            actionLabel: "打开任务与计划",
            href: "/app/plans"
          }
        ],
        quickActions: [
          {
            id: "quick-001",
            label: "新建知识资产",
            summary: "记录新的判断。",
            href: "/app/notes/new-note?state=blank",
            icon: "edit_note"
          }
        ],
        recentKnowledge: [
          {
            id: "note-003",
            title: "来自后端的最近知识",
            excerpt: "最近知识摘要",
            folder: "输出层设计",
            updatedAt: "2026-04-13T08:00:00Z",
            published: true,
            visibility: "public",
            visibilityLabel: "已发布"
          }
        ],
        publishQueue: [
          {
            noteId: "note-unknown",
            title: "还没进入 fixture 的草稿",
            excerpt: "未知知识也要能展示。",
            updatedAt: "2026-04-13T07:00:00Z",
            state: "draft",
            stateLabel: "继续整理后发布"
          }
        ]
      });
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }, async () => {
    const module = await import("../lib/home");
    const snapshot = await module.getWorkbenchSnapshot("owner");

    assert.equal(snapshot.summary.activePlans, 2);
    assert.equal(snapshot.focusPlan.id, "plan-001");
    assert.equal(snapshot.focusPlan.status, "active");
    assert.equal(snapshot.focusPlan.relatedSearchTerms[0], "公开输出");
    assert.equal(snapshot.focusPlan.milestones.length > 0, true);
    assert.equal(snapshot.focusNote.id, "note-002");
    assert.equal(snapshot.focusNote.tags.includes("Agent"), true);
    assert.equal(snapshot.recentKnowledge[0]?.id, "note-003");
    assert.equal(snapshot.publishQueue[0]?.noteId, "note-unknown");
    assert.equal(snapshot.publishQueue[0]?.visibilityLabel, "仅主系统");
    assert.deepEqual(snapshot.publishQueue[0]?.relatedPlanIds, []);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("home helper returns safe placeholders when backend focus data is empty", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input) => {
    const url = new URL(String(input));

    if (url.pathname === "/api/admin/home") {
      return createJsonResponse({
        summary: {
          activePlans: 0,
          privateNotes: 0,
          publishedNotes: 0,
          linkedNotes: 0
        },
        focusPlan: null,
        focusNote: null,
        suggestions: [],
        quickActions: [],
        recentKnowledge: [],
        publishQueue: []
      });
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }, async () => {
    const module = await import("../lib/home");
    const snapshot = await module.getWorkbenchSnapshot("owner");

    assert.equal(snapshot.focusPlan.id, "plan-empty");
    assert.equal(snapshot.focusPlan.nextActionHref, "/app/plans");
    assert.equal(snapshot.focusNote.id, "new-note");
    assert.equal(snapshot.focusNote.visibility, "private");
    assert.deepEqual(snapshot.recentKnowledge, []);
    assert.deepEqual(snapshot.publishQueue, []);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("home page renders backend focus content", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input) => {
    const url = new URL(String(input));

    if (url.pathname === "/api/admin/home") {
      return createJsonResponse({
        summary: {
          activePlans: 2,
          privateNotes: 1,
          publishedNotes: 2,
          linkedNotes: 3
        },
        focusPlan: {
          id: "plan-001",
          title: "来自后端的焦点计划",
          statusLabel: "进行中",
          horizonLabel: "今天",
          priorityLabel: "最高优先级",
          nextStep: "把首页入口和上下文重新排好。",
          nextActionLabel: "继续这个计划",
          nextActionHref: "/app/plans",
          searchTerm: "公开输出"
        },
        focusNote: {
          id: "note-002",
          title: "来自后端的焦点知识",
          excerpt: "后端焦点知识摘要",
          folder: "主系统结构",
          updatedAt: "2026-04-13T09:30:00Z",
          published: false,
          visibility: "private",
          visibilityLabel: "仅主系统"
        },
        suggestions: [
          {
            id: "agent-001",
            category: "今日建议",
            title: "先回到焦点计划",
            summary: "围绕首页把行动路径收短。",
            actionLabel: "打开任务与计划",
            href: "/app/plans"
          }
        ],
        quickActions: [
          {
            id: "quick-001",
            label: "新建知识资产",
            summary: "记录新的判断。",
            href: "/app/notes/new-note?state=blank",
            icon: "edit_note"
          }
        ],
        recentKnowledge: [],
        publishQueue: []
      });
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }, async () => {
    const module = await import("../app/app/page");
    const html = compact(renderToStaticMarkup(await module.default()));

    assert.match(html, /来自后端的焦点计划/);
    assert.match(html, /来自后端的焦点知识/);
    assert.match(html, /先回到焦点计划/);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("home page keeps rendering when focus note is missing and falls back to the new-note CTA", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input) => {
    const url = new URL(String(input));

    if (url.pathname === "/api/admin/home") {
      return createJsonResponse({
        summary: {
          activePlans: 0,
          privateNotes: 0,
          publishedNotes: 0,
          linkedNotes: 0
        },
        focusPlan: null,
        focusNote: null,
        suggestions: [],
        quickActions: [],
        recentKnowledge: [],
        publishQueue: []
      });
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }, async () => {
    const module = await import("../app/app/page");
    const html = compact(renderToStaticMarkup(await module.default()));

    assert.match(html, /当前还没有可直接回看的知识资产/);
    assert.match(html, /\/app\/notes\/new-note\?state=blank/);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("home page falls back to the mock snapshot when API base URL is missing", async () => {
  delete process.env.NEXT_PUBLIC_API_BASE_URL;

  await withMockedFetch(async () => {
    throw new Error("fetch should not run without an API base URL");
  }, async () => {
    const module = await import("../app/app/page");
    const html = compact(renderToStaticMarkup(await module.default()));

    assert.match(html, /把最近三篇笔记压缩成一张行动摘要/);
    assert.match(html, /收口公开输出入口与主系统边界/);
  });
});

test("home page falls back to the mock snapshot when the configured backend is unavailable", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async () => {
    throw new TypeError("fetch failed");
  }, async () => {
    const module = await import("../app/app/page");
    const html = compact(renderToStaticMarkup(await module.default()));

    assert.match(html, /把最近三篇笔记压缩成一张行动摘要/);
    assert.match(html, /收口公开输出入口与主系统边界/);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("public home helper keeps curated knowledge buckets and projects while adapting backend articles", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input) => {
    const url = new URL(String(input));

    if (url.pathname === "/api/public/articles") {
      return createJsonResponse([
        {
          id: "note-001",
          title: "把 Inkdesk 从知识库改造成真正的个人工作台",
          excerpt: "来自后端的公开文章摘要",
          slug: "super-personal-workbench-reframe",
          updatedAt: "2026-04-15T09:30:00Z",
          tags: ["项目实践", "系统设计"]
        },
        {
          id: "note-003",
          title: "给中后台页面做一次真正可维护的前端分层",
          excerpt: "来自后端的第二篇文章摘要",
          slug: "frontend-layering-for-backoffice",
          updatedAt: "2026-04-14T09:30:00Z",
          tags: ["前端", "开发技术"]
        }
      ]);
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }, async () => {
    const module = await import("../lib/public");
    const home = await module.getPublicHomeData();
    const bucket = await module.getPublicKnowledgeBucketBySlug("project-practice");
    const project = await module.getPublicProjectBySlug("inkdesk-main-system");
    const relations = await module.getPublicRelationsForArticleSlug("super-personal-workbench-reframe");

    assert.equal(home.articles.some((article) => article.slug === "super-personal-workbench-reframe"), true);
    assert.equal(home.articles.some((article) => article.slug === "one-request-through-network-stack"), true);
    assert.equal(home.knowledgeBuckets.length, 4);
    assert.equal(home.featuredProjects.length > 0, true);
    assert.equal(home.recentUpdates.some((item) => item.type === "article"), true);
    assert.equal(home.recentUpdates.some((item) => item.type === "project"), true);
    assert.equal(bucket?.featuredArticle?.slug, "super-personal-workbench-reframe");
    assert.equal(project?.relatedArticles.some((article) => article.slug === "super-personal-workbench-reframe"), true);
    assert.equal(relations.relatedBuckets.some((entry) => entry.slug === "project-practice"), true);
    assert.equal(relations.relatedProjects.some((entry) => entry.slug === "inkdesk-main-system"), true);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});
