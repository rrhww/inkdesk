import { describe, expect, it } from "vitest";

import {
  deriveTaskFocusGraph,
  layoutGraphSnapshot,
  nodeIdsForGraphReason,
  toMacroGraph,
  traceUpstreamPath
} from "@/lib/graph-layout";
import type { GraphSnapshot } from "@/lib/server-api";

const snapshot: GraphSnapshot = {
  version: "v1",
  generatedAt: "2026-07-20T00:00:00Z",
  stats: { nodeCount: 4, edgeCount: 3, missingCount: 0 },
  nodes: [
    { id: "vault:wiki/index.md", label: "Index", kind: "concept", path: "wiki/index.md", source: "vault", status: "stable", summary: "" },
    { id: "vault:wiki/api.md", label: "API", kind: "class", path: "wiki/api.md", source: "vault", status: "stable", summary: "" },
    { id: "vault:wiki/solution.md", label: "Solution", kind: "solution", path: "wiki/solution.md", source: "vault", status: "stable", summary: "" },
    { id: "vault:wiki/other.md", label: "Other", kind: "concept", path: "wiki/other.md", source: "vault", status: "stable", summary: "" }
  ],
  edges: [
    { id: "edge-1", source: "vault:wiki/index.md", target: "vault:wiki/api.md", kind: "wikilink" },
    { id: "edge-2", source: "vault:wiki/index.md", target: "vault:wiki/solution.md", kind: "wikilink" },
    { id: "edge-3", source: "vault:wiki/index.md", target: "vault:wiki/other.md", kind: "wikilink" }
  ]
};

