import dagre, { type Graph } from "@dagrejs/dagre";
import type { Edge, Node } from "reactflow";

import type { GraphSnapshot, GraphSnapshotEdge, GraphSnapshotNode } from "@/lib/server-api";

export type GraphNodeData = {
  label: string;
  module?: string;
  documentId?: string;
  isActive?: boolean;
  kind: string;
  path: string;
  status: string;
  summary: string;
};

type PathEdge = Pick<Edge, "id" | "source" | "target">;

export function traceUpstreamPath(focusNodeId: string | null, edges: readonly PathEdge[]) {
  const nodeIds = new Set<string>();
  const edgeIds = new Set<string>();
  const adjacency = new Map<string, Set<string>>();
  if (!focusNodeId) {
    return { nodeIds, edgeIds };
  }

  const hasPath = (start: string, destination: string) => {
    const visited = new Set([start]);
    const queue = [start];
    for (let index = 0; index < queue.length; index += 1) {
      const current = queue[index];
      if (current === destination) {
        return true;
      }
      for (const next of adjacency.get(current) ?? []) {
        if (!visited.has(next)) {
          visited.add(next);
          queue.push(next);
        }
      }
    }
    return false;
  };

  nodeIds.add(focusNodeId);
  const queue = [focusNodeId];

  for (let index = 0; index < queue.length; index += 1) {
    const currentNodeId = queue[index];
    for (const edge of edges) {
      if (edge.target !== currentNodeId || hasPath(edge.target, edge.source)) {
        continue;
      }
      edgeIds.add(edge.id);
      const targets = adjacency.get(edge.source) ?? new Set<string>();
      targets.add(edge.target);
      adjacency.set(edge.source, targets);
      if (!nodeIds.has(edge.source)) {
        nodeIds.add(edge.source);
        queue.push(edge.source);
      }
    }
  }

  return { nodeIds, edgeIds };
}

type GraphNodeType = "concept" | "entity" | "action";

const NODE_DIMENSIONS: Record<GraphNodeType, { width: number; height: number }> = {
  concept: { width: 96, height: 96 },
  entity: { width: 220, height: 86 },
  action: { width: 280, height: 48 }
};

export function graphNodeDimensions(type: string | undefined) {
  return type === "concept" || type === "entity" || type === "action"
    ? NODE_DIMENSIONS[type]
    : NODE_DIMENSIONS.action;
}

export function nodeIdsForGraphReason(snapshot: GraphSnapshot, reason?: string) {
  const separator = reason?.indexOf(":") ?? -1;
  if (separator < 0) {
    return [];
  }
  const changedPath = reason?.slice(separator + 1).trim().replaceAll("\\", "/") ?? "";
  const fileName = changedPath.split("/").at(-1)?.toLowerCase();
  if (!fileName?.endsWith(".md")) {
    return [];
  }
  return snapshot.nodes
    .filter((node) => node.path.replaceAll("\\", "/").split("/").at(-1)?.toLowerCase() === fileName)
    .map((node) => node.id);
}

function nodeType(node: GraphSnapshotNode): GraphNodeType {
  if (node.kind === "class") {
    return "entity";
  }
  if (node.kind === "solution") {
    return "action";
  }
  if (node.path.toLowerCase() === "wiki/index.md") {
    return "concept";
  }
  return node.source === "vault" ? "action" : "concept";
}

function nodeModule(node: GraphSnapshotNode) {
  const parts = node.path.split("/");
  return parts.length > 1 ? parts.at(-2) : node.source;
}

function assignHandle(index: number, count: number) {
  if (count <= 1) {
    return 2;
  }
  return Math.round((index * 4) / (count - 1));
}

function edgeHandles(edges: GraphSnapshotEdge[], key: "source" | "target", graph: Graph) {
  const grouped = new Map<string, GraphSnapshotEdge[]>();
  for (const edge of edges) {
    const items = grouped.get(edge[key]) ?? [];
    items.push(edge);
    grouped.set(edge[key], items);
  }

  const handles = new Map<string, string>();
  for (const items of grouped.values()) {
    items
      .sort((left, right) => {
        const leftNeighbor = graph.node(key === "source" ? left.target : left.source);
        const rightNeighbor = graph.node(key === "source" ? right.target : right.source);
        return leftNeighbor.x - rightNeighbor.x || left.id.localeCompare(right.id);
      })
      .forEach((edge, index) => handles.set(edge.id, `${key}-${assignHandle(index, items.length)}`));
  }
  return handles;
}

export function layoutGraphSnapshot(snapshot: GraphSnapshot): {
  nodes: Node<GraphNodeData>[];
  edges: Edge[];
} {
  const graph = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  graph.setGraph({
    rankdir: "TB",
    ranker: "network-simplex",
    nodesep: 80,
    ranksep: 120,
    marginx: 40,
    marginy: 40
  });

  const nodeIds = new Set(snapshot.nodes.map((node) => node.id));
  const validEdges = snapshot.edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target));
  for (const node of snapshot.nodes) {
    graph.setNode(node.id, { ...graphNodeDimensions(nodeType(node)) });
  }
  for (const edge of validEdges) {
    graph.setEdge(edge.source, edge.target);
  }
  dagre.layout(graph);

  const nodeTypes = new Map(snapshot.nodes.map((node) => [node.id, nodeType(node)]));
  const nodeKinds = new Map(snapshot.nodes.map((node) => [node.id, node.kind]));
  const sourceHandles = edgeHandles(validEdges, "source", graph);
  const targetHandles = edgeHandles(validEdges, "target", graph);

  return {
    nodes: snapshot.nodes.map((node) => {
      const type = nodeTypes.get(node.id) ?? "concept";
      const dimensions = graphNodeDimensions(type);
      const position = graph.node(node.id);
      return {
        id: node.id,
        type,
        position: {
          x: position.x - dimensions.width / 2,
          y: position.y - dimensions.height / 2
        },
        data: {
          label: node.label,
          module: nodeModule(node),
          documentId: node.source === "unresolved" ? undefined : node.id,
          kind: node.kind,
          path: node.path,
          status: node.status,
          summary: node.summary
        }
      };
    }),
    edges: validEdges.map((edge) => {
      const highlighted = nodeKinds.get(edge.source) === "solution" || nodeKinds.get(edge.target) === "solution";
      return {
        id: edge.id,
        source: edge.source,
        sourceHandle: sourceHandles.get(edge.id),
        target: edge.target,
        targetHandle: targetHandles.get(edge.id),
        type: highlighted ? "step" : "straight",
        animated: highlighted,
        style: {
          stroke: highlighted ? "#10B981" : "#CBD5E0",
          strokeWidth: highlighted ? 2 : 1.5
        }
      };
    })
  };
}
