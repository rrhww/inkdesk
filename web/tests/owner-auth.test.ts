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

test("owner auth helper logs in against the backend when an API base URL is configured", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input, init) => {
    const url = String(input);

    if (url === "http://localhost:8080/api/auth/login") {
      assert.equal(init?.method, "POST");
      assert.equal((init?.headers as Record<string, string> | undefined)?.["Content-Type"], "application/json");
      assert.deepEqual(JSON.parse(String(init.body)), {
        email: "owner@inkvault.local",
        password: "inkvault-owner"
      });

      return createJsonResponse({
        sessionToken: "backend-session-token"
      });
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  }, async () => {
    const module = await import("../lib/owner-auth");
    const result = await module.loginOwner("owner@inkvault.local", "inkvault-owner");

    assert.equal(result?.sessionToken, "backend-session-token");
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("owner auth helper falls back to the local hidden-owner credentials when no API base URL is configured", async () => {
  delete process.env.NEXT_PUBLIC_API_BASE_URL;

  await withMockedFetch(async () => {
    throw new Error("fetch should not be called without an API base URL");
  }, async () => {
    const module = await import("../lib/owner-auth");

    assert.equal((await module.loginOwner("owner@inkvault.local", "inkvault-owner"))?.sessionToken, "owner");
    assert.equal(await module.loginOwner("owner@inkvault.local", "wrong-password"), null);
  });
});

test("owner auth helper falls back to the local hidden-owner credentials when the configured backend is unavailable", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async () => {
    throw new TypeError("fetch failed");
  }, async () => {
    const module = await import("../lib/owner-auth");

    assert.equal((await module.loginOwner("owner@inkvault.local", "inkvault-owner"))?.sessionToken, "owner");
    assert.equal(await module.loginOwner("owner@inkvault.local", "wrong-password"), null);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("owner auth helper forwards the owner session cookie when logging out against the backend", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input, init) => {
    const url = String(input);

    if (url === "http://localhost:8080/api/auth/logout") {
      assert.equal(init?.method, "POST");
      assert.equal(
        (init?.headers as Record<string, string> | undefined)?.Cookie,
        `${OWNER_SESSION_COOKIE}=session-token`
      );
      return new Response(null, { status: 204 });
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  }, async () => {
    const module = await import("../lib/owner-auth");
    await module.logoutOwner("session-token");
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});
