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

test("plans helper calls backend plan list and adapts workbench lanes", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input, init) => {
    const url = new URL(String(input));

    if (url.pathname === "/api/admin/plans") {
      assert.equal((init?.headers as Record<string, string> | undefined)?.Cookie, "inkdesk_owner_session=owner");

      return createJsonResponse([
        {
          id: "plan-001",
          title: "来自后端的计划",
          summary: "后端计划摘要",
          status: "active",
          statusLabel: "进行中",
          horizon: "today",
          horizonLabel: "今天",
          priority: "critical",
          priorityLabel: "最高优先级",
          focusLabel: "系统入口",
          nextStep: "后端下一步",
          nextActionLabel: "查看后端计划",
          nextActionHref: "/app/plans",
          searchTerm: "公开输出",
          agentPrompt: "压缩当前执行视图。",
          updatedAt: "2026-04-12T10:30:00Z",
          relatedNoteIds: ["note-001"]
        }
      ]);
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }, async () => {
    const module = await import("../lib/plans");
    const workbench = await module.getPlanWorkbenchData("owner");

    assert.equal(workbench.summary.todayPlans, 1);
    assert.equal(workbench.lanes[0]?.plans[0]?.title, "来自后端的计划");
    assert.equal(workbench.lanes[0]?.plans[0]?.relatedSearchTerms[0], "公开输出");
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("plans helper falls back to mock plans when API base URL is missing", async () => {
  delete process.env.NEXT_PUBLIC_API_BASE_URL;

  await withMockedFetch(async () => {
    throw new Error("fetch should not run without an API base URL");
  }, async () => {
    const module = await import("../lib/plans");
    const workbench = await module.getPlanWorkbenchData();

    assert.equal(workbench.lanes[0]?.plans[0]?.id, "plan-001");
  });
});

test("plans page renders backend plans and linked knowledge", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input) => {
    const url = new URL(String(input));

    if (url.pathname === "/api/admin/plans") {
      return createJsonResponse([
        {
          id: "plan-001",
          title: "来自后端的计划",
          summary: "后端计划摘要",
          status: "active",
          statusLabel: "进行中",
          horizon: "today",
          horizonLabel: "今天",
          priority: "critical",
          priorityLabel: "最高优先级",
          focusLabel: "系统入口",
          nextStep: "后端下一步",
          nextActionLabel: "查看后端计划",
          nextActionHref: "/app/plans",
          searchTerm: "公开输出",
          agentPrompt: "压缩当前执行视图。",
          updatedAt: "2026-04-12T10:30:00Z",
          relatedNoteIds: ["note-001"]
        }
      ]);
    }

    if (url.pathname === "/api/admin/notes/tree") {
      return createJsonResponse([
        {
          id: "folder-product-reframe",
          parentId: null,
          type: "folder",
          title: "产品重构",
          sortOrder: 100,
          updatedAt: "2026-04-12T08:10:00Z",
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
          title: "来自后端的关联知识",
          sortOrder: 110,
          updatedAt: "2026-04-12T08:10:00Z",
          excerpt: "后端知识摘要",
          tags: ["定位"],
          visibility: "public",
          published: true,
          slug: "backend-note"
        }
      ]);
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }, async () => {
    const module = await import("../app/app/plans/page");
    const html = compact(renderToStaticMarkup(await module.default()));

    assert.match(html, /来自后端的计划/);
    assert.match(html, /来自后端的关联知识/);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("plan write helpers send create and update requests to the backend with the owner cookie", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input, init) => {
    const url = new URL(String(input));
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;

    if (url.pathname === "/api/admin/plans") {
      assert.equal(init?.method, "POST");
      assert.equal((init?.headers as Record<string, string> | undefined)?.Cookie, "inkdesk_owner_session=owner");
      assert.equal(body?.title, "本地全栈闭环");
      assert.deepEqual(body?.relatedNoteIds, ["note-001"]);

      return createJsonResponse(
        {
          id: "plan-new",
          title: "本地全栈闭环",
          summary: "先打通登录、知识、计划和设置。",
          status: "active",
          statusLabel: "进行中",
          horizon: "today",
          horizonLabel: "今天",
          priority: "critical",
          priorityLabel: "最高优先级",
          focusLabel: "闭环推进",
          nextStep: "先收掉知识和计划前端真写入",
          nextActionLabel: "打开计划页",
          nextActionHref: "/app/plans",
          searchTerm: "本地闭环",
          agentPrompt: "聚焦当前本地全栈闭环交付。",
          updatedAt: "2026-04-12T10:30:00Z",
          relatedNoteIds: ["note-001"]
        },
        201
      );
    }

    if (url.pathname === "/api/admin/plans/plan-new") {
      assert.equal(init?.method, "PATCH");
      assert.equal((init?.headers as Record<string, string> | undefined)?.Cookie, "inkdesk_owner_session=owner");
      assert.equal(body?.status, "done");

      return createJsonResponse({
        id: "plan-new",
        title: "本地全栈闭环",
        summary: "先打通登录、知识、计划和设置。",
        status: "done",
        statusLabel: "已完成",
        horizon: "today",
        horizonLabel: "今天",
        priority: "critical",
        priorityLabel: "最高优先级",
        focusLabel: "闭环推进",
        nextStep: "补完最终验收。",
        nextActionLabel: "打开计划页",
        nextActionHref: "/app/plans",
        searchTerm: "本地闭环",
        agentPrompt: "聚焦当前本地全栈闭环交付。",
        updatedAt: "2026-04-12T12:00:00Z",
        relatedNoteIds: ["note-001"]
      });
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }, async () => {
    const module = await import("../lib/plans");
    const created = await module.createPlanRecord(
      {
        title: "本地全栈闭环",
        summary: "先打通登录、知识、计划和设置。",
        status: "active",
        horizon: "today",
        priority: "critical",
        focusLabel: "闭环推进",
        nextStep: "先收掉知识和计划前端真写入",
        nextActionLabel: "打开计划页",
        nextActionHref: "/app/plans",
        searchTerm: "本地闭环",
        agentPrompt: "聚焦当前本地全栈闭环交付。",
        relatedNoteIds: ["note-001"]
      },
      "owner"
    );
    const updated = await module.updatePlanRecord(
      "plan-new",
      {
        title: "本地全栈闭环",
        summary: "先打通登录、知识、计划和设置。",
        status: "done",
        horizon: "today",
        priority: "critical",
        focusLabel: "闭环推进",
        nextStep: "补完最终验收。",
        nextActionLabel: "打开计划页",
        nextActionHref: "/app/plans",
        searchTerm: "本地闭环",
        agentPrompt: "聚焦当前本地全栈闭环交付。",
        relatedNoteIds: ["note-001"]
      },
      "owner"
    );

    assert.equal(created.id, "plan-new");
    assert.equal(updated.status, "done");
    assert.equal(updated.statusLabel, "已完成");
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});
