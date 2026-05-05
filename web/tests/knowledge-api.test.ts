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

test("public data helpers merge backend articles with curated public writing when an API base URL is configured", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input) => {
    const url = String(input);

    if (url === "http://localhost:8080/api/public/articles") {
      return createJsonResponse([
        {
          id: "note-001",
          title: "真实文章 A",
          excerpt: "真实摘要 A",
          slug: "real-article-a",
          updatedAt: "2026-04-12T08:10:00Z",
          tags: ["定位", "Agent"]
        },
        {
          id: "note-003",
          title: "真实文章 B",
          excerpt: "真实摘要 B",
          slug: "real-article-b",
          updatedAt: "2026-04-12T06:58:00Z",
          tags: ["公开输出"]
        }
      ]);
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  }, async (calls) => {
    const module = await import("../lib/public");
    const data = await module.getPublicHomeData();

    assert.equal(data.articles.some((article) => article.slug === "real-article-a"), true);
    assert.equal(data.articles.some((article) => article.slug === "frontend-layering-for-backoffice"), true);
    assert.equal(data.articles.find((article) => article.slug === "real-article-a")?.title, "真实文章 A");
    assert.equal(data.articles.find((article) => article.slug === "real-article-a")?.sourceNoteId, "note-001");
    assert.equal(data.knowledgeBuckets.length, 4);
    assert.equal(data.featuredProjects.length > 0, true);
    assert.equal(data.recentUpdates.some((item) => item.type === "article"), true);
    assert.equal(data.authorProfile.name, "R");
    assert.equal(calls[0]?.init?.headers, undefined);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("public knowledge bucket helper keeps curated article links when backend articles do not cover those slugs", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input) => {
    const url = String(input);

    if (url === "http://localhost:8080/api/public/articles") {
      return createJsonResponse([
        {
          id: "note-001",
          title: "真实文章 A",
          excerpt: "真实摘要 A",
          slug: "real-article-a",
          updatedAt: "2026-04-12T08:10:00Z",
          tags: ["定位", "Agent"]
        }
      ]);
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  }, async () => {
    const module = await import("../lib/public");
    const bucket = await module.getPublicKnowledgeBucketBySlug("development-tech");

    assert.equal(bucket?.featuredArticle?.slug, "frontend-layering-for-backoffice");
    assert.match(bucket?.featuredArticle?.title ?? "", /真正可维护的前端分层/);
    assert.deepEqual(
      bucket?.relatedArticles.map((article) => article.slug),
      ["why-indexes-change-query-cost"]
    );
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("public article helper falls back to curated article detail when backend does not know that slug", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input) => {
    const url = String(input);

    if (url === "http://localhost:8080/api/public/articles/frontend-layering-for-backoffice") {
      return createJsonResponse({ message: "not found" }, 404);
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  }, async () => {
    const module = await import("../lib/public");
    const article = await module.getPublicArticleBySlug("frontend-layering-for-backoffice");

    assert.equal(article?.slug, "frontend-layering-for-backoffice");
    assert.match(article?.title ?? "", /真正可维护的前端分层/);
    assert.equal(article?.body.length > 0, true);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("knowledge hub helper rebuilds note summaries from the admin tree and forwards the owner cookie", async () => {
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
          title: "真实知识标题",
          sortOrder: 1,
          updatedAt: "2026-04-12T08:10:00Z",
          excerpt: "真实知识摘要",
          tags: ["定位"],
          visibility: "public",
          published: true,
          slug: "real-note"
        }
      ]);
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  }, async () => {
    const module = await import("../lib/knowledge");
    const data = await module.getKnowledgeHubData("published", "owner");

    assert.equal(data.summary.totalNotes, 1);
    assert.equal(data.summary.publicNotes, 1);
    assert.equal(data.notes.length, 1);
    assert.equal(data.notes[0]?.title, "真实知识标题");
    assert.equal(data.notes[0]?.folder, "产品重构");
    assert.equal(data.notes[0]?.slug, "real-note");
    assert.equal(data.notes[0]?.visibility, "public");
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("knowledge detail helper adapts backend markdown into editor paragraphs", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input, init) => {
    const url = String(input);

    if (url === "http://localhost:8080/api/admin/notes/note-001") {
      assert.equal(
        (init?.headers as Record<string, string> | undefined)?.Cookie,
        `${OWNER_SESSION_COOKIE}=owner`
      );

      return createJsonResponse({
        id: "note-001",
        parentId: "folder-001",
        title: "真实知识详情",
        excerpt: "详情摘要",
        markdownContent: `第一段

第二段`,
        updatedAt: "2026-04-12T08:10:00Z",
        tags: ["定位", "Agent"],
        visibility: "public",
        published: true,
        slug: "real-note"
      });
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  }, async () => {
    const module = await import("../lib/knowledge");
    const note = await module.getKnowledgeNoteById("note-001", "owner");

    assert.ok(note);
    assert.equal(note?.title, "真实知识详情");
    assert.deepEqual(note?.body, ["第一段", "第二段"]);
    assert.equal(note?.published, true);
    assert.equal(note?.slug, "real-note");
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("knowledge write helpers send create and update requests to the backend with the owner cookie", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input, init) => {
    const url = String(input);
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;

    if (url === "http://localhost:8080/api/admin/notes") {
      assert.equal(init?.method, "POST");
      assert.equal(
        (init?.headers as Record<string, string> | undefined)?.Cookie,
        `${OWNER_SESSION_COOKIE}=owner`
      );
      assert.equal(body?.title, "新建知识资产");
      assert.equal(body?.parentId, "folder-product-reframe");

      return createJsonResponse(
        {
          id: "note-new",
          parentId: "folder-product-reframe",
          title: "新建知识资产",
          excerpt: "首次摘要",
          markdownContent: "# 新建知识资产",
          updatedAt: "2026-04-12T08:10:00Z",
          tags: [],
          visibility: "private",
          published: false,
          slug: null
        },
        201
      );
    }

    if (url === "http://localhost:8080/api/admin/notes/note-new") {
      assert.equal(init?.method, "PATCH");
      assert.equal(
        (init?.headers as Record<string, string> | undefined)?.Cookie,
        `${OWNER_SESSION_COOKIE}=owner`
      );
      assert.equal(body?.excerpt, "更新后的摘要");

      return createJsonResponse({
        id: "note-new",
        parentId: "folder-product-reframe",
        title: "新建知识资产",
        excerpt: "更新后的摘要",
        markdownContent: "# 新建知识资产\n\n更新后的正文",
        updatedAt: "2026-04-12T08:12:00Z",
        tags: [],
        visibility: "private",
        published: false,
        slug: null
      });
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  }, async () => {
    const module = await import("../lib/knowledge");
    const created = await module.createKnowledgeNote(
      {
        title: "新建知识资产",
        parentId: "folder-product-reframe",
        excerpt: "首次摘要",
        markdownContent: "# 新建知识资产"
      },
      "owner"
    );
    const updated = await module.updateKnowledgeNote(
      "note-new",
      {
        title: "新建知识资产",
        parentId: "folder-product-reframe",
        excerpt: "更新后的摘要",
        markdownContent: "# 新建知识资产\n\n更新后的正文"
      },
      "owner"
    );

    assert.equal(created.id, "note-new");
    assert.equal(updated.excerpt, "更新后的摘要");
    assert.deepEqual(updated.body, ["# 新建知识资产", "更新后的正文"]);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("knowledge folder helper returns backend folder options for create forms", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input) => {
    const url = String(input);

    if (url === "http://localhost:8080/api/admin/notes/tree") {
      return createJsonResponse([
        {
          id: "folder-product-reframe",
          parentId: null,
          type: "folder",
          title: "产品重构",
          sortOrder: 100,
          updatedAt: "2026-04-12T08:00:00Z",
          excerpt: null,
          tags: [],
          visibility: "private",
          published: false,
          slug: null
        },
        {
          id: "note-001",
          parentId: "folder-product-reframe",
          type: "note",
          title: "知识资产",
          sortOrder: 110,
          updatedAt: "2026-04-12T08:10:00Z",
          excerpt: "摘要",
          tags: [],
          visibility: "private",
          published: false,
          slug: null
        }
      ]);
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  }, async () => {
    const module = await import("../lib/knowledge");
    const folders = await module.getKnowledgeFolderOptions("owner");

    assert.deepEqual(folders, [
      {
        id: "folder-product-reframe",
        title: "产品重构"
      }
    ]);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("knowledge helpers fall back to mock data when no API base URL is configured", async () => {
  delete process.env.NEXT_PUBLIC_API_BASE_URL;

  await withMockedFetch(async () => {
    throw new Error("fetch should not be called without an API base URL");
  }, async () => {
    const publicModule = await import("../lib/public");
    const knowledgeModule = await import("../lib/knowledge");

    const publicHome = await publicModule.getPublicHomeData();
    const knowledgeHub = await knowledgeModule.getKnowledgeHubData();

    assert.equal(publicHome.articles[0]?.slug, "super-personal-workbench-reframe");
    assert.equal(knowledgeHub.summary.totalNotes, 3);
  });
});

test("public data helpers fall back to mock data when the configured backend is unavailable", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async () => {
    throw new TypeError("fetch failed");
  }, async () => {
    const module = await import("../lib/public");
    const publicHome = await module.getPublicHomeData();
    const article = await module.getPublicArticleBySlug("super-personal-workbench-reframe");
    const params = await module.getPublicArticleParams();

    assert.equal(publicHome.articles[0]?.slug, "super-personal-workbench-reframe");
    assert.equal(article?.slug, "super-personal-workbench-reframe");
    assert.equal(params.some((item) => item.slug === "super-personal-workbench-reframe"), true);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});
