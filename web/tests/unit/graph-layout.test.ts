import { describe, expect, it } from "vitest";

import { layoutGraphSnapshot, nodeIdsForGraphReason, traceUpstreamPath } from "@/lib/graph-layout";
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
});
