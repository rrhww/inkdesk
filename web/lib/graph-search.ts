import type { Node } from "@xyflow/react";

import type { GraphNodeData } from "@/lib/graph-layout";

function normalize(value: string | undefined) {
  return value?.trim().toLocaleLowerCase() ?? "";
}

function matchScore(node: Node<GraphNodeData>, query: string) {
  const label = normalize(node.data.label);
  const moduleName = normalize(node.data.module);
  const path = normalize(node.data.path);

  if (label === query) return 0;
  if (label.startsWith(query)) return 1;
  if (moduleName === query) return 2;
  if (moduleName.startsWith(query)) return 3;
  if (label.includes(query)) return 4;
  if (moduleName.includes(query)) return 5;
  if (path.includes(query)) return 6;
  return Number.POSITIVE_INFINITY;
}

export function findGraphNodes(nodes: readonly Node<GraphNodeData>[], searchTerm: string, limit = 6) {
  const query = normalize(searchTerm);
  if (!query) {
    return [];
  }

  return nodes
    .map((node) => ({ node, score: matchScore(node, query) }))
    .filter(({ score }) => Number.isFinite(score))
    .sort(
      (left, right) =>
        left.score - right.score ||
        left.node.data.label.localeCompare(right.node.data.label, "en", { sensitivity: "base" }) ||
        left.node.id.localeCompare(right.node.id)
    )
    .slice(0, limit)
    .map(({ node }) => node);
}