describe("graph layout", () => {
  it("maps backend kinds, lays out layers deterministically, and separates edge handles", () => {
    const first = layoutGraphSnapshot(snapshot);
    const second = layoutGraphSnapshot(snapshot);

    expect(first).toEqual(second);
    expect(Object.fromEntries(first.nodes.map((node) => [node.id, node.type]))).toEqual({
      "vault:wiki/index.md": "concept",
      "vault:wiki/api.md": "entity",
      "vault:wiki/solution.md": "action",
      "vault:wiki/other.md": "action"
    });

    const index = first.nodes.find((node) => node.id === "vault:wiki/index.md");
    const targets = first.nodes.filter((node) => node.id !== "vault:wiki/index.md");
    expect(index).toBeDefined();
    expect(targets.every((node) => node.position.y > index!.position.y)).toBe(true);
    expect(new Set(first.edges.map((edge) => edge.sourceHandle)).size).toBe(3);
    expect(first.edges.filter((edge) => edge.type === "straight")).toHaveLength(2);
    expect(first.edges.filter((edge) => edge.type === "step")).toHaveLength(1);
  });

  it("traces every upstream node and edge without looping on cycles", () => {
    const focus = traceUpstreamPath("target", [
      { id: "root-a", source: "root", target: "branch-a" },
      { id: "root-b", source: "root", target: "branch-b" },
      { id: "a-target", source: "branch-a", target: "target" },
      { id: "b-target", source: "branch-b", target: "target" },
      { id: "cycle", source: "target", target: "root" },
      { id: "unrelated", source: "other", target: "elsewhere" }
    ]);

    expect([...focus.nodeIds].sort()).toEqual(["branch-a", "branch-b", "root", "target"]);
    expect([...focus.edgeIds].sort()).toEqual(["a-target", "b-target", "root-a", "root-b"]);
  });

  it("returns an empty focus when no node is active", () => {
    const focus = traceUpstreamPath(null, snapshot.edges);

    expect(focus.nodeIds.size).toBe(0);
    expect(focus.edgeIds.size).toBe(0);
  });

  it("maps watchdog reasons to the changed Vault node", () => {
    expect(nodeIdsForGraphReason(snapshot, "modified:api.md")).toEqual(["vault:wiki/api.md"]);
    expect(nodeIdsForGraphReason(snapshot, "startup")).toEqual([]);
    expect(nodeIdsForGraphReason(snapshot, "modified:module.py")).toEqual([]);
  });

  it("groups related code entities into a parent module with relative child positions", () => {
    const grouped = layoutGraphSnapshot({
      ...snapshot,
      nodes: [
        snapshot.nodes[0],
        { id: "repo:link-service/order.ts", label: "OrderBookingService", kind: "class", path: "src/link-service/order.ts", source: "repo", status: "stable", summary: "" },
        { id: "repo:link-service/context.ts", label: "BookingContextFactory", kind: "class", path: "src/link-service/context.ts", source: "repo", status: "stable", summary: "" },
        snapshot.nodes[2]
      ],
      edges: [
        { id: "root-order", source: "vault:wiki/index.md", target: "repo:link-service/order.ts", kind: "wikilink" },
        { id: "root-context", source: "vault:wiki/index.md", target: "repo:link-service/context.ts", kind: "wikilink" },
        { id: "order-solution", source: "repo:link-service/order.ts", target: "vault:wiki/solution.md", kind: "wikilink" }
      ],
      stats: { nodeCount: 4, edgeCount: 3, missingCount: 0 }
    });

    const module = grouped.nodes.find((node) => node.id === "module:repo:link-service");
    const children = grouped.nodes.filter((node) => node.parentId === module?.id);

    expect(module).toMatchObject({ type: "module", draggable: false, selectable: false });
    expect(module?.style).toMatchObject({ width: expect.any(Number), height: expect.any(Number) });
    expect(children).toHaveLength(2);
    expect(children.every((node) => node.extent === "parent")).toBe(true);
    expect(children.every((node) => node.position.x >= 0 && node.position.y >= 0)).toBe(true);
    expect(grouped.nodes.findIndex((node) => node.id === module?.id)).toBeLessThan(
      grouped.nodes.findIndex((node) => node.id === children[0]?.id)
    );
  });

  it("collapses child edges into deduplicated macro edges", () => {
    const grouped = layoutGraphSnapshot({
      ...snapshot,
      nodes: [
        snapshot.nodes[0],
        { id: "repo:link-service/order.ts", label: "OrderBookingService", kind: "class", path: "src/link-service/order.ts", source: "repo", status: "stable", summary: "" },
        { id: "repo:link-service/context.ts", label: "BookingContextFactory", kind: "class", path: "src/link-service/context.ts", source: "repo", status: "stable", summary: "" }
      ],
      edges: [
        { id: "root-order", source: "vault:wiki/index.md", target: "repo:link-service/order.ts", kind: "wikilink" },
        { id: "root-context", source: "vault:wiki/index.md", target: "repo:link-service/context.ts", kind: "wikilink" }
      ],
      stats: { nodeCount: 3, edgeCount: 2, missingCount: 0 }
    });

    const macro = toMacroGraph(grouped.nodes, grouped.edges);

    expect(macro.nodes.map((node) => node.id).sort()).toEqual(["module:repo:link-service", "vault:wiki/index.md"]);
    expect(macro.edges).toHaveLength(1);
    expect(macro.edges[0]).toMatchObject({ source: "vault:wiki/index.md", target: "module:repo:link-service" });
  });

  it("keeps a bounded task focus subgraph and returns empty without a task root", () => {
    const layout = layoutGraphSnapshot(snapshot);
    const focused = deriveTaskFocusGraph(layout.nodes, layout.edges, "vault:wiki/solution.md", 1);

    expect(focused.nodes.map((node) => node.id).sort()).toEqual(["vault:wiki/index.md", "vault:wiki/solution.md"]);
    expect(focused.edges.map((edge) => edge.id)).toEqual(["edge-2"]);
    expect(deriveTaskFocusGraph(layout.nodes, layout.edges, null)).toEqual({ nodes: [], edges: [] });
  });
});
