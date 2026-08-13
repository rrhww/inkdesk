import dagre, { type Graph } from "@dagrejs/dagre";
import type { Edge, Node } from "reactflow";

import type { GraphClassification, GraphSnapshot, GraphSnapshotEdge, GraphSnapshotNode, GraphStage } from "@/lib/server-api";

export type GraphNodeData = {
  label: string;
  module?: string;
  documentId?: string;
  isActive?: boolean;
  kind: string;
  path: string;
  status: string;
  summary: string;
  role?: "stage" | "domain" | "document" | "health";
  stage?: GraphStage;
  domain?: string;
  category?: string;
  classification?: GraphClassification;
  primaryCount?: number;
  secondaryCount?: number;
  issueCount?: number;
  totalCount?: number;
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

type GraphNodeType = "concept" | "entity" | "action" | "module";

const NODE_DIMENSIONS: Record<GraphNodeType, { width: number; height: number }> = {
  concept: { width: 96, height: 96 },
  entity: { width: 220, height: 86 },
  action: { width: 280, height: 48 },
  module: { width: 320, height: 220 }
};

export function graphNodeDimensions(type: string | undefined) {
  return type === "concept" || type === "entity" || type === "action" || type === "module"
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
  return node.source === "vault" ? "action" : "entity";
}

function nodeModule(node: GraphSnapshotNode) {
  const parts = node.path.replaceAll("\\", "/").split("/").filter(Boolean);
  const firstSegment = parts[0];
  if (!firstSegment || firstSegment === "..") {
    return node.source;
  }
  if (firstSegment === "src" && parts[1]) {
    return parts[1];
  }
  return firstSegment;
}

type ModuleGroup = {
  id: string;
  label: string;
  memberIds: string[];
};

function moduleGroupId(source: string, module: string) {
  return `module:${source}:${module}`;
}

function deriveModuleGroups(nodes: readonly GraphSnapshotNode[]): ModuleGroup[] {
  const groups = new Map<string, ModuleGroup>();
  for (const node of nodes) {
    if (node.source !== "repo" || node.kind === "solution") {
      continue;
    }
    const moduleName = nodeModule(node);
    const id = moduleGroupId(node.source, moduleName);
    const group = groups.get(id) ?? { id, label: moduleName, memberIds: [] };
    group.memberIds.push(node.id);
    groups.set(id, group);
  }
  return [...groups.values()].filter((group) => group.memberIds.length >= 2);
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
  const graph = new dagre.graphlib.Graph({ compound: true }).setDefaultEdgeLabel(() => ({}));
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
  const moduleGroups = deriveModuleGroups(snapshot.nodes);
  const parentByChildId = new Map(moduleGroups.flatMap((group) => group.memberIds.map((memberId) => [memberId, group.id])));

  for (const group of moduleGroups) {
    graph.setNode(group.id, { ...NODE_DIMENSIONS.module });
  }
  for (const node of snapshot.nodes) {
    graph.setNode(node.id, { ...graphNodeDimensions(nodeType(node)) });
  }
  for (const [childId, parentId] of parentByChildId) {
    graph.setParent(childId, parentId);
  }
  for (const edge of validEdges) {
    graph.setEdge(edge.source, edge.target);
  }
  dagre.layout(graph);

  const nodeTypes = new Map(snapshot.nodes.map((node) => [node.id, nodeType(node)]));
  const nodeKinds = new Map(snapshot.nodes.map((node) => [node.id, node.kind]));
  const sourceHandles = edgeHandles(validEdges, "source", graph);
  const targetHandles = edgeHandles(validEdges, "target", graph);

  const moduleNodes = moduleGroups.map((group) => {
    const layout = graph.node(group.id);
    return {
      id: group.id,
      type: "module",
      position: {
        x: layout.x - layout.width / 2,
        y: layout.y - layout.height / 2
      },
      style: { width: layout.width, height: layout.height },
      data: {
        label: group.label,
        module: group.label,
        kind: "module",
        path: group.label,
        status: "stable",
        summary: ""
      },
      draggable: false,
      selectable: false,
      connectable: false,
      focusable: false,
      zIndex: 0
    } satisfies Node<GraphNodeData>;
  });

  return {
    nodes: [
      ...moduleNodes,
      ...snapshot.nodes.map((node) => {
      const type = nodeTypes.get(node.id) ?? "concept";
      const dimensions = graphNodeDimensions(type);
      const position = graph.node(node.id);
      const parentNode = parentByChildId.get(node.id);
      const parentPosition = parentNode ? graph.node(parentNode) : null;
      const parentTopLeft = parentPosition
        ? { x: parentPosition.x - parentPosition.width / 2, y: parentPosition.y - parentPosition.height / 2 }
        : null;
      const absolutePosition = {
        x: position.x - dimensions.width / 2,
        y: position.y - dimensions.height / 2
      };
      return {
        id: node.id,
        type,
        position: {
          x: parentTopLeft ? absolutePosition.x - parentTopLeft.x : absolutePosition.x,
          y: parentTopLeft ? absolutePosition.y - parentTopLeft.y : absolutePosition.y
        },
        ...(parentNode ? { parentId: parentNode, extent: "parent" as const, zIndex: 1 } : {}),
        data: {
          label: node.label,
          module: nodeModule(node),
          documentId: node.source === "unresolved" ? undefined : node.id,
          kind: node.kind,
          path: node.path,
            status: node.status,
            summary: node.summary,
            role: "document" as const,
            stage: node.classification?.stage,
            domain: node.classification?.domain,
            category: node.classification?.category,
            classification: node.classification
        }
      };
      })
    ],
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

export function toMacroGraph(nodes: readonly Node<GraphNodeData>[], edges: readonly Edge[]) {
  const macroNodes = nodes.filter(
    (node) => !node.parentId && (node.type === "module" || node.data.kind === "concept" || node.data.kind === "solution")
  );
  const visibleNodeIds = new Set(macroNodes.map((node) => node.id));
  const macroIdForNode = new Map(nodes.map((node) => [node.id, node.parentId ?? node.id]));
  const macroEdges = new Map<string, Edge>();

  for (const edge of edges) {
    const source = macroIdForNode.get(edge.source) ?? edge.source;
    const target = macroIdForNode.get(edge.target) ?? edge.target;
    if (source === target || !visibleNodeIds.has(source) || !visibleNodeIds.has(target)) {
      continue;
    }
    const id = `macro:${source}:${target}`;
    if (!macroEdges.has(id)) {
      macroEdges.set(id, {
        ...edge,
        id,
        source,
        target,
        sourceHandle: undefined,
        targetHandle: undefined
      });
    }
  }

  const connectedNodeIds = new Set<string>();
  for (const edge of macroEdges.values()) {
    connectedNodeIds.add(edge.source);
    connectedNodeIds.add(edge.target);
  }
  return layoutViewGraph(
    macroNodes.filter((node) => connectedNodeIds.has(node.id)),
    [...macroEdges.values()],
    "macro"
  );
}

function layoutViewGraph(
  nodes: readonly Node<GraphNodeData>[],
  edges: readonly Edge[],
  mode: "macro" | "task"
): { nodes: Node<GraphNodeData>[]; edges: Edge[] } {
  const graph = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  graph.setGraph({
    rankdir: "TB",
    ranker: "network-simplex",
    nodesep: mode === "macro" ? 96 : 72,
    ranksep: mode === "macro" ? 112 : 96,
    marginx: 40,
    marginy: 40
  });
  const nodeIds = new Set(nodes.map((node) => node.id));
  const validEdges = edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target));

  for (const node of nodes) {
    const dimensions = node.type === "module" ? { width: 240, height: 72 } : graphNodeDimensions(node.type);
    graph.setNode(node.id, dimensions);
  }
  for (const edge of validEdges) {
    graph.setEdge(edge.source, edge.target);
  }
  dagre.layout(graph);

  return {
    nodes: nodes.map((node) => {
      const flatNode: Node<GraphNodeData> = { ...node };
      delete flatNode.parentId;
      delete flatNode.extent;
      const dimensions = node.type === "module" ? { width: 240, height: 72 } : graphNodeDimensions(node.type);
      const position = graph.node(node.id);
      return {
        ...flatNode,
        position: {
          x: position.x - dimensions.width / 2,
          y: position.y - dimensions.height / 2
        },
        ...(node.type === "module" ? { style: { ...node.style, ...dimensions }, zIndex: 0 } : {})
      };
    }),
    edges: validEdges
  };
}

export function deriveTaskFocusGraph(
  nodes: readonly Node<GraphNodeData>[],
  edges: readonly Edge[],
  taskRootId: string | null,
  maxHops = 2
) {
  if (!taskRootId || !nodes.some((node) => node.id === taskRootId)) {
    return { nodes: [], edges: [] };
  }

  const adjacency = new Map<string, Set<string>>();
  for (const edge of edges) {
    const sourceNeighbors = adjacency.get(edge.source) ?? new Set<string>();
    sourceNeighbors.add(edge.target);
    adjacency.set(edge.source, sourceNeighbors);
    const targetNeighbors = adjacency.get(edge.target) ?? new Set<string>();
    targetNeighbors.add(edge.source);
    adjacency.set(edge.target, targetNeighbors);
  }

  const includedIds = new Set([taskRootId]);
  const queue: Array<{ id: string; depth: number }> = [{ id: taskRootId, depth: 0 }];
  for (let index = 0; index < queue.length; index += 1) {
    const current = queue[index];
    if (current.depth >= maxHops) {
      continue;
    }
    for (const neighbor of adjacency.get(current.id) ?? []) {
      if (!includedIds.has(neighbor)) {
        includedIds.add(neighbor);
        queue.push({ id: neighbor, depth: current.depth + 1 });
      }
    }
  }

  return layoutViewGraph(
    nodes.filter((node) => includedIds.has(node.id)),
    edges.filter((edge) => includedIds.has(edge.source) && includedIds.has(edge.target)),
    "task"
  );
}
