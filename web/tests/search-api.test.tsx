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

test("search helper calls backend search when API base URL is configured", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input, init) => {
    const url = new URL(String(input));

    if (url.pathname === "/api/admin/search") {
      assert.equal(url.searchParams.get("q"), "Agent");
      assert.equal(url.searchParams.get("visibility"), "all");
      assert.equal((init?.headers as Record<string, string> | undefined)?.Cookie, "inkdesk_owner_session=owner");

      return createJsonResponse([
        {
          note: {
            id: "note-002",
            title: "来自后端的搜索命中",
            excerpt: "后端搜索摘要",
            tags: ["Agent"],
            folder: "主系统结构",
            updatedAt: "2026-04-12T07:42:00Z",
            visibility: "private",
            published: false,
            slug: null
          },
          score: 11,
          hitLabels: ["标题", "标签"],
          matchedTerms: ["Agent"]
        }
      ]);
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }, async () => {
    const module = await import("../lib/search");
    const results = await module.searchKnowledge({ q: "Agent", visibility: "all" }, "owner");

    assert.equal(results.length, 1);
    assert.equal(results[0]?.note.id, "note-002");
    assert.equal(results[0]?.note.title, "来自后端的搜索命中");
    assert.equal(results[0]?.hitLabels[0], "标题");
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("search helper falls back to mock search when API base URL is missing", async () => {
  delete process.env.NEXT_PUBLIC_API_BASE_URL;

  await withMockedFetch(async () => {
    throw new Error("fetch should not run without an API base URL");
  }, async () => {
    const module = await import("../lib/search");
    const results = await module.searchKnowledge({ q: "Agent", visibility: "all" });

    assert.equal(results[0]?.note.id, "note-002");
  });
});

test("search page renders backend results", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input) => {
    const url = new URL(String(input));

    if (url.pathname === "/api/admin/search") {
      return createJsonResponse([
        {
          note: {
            id: "note-002",
            title: "来自后端的搜索命中",
            excerpt: "后端搜索摘要",
            tags: ["Agent"],
            folder: "主系统结构",
            updatedAt: "2026-04-12T07:42:00Z",
            visibility: "private",
            published: false,
            slug: null
          },
          score: 11,
          hitLabels: ["标题", "标签"],
          matchedTerms: ["Agent"]
        }
      ]);
    }

    if (url.pathname === "/api/admin/notes/tree") {
      return createJsonResponse([
        {
          id: "folder-system-structure",
          parentId: null,
          type: "folder",
          title: "主系统结构",
          sortOrder: 200,
          updatedAt: "2026-04-12T07:42:00Z",
          excerpt: null,
          tags: [],
          visibility: "private",
          published: false,
          slug: null
        },
        {
          id: "note-002",
          parentId: "folder-system-structure",
          type: "note",
          title: "为什么主系统首页必须先看到 Agent",
          sortOrder: 210,
          updatedAt: "2026-04-12T07:42:00Z",
          excerpt: "记录 Agent 控制台为何要成为主人进入系统后的第一屏，而不是笔记列表或发布页。",
          tags: ["Agent", "首页", "系统设计"],
          visibility: "private",
          published: false,
          slug: null
        }
      ]);
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }, async () => {
    const module = await import("../app/app/search/page");
    const html = compact(
      renderToStaticMarkup(
        await module.default({
          searchParams: Promise.resolve({
            q: "Agent"
          })
        })
      )
    );

    assert.match(html, /来自后端的搜索命中/);
    assert.match(html, /命中来源：标题 \/ 标签/);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});
