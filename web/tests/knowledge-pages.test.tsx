import assert from "node:assert/strict";
import test from "node:test";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import type { KnowledgeNoteDetail } from "../lib/types";

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

test("public home view can render backend-provided article data", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input) => {
    const url = String(input);

    if (url === "http://localhost:8080/api/public/articles") {
      return createJsonResponse([
        {
          id: "note-backend-home",
          title: "来自后端的首页文章",
          excerpt: "后端首页摘要",
          slug: "backend-home-article",
          updatedAt: "2026-04-20T08:10:00Z",
          tags: ["定位"]
        }
      ]);
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  }, async () => {
    const module = await import("../components/public-home-view");
    const html = compact(renderToStaticMarkup(await module.PublicHomeView()));

    assert.match(html, /来自后端的首页文章/);
    assert.match(html, /开发技术/);
    assert.match(html, /精选项目/);
    assert.match(html, /最近更新/);
    assert.match(html, /保持联系/);
    assert.doesNotMatch(html, /公开统计/);
    assert.doesNotMatch(html, /研究主题/);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("public article page renders backend article detail instead of the mock article body", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input) => {
    const url = String(input);

    if (url === "http://localhost:8080/api/public/articles/backend-article") {
      return createJsonResponse({
        id: "note-001",
        title: "来自后端的文章详情",
        excerpt: "详情摘要",
        slug: "backend-article",
        markdownContent: `第一段

第二段`,
        updatedAt: "2026-04-12T08:10:00Z",
        tags: ["定位", "Agent"]
      });
    }

    if (url === "http://localhost:8080/api/public/articles") {
      return createJsonResponse([
        {
          id: "note-001",
          title: "来自后端的文章详情",
          excerpt: "详情摘要",
          slug: "backend-article",
          updatedAt: "2026-04-12T08:10:00Z",
          tags: ["定位", "Agent"]
        },
        {
          id: "note-backend-related",
          title: "继续阅读文章",
          excerpt: "继续阅读摘要",
          slug: "other-article",
          updatedAt: "2026-04-20T06:58:00Z",
          tags: ["公开输出"]
        }
      ]);
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  }, async () => {
    const module = await import("../app/articles/[slug]/page");
    const html = compact(
      renderToStaticMarkup(
        await module.default({
          params: Promise.resolve({
            slug: "backend-article"
          })
        })
      )
    );

    assert.match(html, /来自后端的文章详情/);
    assert.match(html, /详情摘要/);
    assert.match(html, /第一段/);
    assert.match(html, /第二段/);
    assert.match(html, /继续阅读文章/);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("public article page falls back to mock data when the configured backend is unavailable", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async () => {
    throw new TypeError("fetch failed");
  }, async () => {
    const module = await import("../app/articles/[slug]/page");
    const html = compact(
      renderToStaticMarkup(
        await module.default({
          params: Promise.resolve({
            slug: "super-personal-workbench-reframe"
          })
        })
      )
    );

    assert.match(html, /公开文章/);
    assert.match(html, /这篇文章来自 Inkdesk 主系统中的长期知识资产/);
    assert.match(html, /继续阅读/);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("editor view can render a provided knowledge note detail", async () => {
  const note: KnowledgeNoteDetail = {
    id: "note-001",
    title: "来自后端的知识详情",
    excerpt: "知识详情摘要",
    body: ["第一段", "第二段"],
    tags: ["定位", "Agent"],
    folder: "产品重构",
    updatedAt: "2026-04-12 16:10",
    readingMinutes: 3,
    words: 320,
    published: true,
    visibility: "public",
    visibilityLabel: "已发布",
    relatedPlanIds: ["plan-001"],
    relatedTagIds: ["tag-positioning"],
    relatedSearchTerms: ["Agent", "公开输出"],
    knowledgeStateLabel: "已发布",
    slug: "backend-note"
  };

  const module = await import("../components/editor-view");
  const html = compact(renderToStaticMarkup(<module.EditorView noteId={note.id} note={note} status="draft" />));

  assert.match(html, /来自后端的知识详情/);
  assert.match(html, /第一段/);
  assert.match(html, /第二段/);
  assert.match(html, /已发布/);
});
