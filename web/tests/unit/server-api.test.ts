import { afterEach, describe, expect, it } from "vitest";

import { resolveApiBaseUrl, ServerAPI } from "@/lib/server-api";

describe("server API base URL", () => {
  const originalPublicApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  afterEach(() => {
    if (originalPublicApiBaseUrl === undefined) {
      delete process.env.NEXT_PUBLIC_API_BASE_URL;
      return;
    }

    process.env.NEXT_PUBLIC_API_BASE_URL = originalPublicApiBaseUrl;
  });

  it("uses the same-origin API rewrite from browser code", () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8080";

    expect(resolveApiBaseUrl()).toBe("/api");
  });

  it("loads the vault graph and encoded graph documents from the graph engine", async () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8080";
    const originalFetch = globalThis.fetch;
    const calls: string[] = [];
    globalThis.fetch = async (input) => {
      calls.push(String(input));
      return new Response(JSON.stringify({ version: "v1", generatedAt: "now", nodes: [], edges: [], stats: {} }));
    };

    try {
      await ServerAPI.fetchGraphTopology();
      globalThis.fetch = async (input) => {
        calls.push(String(input));
        return new Response(JSON.stringify({
          id: "vault:wiki/core.md",
          title: "Core",
          sourcePath: "wiki/core.md",
          content: "# Core"
        }));
      };
      await ServerAPI.fetchNodeDocument("vault:wiki/core.md");
    } finally {
      globalThis.fetch = originalFetch;
    }

    expect(calls).toEqual([
      "/api/graph?source=vault",
      "/api/graph/document?nodeId=vault%3Awiki%2Fcore.md"
    ]);
  });
});
