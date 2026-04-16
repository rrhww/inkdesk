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

test("publish page renders backend-backed published and draft knowledge while hiding preview links without a public path", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input) => {
    const url = String(input);

    if (url === "http://localhost:8080/api/admin/notes/tree") {
      return createJsonResponse([
        {
          id: "folder-001",
          parentId: null,
          type: "folder",
          title: "产品重构",
          sortOrder: 1,
          updatedAt: "2026-04-12T08:10:00Z",
          excerpt: null,
          tags: [],
          visibility: "private",
          published: false,
          slug: null
        },
        {
          id: "note-001",
          parentId: "folder-001",
          type: "note",
          title: "来自后端的已发布内容",
          sortOrder: 1,
          updatedAt: "2026-04-12T08:10:00Z",
          excerpt: "已发布摘要",
          tags: ["定位"],
          visibility: "public",
          published: true,
          slug: "backend-published-note"
        },
        {
          id: "note-no-slug",
          parentId: "folder-001",
          type: "note",
          title: "缺少公开路径的已发布内容",
          sortOrder: 2,
          updatedAt: "2026-04-12T07:45:00Z",
          excerpt: "缺少 slug 的摘要",
          tags: ["公开输出"],
          visibility: "public",
          published: true,
          slug: null
        },
        {
          id: "note-extra",
          parentId: "folder-001",
          type: "note",
          title: "来自后端的草稿内容",
          sortOrder: 3,
          updatedAt: "2026-04-12T07:10:00Z",
          excerpt: "草稿摘要",
          tags: ["草稿"],
          visibility: "private",
          published: false,
          slug: null
        }
      ]);
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  }, async () => {
    const module = await import("../app/app/publish/page");
    const html = compact(renderToStaticMarkup(await module.default()));
    const previewLinks = html.match(/>预览公共文章</g) ?? [];

    assert.match(html, /来自后端的已发布内容/);
    assert.match(html, /缺少公开路径的已发布内容/);
    assert.match(html, /来自后端的草稿内容/);
    assert.equal(previewLinks.length, 1);
    assert.match(html, /回到知识资产/);
    assert.match(html, /继续整理上下文/);
    assert.doesNotMatch(html, /href="\/">预览公共文章</);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});
