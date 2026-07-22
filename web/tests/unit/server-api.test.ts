import { afterEach, describe, expect, it, vi } from "vitest";

import { resolveApiBaseUrl, ServerAPI } from "@/lib/server-api";

describe("server API base URL", () => {
  const originalPublicApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  afterEach(() => {
    vi.unstubAllGlobals();
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

  it("subscribes to named graph events and leaves reconnects to EventSource", () => {
    const statuses: string[] = [];
    const events: unknown[] = [];
    const listeners = new Map<string, (event: MessageEvent<string>) => void>();
    const close = vi.fn();

    class FakeEventSource {
      static instance: FakeEventSource;
      onopen: ((event: Event) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;

      constructor(readonly url: string) {
        FakeEventSource.instance = this;
      }

      addEventListener(type: string, listener: EventListenerOrEventListenerObject) {
        listeners.set(type, listener as (event: MessageEvent<string>) => void);
      }

      close = close;
    }

    vi.stubGlobal("EventSource", FakeEventSource);
    const unsubscribe = ServerAPI.subscribeToGraphEvents(
      (event) => events.push(event),
      (status) => statuses.push(status)
    );
    const source = FakeEventSource.instance;
    const snapshot = {
      version: "v1",
      generatedAt: "now",
      nodes: [],
      edges: [],
      stats: { nodeCount: 0, edgeCount: 0, missingCount: 0 }
    };

    expect(source.url).toBe("/api/graph/stream");
    expect(statuses).toEqual(["connecting"]);
    source.onopen?.(new Event("open"));
    listeners.get("graph.snapshot")?.(new MessageEvent("graph.snapshot", { data: JSON.stringify(snapshot) }));
    listeners.get("graph.updated")?.(
      new MessageEvent("graph.updated", {
        data: JSON.stringify({ event: "graph.updated", reason: "modified:core.md", snapshot })
      })
    );
    listeners.get("node_active")?.(
      new MessageEvent("node_active", { data: JSON.stringify({ node_id: "vault:wiki/core.md" }) })
    );
    source.onerror?.(new Event("error"));

    expect(statuses).toEqual(["connecting", "connected", "offline"]);
    expect(events).toEqual([
      { type: "graph.snapshot", snapshot },
      { type: "graph.updated", reason: "modified:core.md", snapshot },
      { type: "node.active", nodeId: "vault:wiki/core.md" }
    ]);
    expect(close).not.toHaveBeenCalled();

    unsubscribe();
    expect(close).toHaveBeenCalledOnce();
  });

  it("loads all, vault, and repository graph scopes with encoded graph documents", async () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8080";
    const originalFetch = globalThis.fetch;
    const calls: string[] = [];
    globalThis.fetch = async (input) => {
      calls.push(String(input));
      return new Response(JSON.stringify({ version: "v1", generatedAt: "now", nodes: [], edges: [], stats: {} }));
    };

    try {
      await ServerAPI.fetchGraphTopology();
      await ServerAPI.fetchGraphTopology("vault");
      await ServerAPI.fetchGraphTopology("repo");
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
      "/api/graph",
      "/api/graph?source=vault",
      "/api/graph?source=repo",
      "/api/graph/document?nodeId=vault%3Awiki%2Fcore.md"
    ]);
  });

  it("subscribes the stream to the requested graph scope", () => {
    const urls: string[] = [];

    class FakeEventSource {
      onopen: ((event: Event) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;

      constructor(readonly url: string) {
        urls.push(url);
      }

      addEventListener() {}
      close() {}
    }

    vi.stubGlobal("EventSource", FakeEventSource);
    ServerAPI.subscribeToGraphEvents(() => undefined, () => undefined, "vault")();
    ServerAPI.subscribeToGraphEvents(() => undefined, () => undefined, "repo")();

    expect(urls).toEqual(["/api/graph/stream?source=vault", "/api/graph/stream?source=repo"]);
  });
});
