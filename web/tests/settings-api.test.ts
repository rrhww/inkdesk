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

test("settings helpers call backend GET and PATCH endpoints and forward the owner session cookie", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input, init) => {
    const url = String(input);

    if (url === "http://localhost:8080/api/admin/settings" && (!init?.method || init.method === "GET")) {
      assert.equal(
        (init?.headers as Record<string, string> | undefined)?.Cookie,
        `${OWNER_SESSION_COOKIE}=session-token`
      );

      return createJsonResponse({
        profile: {
          displayName: "R",
          publicTitle: "构建超级个人工作台的人",
          summary: "原始摘要",
          publicLocation: "Shanghai"
        },
        workbench: {
          defaultPage: "/app",
          compactMode: false,
          showContextRibbon: true
        },
        editor: {
          defaultView: "edit",
          autoSave: true,
          publishReminder: true
        },
        publish: {
          defaultAudience: "public",
          showProvenance: true,
          highlightRecentUpdates: true
        },
        security: {
          ownerEmail: "owner@inkdesk.local",
          sessionMode: "隐藏主人入口",
          sessionDurationLabel: "8 小时"
        }
      });
    }

    if (url === "http://localhost:8080/api/admin/settings" && init?.method === "PATCH") {
      assert.equal(
        (init?.headers as Record<string, string> | undefined)?.Cookie,
        `${OWNER_SESSION_COOKIE}=session-token`
      );
      assert.equal((init?.headers as Record<string, string> | undefined)?.["Content-Type"], "application/json");

      assert.deepEqual(JSON.parse(String(init.body)), {
        profile: {
          displayName: "Inkdesk Owner",
          publicTitle: "本地闭环实验者",
          summary: "更新后的摘要",
          publicLocation: "Shanghai"
        },
        workbench: {
          defaultPage: "/app/plans",
          compactMode: true,
          showContextRibbon: false
        },
        editor: {
          defaultView: "preview",
          autoSave: false,
          publishReminder: false
        },
        publish: {
          defaultAudience: "private",
          showProvenance: false,
          highlightRecentUpdates: false
        }
      });

      return createJsonResponse({
        profile: {
          displayName: "Inkdesk Owner",
          publicTitle: "本地闭环实验者",
          summary: "更新后的摘要",
          publicLocation: "Shanghai"
        },
        workbench: {
          defaultPage: "/app/plans",
          compactMode: true,
          showContextRibbon: false
        },
        editor: {
          defaultView: "preview",
          autoSave: false,
          publishReminder: false
        },
        publish: {
          defaultAudience: "private",
          showProvenance: false,
          highlightRecentUpdates: false
        },
        security: {
          ownerEmail: "owner@inkdesk.local",
          sessionMode: "隐藏主人入口",
          sessionDurationLabel: "8 小时"
        }
      });
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  }, async () => {
    const module = await import("../lib/settings");
    const initialSettings = await module.getSettingsRecord("session-token");

    assert.equal(initialSettings.profile.displayName, "R");
    assert.equal(initialSettings.security.ownerEmail, "owner@inkdesk.local");

    const savedSettings = await module.saveSettingsRecord(
      {
        profile: {
          displayName: "Inkdesk Owner",
          publicTitle: "本地闭环实验者",
          summary: "更新后的摘要",
          publicLocation: "Shanghai"
        },
        workbench: {
          defaultPage: "/app/plans",
          compactMode: true,
          showContextRibbon: false
        },
        editor: {
          defaultView: "preview",
          autoSave: false,
          publishReminder: false
        },
        publish: {
          defaultAudience: "private",
          showProvenance: false,
          highlightRecentUpdates: false
        }
      },
      "session-token"
    );

    assert.equal(savedSettings.profile.displayName, "Inkdesk Owner");
    assert.equal(savedSettings.workbench.defaultPage, "/app/plans");
    assert.equal(savedSettings.publish.defaultAudience, "private");
    assert.equal(savedSettings.security.sessionMode, "隐藏主人入口");
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("settings helpers fall back to mock data when no API base URL is configured", async () => {
  delete process.env.NEXT_PUBLIC_API_BASE_URL;

  await withMockedFetch(async () => {
    throw new Error("fetch should not be called without an API base URL");
  }, async () => {
    const module = await import("../lib/settings");
    const initialSettings = await module.getSettingsRecord();

    assert.equal(initialSettings.profile.displayName, "R");

    const savedSettings = await module.saveSettingsRecord(
      {
        profile: {
          displayName: "Inkdesk Owner",
          publicTitle: initialSettings.profile.publicTitle,
          summary: initialSettings.profile.summary,
          publicLocation: initialSettings.profile.publicLocation
        },
        workbench: initialSettings.workbench,
        editor: initialSettings.editor,
        publish: initialSettings.publish
      },
      undefined
    );

    assert.equal(savedSettings.profile.displayName, "Inkdesk Owner");
    assert.equal(savedSettings.security.ownerEmail, initialSettings.security.ownerEmail);
  });
});
