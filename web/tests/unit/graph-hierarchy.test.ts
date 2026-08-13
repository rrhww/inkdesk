import { describe, expect, it } from "vitest";

import { buildHierarchyGraph, GRAPH_STAGES } from "@/lib/graph-hierarchy";
import type { GraphClassification, GraphSnapshot, GraphSnapshotNode } from "@/lib/server-api";

function classification(overrides: Partial<GraphClassification> = {}): GraphClassification {
  return {
    stage: "knowledge",
    domain: "general",
    category: "document",
    importance: "normal",
    visibility: "primary",
    origin: "rule",
    ...overrides
  };
}

function node(
  id: string,
  label: string,
  graphClassification: GraphClassification,
  overrides: Partial<GraphSnapshotNode> = {}
): GraphSnapshotNode {
  return {
    id,
    label,
    kind: "document",
    path: `${id}.md`,
    source: "repo",
    status: "stable",
    summary: "",
    classification: graphClassification,
    ...overrides
  };
}

const snapshot: GraphSnapshot = {
  version: "hierarchy",
  generatedAt: "2026-08-04T00:00:00Z",
  stats: { nodeCount: 7, edgeCount: 4, missingCount: 1, classificationWarningCount: 0 },
  nodes: [
    node("prd", "Interview PRD", classification({ stage: "requirements", domain: "product", category: "prd", importance: "core" })),
    node("solution", "Interview Solution", classification({ stage: "design", domain: "architecture", category: "tech-solution", importance: "core" }), { kind: "solution" }),
    node("harness-adr", "Harness ADR", classification({ stage: "design", domain: "harness-agents", category: "adr", importance: "core" })),
    node("test-plan", "Interview Test Plan", classification({ stage: "verification", domain: "quality", category: "test-plan" })),
    node("readme", "Readme", classification({ visibility: "secondary" })),
    node("fixture", "Fixture", classification({ visibility: "hidden" })),
    node("missing:one", "Missing Target", classification({ category: "missing", visibility: "secondary" }), {
      kind: "missing",
      path: "missing-target",
      source: "unresolved",
      status: "missing"
    })
  ],
  edges: [
    { id: "prd-solution", source: "prd", target: "solution", kind: "wikilink" },
    { id: "solution-test", source: "solution", target: "test-plan", kind: "wikilink" },
    { id: "solution-harness", source: "solution", target: "harness-adr", kind: "wikilink" },
    { id: "solution-missing", source: "solution", target: "missing:one", kind: "wikilink" }
  ]
};

describe("hierarchical graph", () => {
  it("starts with exactly the six ordered research and delivery stages", () => {
    const view = buildHierarchyGraph(snapshot, {});

    expect(view.level).toBe("stage");
    expect(view.nodes.map((item) => item.data.stage)).toEqual(GRAPH_STAGES.map((stage) => stage.id));
    expect(view.nodes).toHaveLength(6);
    expect(view.nodes.find((item) => item.data.stage === "design")?.data.primaryCount).toBe(2);
    expect(view.nodes.some((item) => item.data.label === "Fixture")).toBe(false);
    expect(view.edges.map((edge) => [edge.source, edge.target])).toEqual([
      ["stage:requirements", "stage:design"],
      ["stage:design", "stage:verification"]
    ]);
  });

  it("drills from a stage into domain clusters before showing documents", () => {
    const domains = buildHierarchyGraph(snapshot, { stage: "design" });
    const documents = buildHierarchyGraph(snapshot, { stage: "design", domain: "architecture" });

    expect(domains.level).toBe("domain");
    expect(domains.nodes.map((item) => item.data.domain).sort()).toEqual(["architecture", "harness-agents"]);
    expect(documents.level).toBe("document");
    expect(documents.nodes.map((item) => item.id)).toEqual(["solution", "health:unresolved"]);
    expect(documents.nodes.find((item) => item.id === "health:unresolved")?.data.issueCount).toBe(1);
  });

  it("keeps the document canvas at thirty nodes while pinning a selected result", () => {
    const manyNodes = Array.from({ length: 50 }, (_, index) =>
      node(
        `design-${index.toString().padStart(2, "0")}`,
        `Design ${index.toString().padStart(2, "0")}`,
        classification({ stage: "design", domain: "architecture", importance: index === 49 ? "supporting" : "normal" })
      )
    );
    const largeSnapshot: GraphSnapshot = {
      ...snapshot,
      nodes: manyNodes,
      edges: [],
      stats: { nodeCount: manyNodes.length, edgeCount: 0, missingCount: 0, classificationWarningCount: 0 }
    };

    const view = buildHierarchyGraph(largeSnapshot, {
      stage: "design",
      domain: "architecture",
      pinnedNodeId: "design-49"
    });

    expect(view.nodes).toHaveLength(30);
    expect(view.nodes.some((item) => item.id === "design-49")).toBe(true);
    expect(view.totalDocumentCount).toBe(50);
  });

  it("reveals secondary documents only when the content filter is enabled", () => {
    const primary = buildHierarchyGraph(snapshot, { stage: "knowledge", domain: "general" });
    const all = buildHierarchyGraph(snapshot, { stage: "knowledge", domain: "general", includeSecondary: true });

    expect(primary.nodes.some((item) => item.id === "readme")).toBe(false);
    expect(all.nodes.some((item) => item.id === "readme")).toBe(true);
    expect(all.nodes.some((item) => item.id === "fixture")).toBe(false);
  });
});
