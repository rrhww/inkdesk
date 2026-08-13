import dagre from "@dagrejs/dagre";
import type { Edge, Node } from "reactflow";

import type { GraphNodeData } from "@/lib/graph-layout";
import type {
  GraphClassification,
  GraphSnapshot,
  GraphSnapshotEdge,
  GraphSnapshotNode,
  GraphStage
} from "@/lib/server-api";

export const GRAPH_STAGES: ReadonlyArray<{
  id: GraphStage;
  label: string;
  shortLabel: string;
  description: string;
}> = [
  { id: "requirements", label: "需求定义", shortLabel: "需求", description: "PRD、用户故事与产品路线图" },
  { id: "design", label: "方案设计", shortLabel: "方案", description: "技术方案、ADR、接口与数据模型" },
  { id: "implementation", label: "实现准备", shortLabel: "实现", description: "实施计划、模块与 Capability" },
  { id: "verification", label: "验证审计", shortLabel: "验证", description: "测试、评测、Audit 与 Findings" },
  { id: "delivery", label: "发布运维", shortLabel: "交付", description: "Release、部署与运维手册" },
  { id: "knowledge", label: "知识沉淀", shortLabel: "知识", description: "Concept、Source、Schema 与 Reference" }
];

export const GRAPH_DOMAINS: Record<string, string> = {
  product: "Product",
  architecture: "Architecture",
  "harness-agents": "Harness & Agents",
  skills: "Skills",
  repository: "Repository",
  quality: "Quality",
  operations: "Operations",
  general: "General"
};

export type HierarchyLevel = "stage" | "domain" | "document";

export type HierarchyOptions = {
  stage?: GraphStage | null;
  domain?: string | null;
  includeSecondary?: boolean;
  status?: string | null;
  category?: string | null;
  pinnedNodeId?: string | null;
};

export type HierarchyGraph = {
  level: HierarchyLevel;
  nodes: Node<GraphNodeData>[];
  edges: Edge[];
  documents: GraphSnapshotNode[];
  totalDocumentCount: number;
};

const DEFAULT_CLASSIFICATION: GraphClassification = {
  stage: "knowledge",
  domain: "general",
  category: "document",
  importance: "supporting",
  visibility: "secondary",
  origin: "fallback"
};

const IMPORTANCE_ORDER: Record<GraphClassification["importance"], number> = {
  core: 0,
  normal: 1,
  supporting: 2
};

export function classificationForNode(node: GraphSnapshotNode): GraphClassification {
  return node.classification ?? DEFAULT_CLASSIFICATION;
}

export function domainLabel(domain: string) {
  return GRAPH_DOMAINS[domain] ?? domain.replace(/(^|-)([a-z])/g, (_match, separator: string, letter: string) => `${separator ? " " : ""}${letter.toUpperCase()}`);
}

function visibleDocuments(snapshot: GraphSnapshot, options: HierarchyOptions) {
  const pinnedNodeId = options.pinnedNodeId ?? null;
  return snapshot.nodes.filter((node) => {
    if (node.kind === "missing") {
      return false;
    }
    const classification = classificationForNode(node);
    if (classification.visibility === "hidden") {
      return false;
    }
    if (classification.visibility === "secondary" && !options.includeSecondary && node.id !== pinnedNodeId) {
      return false;
    }
    if (options.stage && classification.stage !== options.stage) {
      return false;
    }
    if (options.domain && classification.domain !== options.domain) {
      return false;
    }
    if (options.status && node.status !== options.status) {
      return false;
    }
    if (options.category && classification.category !== options.category) {
      return false;
    }
    return true;
  });
}

function countMissingLinks(snapshot: GraphSnapshot, sourceIds: Set<string>) {
  return snapshot.edges.filter((edge) => sourceIds.has(edge.source) && edge.target.startsWith("missing:")).length;
}

function hierarchyNode(
  id: string,
  position: { x: number; y: number },
  data: GraphNodeData
): Node<GraphNodeData> {
  return {
    id,
    type: "hierarchy",
    position,
    data,
    draggable: false,
    connectable: false,
    selectable: true
  };
}

