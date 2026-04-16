import assert from "node:assert/strict";
import test from "node:test";

import { OWNER_SESSION_COOKIE } from "../lib/owner-session";

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

test("publish helper rebuilds the dashboard from backend knowledge data and forwards the owner cookie", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input, init) => {
    const url = String(input);

    if (url === "http://localhost:8080/api/admin/notes/tree") {
      assert.equal(
        (init?.headers as Record<string, string> | undefined)?.Cookie,
        `${OWNER_SESSION_COOKIE}=owner`
      );

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
          title: "真实已发布笔记",
          sortOrder: 1,
          updatedAt: "2026-04-12T08:10:00Z",
          excerpt: "真实已发布摘要",
          tags: ["定位"],
          visibility: "public",
          published: true,
          slug: "real-published-note"
        },
        {
          id: "note-extra",
          parentId: "folder-001",
          type: "note",
          title: "真实草稿笔记",
          sortOrder: 2,
          updatedAt: "2026-04-12T07:10:00Z",
          excerpt: "真实草稿摘要",
          tags: ["草稿"],
          visibility: "private",
          published: false,
          slug: null
        }
      ]);
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  }, async (calls) => {
    const module = await import("../lib/publish");
    const dashboard = await module.getPublishDashboard("owner");

    assert.equal(calls.length, 1);
    assert.equal(dashboard.summary.publishedNotes, 1);
    assert.equal(dashboard.summary.privateNotes, 1);
    assert.equal(dashboard.summary.workflowLinkedNotes, 1);
    assert.equal(dashboard.published[0]?.title, "真实已发布笔记");
    assert.equal(dashboard.published[0]?.publicPath, "/articles/real-published-note");
    assert.equal(dashboard.published[0]?.state, "published");
    assert.equal(dashboard.drafts[0]?.title, "真实草稿笔记");
    assert.equal(dashboard.drafts[0]?.publicPath, undefined);
    assert.deepEqual(dashboard.drafts[0]?.relatedPlanIds, []);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("publish helper falls back to mock data when no API base URL is configured", async () => {
  delete process.env.NEXT_PUBLIC_API_BASE_URL;

  await withMockedFetch(async () => {
    throw new Error("fetch should not be called without an API base URL");
  }, async () => {
    const module = await import("../lib/publish");
    const dashboard = await module.getPublishDashboard();

    assert.equal(dashboard.summary.publishedNotes, 2);
    assert.equal(dashboard.summary.privateNotes, 1);
    assert.equal(dashboard.published[0]?.publicPath, "/articles/super-personal-workbench-reframe");
  });
});

test("publish helpers call backend publish and unpublish endpoints with the owner cookie", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input, init) => {
    const url = String(input);

    if (url === "http://localhost:8080/api/admin/notes/note-001/publish") {
      assert.equal(init?.method, "POST");
      assert.equal(
        (init?.headers as Record<string, string> | undefined)?.Cookie,
        `${OWNER_SESSION_COOKIE}=owner`
      );

      return createJsonResponse({
        id: "note-001",
        parentId: "folder-product-reframe",
        title: "发布中的知识资产",
        excerpt: "发布摘要",
        markdownContent: "# 发布中的知识资产",
        updatedAt: "2026-04-12T08:20:00Z",
        tags: [],
        visibility: "public",
        published: true,
        slug: "published-note"
      });
    }

    if (url === "http://localhost:8080/api/admin/notes/note-001/unpublish") {
      assert.equal(init?.method, "POST");
      assert.equal(
        (init?.headers as Record<string, string> | undefined)?.Cookie,
        `${OWNER_SESSION_COOKIE}=owner`
      );

      return createJsonResponse({
        id: "note-001",
        parentId: "folder-product-reframe",
        title: "发布中的知识资产",
        excerpt: "发布摘要",
        markdownContent: "# 发布中的知识资产",
        updatedAt: "2026-04-12T08:25:00Z",
        tags: [],
        visibility: "private",
        published: false,
        slug: "published-note"
      });
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  }, async () => {
    const module = await import("../lib/publish");
    const published = await module.publishKnowledgeNote("note-001", "owner");
    const unpublished = await module.unpublishKnowledgeNote("note-001", "owner");

    assert.equal(published.slug, "published-note");
    assert.equal(published.published, true);
    assert.equal(unpublished.visibility, "private");
    assert.equal(unpublished.published, false);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});
