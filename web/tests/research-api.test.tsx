import assert from "node:assert/strict";
import test from "node:test";

import {
  getResearchTopicDetailFixture,
  researchDashboardFixture,
  researchSourcesFixture,
  researchTopicSummariesFixture,
  vaultHealthFixture,
} from "../lib/mock/research-fixtures";

type FetchCall = { input: RequestInfo | URL; init?: RequestInit };

function json(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

async function withMockedFetch(
  responder: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response> | Response,
  run: (calls: FetchCall[]) => Promise<void>,
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

test("read-only research helpers call only observer endpoints", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";
  const detail = getResearchTopicDetailFixture("topic-001");
  assert.ok(detail);

  await withMockedFetch((input) => {
    const pathname = new URL(String(input)).pathname;
    if (pathname === "/api/admin/home") return json(researchDashboardFixture);
    if (pathname === "/api/wiki") return json(researchTopicSummariesFixture);
    if (pathname === "/api/wiki/topic-001") return json(detail);
    if (pathname === "/api/raw") return json(researchSourcesFixture);
    if (pathname === "/api/health") return json(vaultHealthFixture);
    if (pathname === "/api/skills") {
      return json({ total: 0, valid: 0, invalid: 0, byStatus: { draft: 0, active: 0, deprecated: 0 }, skills: [] });
    }
    throw new Error(`Unexpected fetch URL: ${pathname}`);
  }, async (calls) => {
    const research = await import("../lib/research");

    assert.equal((await research.getResearchDashboard()).summary.activeTopics, researchDashboardFixture.summary.activeTopics);
    assert.equal((await research.getWikiPages())[0]?.id, "topic-001");
    assert.equal((await research.getWikiDetail("topic-001")).id, "topic-001");
    assert.equal((await research.getRawSources())[0]?.id, researchSourcesFixture[0]?.id);
    assert.equal((await research.getVaultHealth()).summary.totalPages, vaultHealthFixture.summary.totalPages);
    assert.equal((await research.getSkills()).total, 0);

    assert.deepEqual(
      calls.map((call) => new URL(String(call.input)).pathname),
      ["/api/admin/home", "/api/wiki", "/api/wiki/topic-001", "/api/raw", "/api/health", "/api/skills"],
    );
    assert.ok(calls.every((call) => !call.init?.method || call.init.method === "GET"));
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("observer helpers fall back to local topology fixtures without an API base URL", async () => {
  delete process.env.NEXT_PUBLIC_API_BASE_URL;
  delete process.env.INKDESK_API_BASE_URL;
  const research = await import("../lib/research");

  assert.equal(await research.getResearchDashboard(), researchDashboardFixture);
  assert.equal(await research.getWikiPages(), researchTopicSummariesFixture);
  assert.equal(await research.getRawSources(), researchSourcesFixture);
  assert.equal(await research.getVaultHealth(), vaultHealthFixture);
});