function stageGraph(snapshot: GraphSnapshot, options: HierarchyOptions): HierarchyGraph {
  const documents = visibleDocuments(snapshot, { ...options, stage: null, domain: null });
  const positions = [
    { x: 0, y: 0 },
    { x: 310, y: 0 },
    { x: 620, y: 0 },
    { x: 620, y: 190 },
    { x: 310, y: 190 },
    { x: 0, y: 190 }
  ];
  const nodes = GRAPH_STAGES.map((stage, index) => {
    const members = documents.filter((document) => classificationForNode(document).stage === stage.id);
    const primaryCount = members.filter((document) => classificationForNode(document).visibility === "primary").length;
    const secondaryCount = snapshot.nodes.filter((document) => {
      const classification = classificationForNode(document);
      return document.kind !== "missing" && classification.visibility === "secondary" && classification.stage === stage.id;
    }).length;
    return hierarchyNode(`stage:${stage.id}`, positions[index], {
      label: stage.label,
      kind: "stage",
      path: stage.id,
      status: "indexed",
      summary: stage.description,
      role: "stage",
      stage: stage.id,
      primaryCount,
      secondaryCount,
      issueCount: countMissingLinks(snapshot, new Set(members.map((member) => member.id))),
      totalCount: members.length
    });
  });
  const groupForNode = new Map(
    documents.map((document) => [document.id, `stage:${classificationForNode(document).stage}`])
  );
  const edges = aggregateEdges(snapshot.edges, groupForNode, new Set(nodes.map((node) => node.id)))
    .map((edge) => ({
      ...edge,
      style: { stroke: "#94A3B8", strokeWidth: 1.5 }
    }));

  return { level: "stage", nodes, edges, documents, totalDocumentCount: documents.length };
}

function aggregateEdges(
  edges: readonly GraphSnapshotEdge[],
  groupForNode: Map<string, string>,
  visibleGroupIds: Set<string>
) {
  const aggregated = new Map<string, Edge>();
  for (const edge of edges) {
    const source = groupForNode.get(edge.source);
    const target = groupForNode.get(edge.target);
    if (!source || !target || source === target || !visibleGroupIds.has(source) || !visibleGroupIds.has(target)) {
      continue;
    }
    const id = `aggregate:${source}:${target}`;
    if (!aggregated.has(id)) {
      aggregated.set(id, {
        id,
        source,
        target,
        type: "smoothstep",
        style: { stroke: "#CBD5E1", strokeWidth: 1.5 }
      });
    }
  }
  return [...aggregated.values()];
}

function domainGraph(snapshot: GraphSnapshot, options: HierarchyOptions): HierarchyGraph {
  const documents = visibleDocuments(snapshot, { ...options, domain: null });
  const domains = [...new Set(documents.map((document) => classificationForNode(document).domain))].sort((left, right) => {
    const leftKnown = Object.keys(GRAPH_DOMAINS).indexOf(left);
    const rightKnown = Object.keys(GRAPH_DOMAINS).indexOf(right);
    if (leftKnown >= 0 || rightKnown >= 0) {
      return (leftKnown < 0 ? Number.MAX_SAFE_INTEGER : leftKnown) - (rightKnown < 0 ? Number.MAX_SAFE_INTEGER : rightKnown);
    }
    return left.localeCompare(right);
  });
  const nodes = domains.map((domain, index) => {
    const members = documents.filter((document) => classificationForNode(document).domain === domain);
    return hierarchyNode(`domain:${options.stage}:${domain}`, { x: (index % 3) * 310, y: Math.floor(index / 3) * 170 }, {
      label: domainLabel(domain),
      kind: "domain",
      path: domain,
      status: "indexed",
      summary: `${members.length} documents in ${domainLabel(domain)}`,
      role: "domain",
      stage: options.stage ?? undefined,
      domain,
      primaryCount: members.filter((member) => classificationForNode(member).visibility === "primary").length,
      secondaryCount: snapshot.nodes.filter((member) => {
        const classification = classificationForNode(member);
        return classification.stage === options.stage && classification.domain === domain && classification.visibility === "secondary";
      }).length,
      issueCount: countMissingLinks(snapshot, new Set(members.map((member) => member.id))),
      totalCount: members.length
    });
  });
  const groupForNode = new Map(documents.map((document) => [document.id, `domain:${options.stage}:${classificationForNode(document).domain}`]));
  const edges = aggregateEdges(snapshot.edges, groupForNode, new Set(nodes.map((node) => node.id)));
  return { level: "domain", nodes, edges, documents, totalDocumentCount: documents.length };
}

function nodeDegree(snapshot: GraphSnapshot) {
  const degree = new Map<string, number>();
  for (const edge of snapshot.edges) {
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1);
  }
  return degree;
}

function layoutDocumentNodes(nodes: Node<GraphNodeData>[], edges: Edge[]) {
  const graph = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "LR", ranker: "network-simplex", nodesep: 44, ranksep: 96, marginx: 32, marginy: 32 });
  for (const node of nodes) {
    graph.setNode(node.id, { width: node.data.role === "health" ? 220 : 244, height: 76 });
  }
  for (const edge of edges) {
    graph.setEdge(edge.source, edge.target);
  }
  dagre.layout(graph);
  return nodes.map((node) => {
    const dimensions = graph.node(node.id);
    return {
      ...node,
      position: { x: dimensions.x - dimensions.width / 2, y: dimensions.y - dimensions.height / 2 }
    };
  });
}

function documentGraph(snapshot: GraphSnapshot, options: HierarchyOptions): HierarchyGraph {
  const allDocuments = visibleDocuments(snapshot, options);
  const sourceIds = new Set(allDocuments.map((document) => document.id));
  const missingEdges = snapshot.edges.filter((edge) => sourceIds.has(edge.source) && edge.target.startsWith("missing:"));
  const degree = nodeDegree(snapshot);
  const ranked = [...allDocuments].sort((left, right) => {
    const importance = IMPORTANCE_ORDER[classificationForNode(left).importance] - IMPORTANCE_ORDER[classificationForNode(right).importance];
    return importance || (degree.get(right.id) ?? 0) - (degree.get(left.id) ?? 0) || left.label.localeCompare(right.label);
  });
  const documentLimit = missingEdges.length ? 29 : 30;
  const selected = ranked.slice(0, documentLimit);
  const pinned = options.pinnedNodeId ? ranked.find((document) => document.id === options.pinnedNodeId) : undefined;
  if (pinned && !selected.some((document) => document.id === pinned.id)) {
    selected.splice(Math.max(0, selected.length - 1), 1, pinned);
  }
  const selectedIds = new Set(selected.map((document) => document.id));
  const documentNodes: Node<GraphNodeData>[] = selected.map((document) => {
    const classification = classificationForNode(document);
    return {
      id: document.id,
      type: "entity",
      position: { x: 0, y: 0 },
      data: {
        label: document.label,
        module: domainLabel(classification.domain),
        documentId: document.source === "unresolved" ? undefined : document.id,
        kind: document.kind,
        path: document.path,
        status: document.status,
        summary: document.summary,
        role: "document" as const,
        stage: classification.stage,
        domain: classification.domain,
        category: classification.category,
        classification
      },
      draggable: false,
      connectable: false
    } satisfies Node<GraphNodeData>;
  });
  const visibleEdges: Edge[] = snapshot.edges
    .filter((edge) => selectedIds.has(edge.source) && selectedIds.has(edge.target))
    .map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: "smoothstep",
      style: { stroke: "#CBD5E1", strokeWidth: 1.5 }
    } satisfies Edge));

  if (missingEdges.length) {
    documentNodes.push(hierarchyNode("health:unresolved", { x: 0, y: 0 }, {
      label: "Unresolved links",
      kind: "missing",
      path: "unresolved",
      status: "attention",
      summary: "Broken knowledge links in this selection",
      role: "health",
      stage: options.stage ?? undefined,
      domain: options.domain ?? undefined,
      issueCount: missingEdges.length,
      totalCount: missingEdges.length
    }));
    const missingSources = [...new Set(missingEdges.map((edge) => edge.source))].filter((source) => selectedIds.has(source));
    for (const source of missingSources) {
      visibleEdges.push({
        id: `unresolved:${source}`,
        source,
        target: "health:unresolved",
        type: "smoothstep",
        style: { stroke: "#E11D48", strokeDasharray: "4 4", strokeWidth: 1.5 }
      });
    }
  }

  return {
    level: "document",
    nodes: layoutDocumentNodes(documentNodes, visibleEdges),
    edges: visibleEdges,
    documents: allDocuments,
    totalDocumentCount: allDocuments.length
  };
}

export function buildHierarchyGraph(snapshot: GraphSnapshot, options: HierarchyOptions): HierarchyGraph {
  if (!options.stage) {
    return stageGraph(snapshot, options);
  }
  if (!options.domain) {
    return domainGraph(snapshot, options);
  }
  return documentGraph(snapshot, options);
}

export function buildRelationGraph(snapshot: GraphSnapshot, options: HierarchyOptions): HierarchyGraph {
  return documentGraph(snapshot, options);
}
