"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronRight, RotateCw, X } from "lucide-react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlowProvider,
  useStore,
  type Node
} from "reactflow";
import "reactflow/dist/style.css";

import { ActionNode, ConceptNode, EntityNode, HierarchyNode, ModuleGroupNode } from "@/components/ui/graph-nodes";
import { GraphFilterControl } from "@/components/workbench/graph-filter-control";
import { GraphNavigator } from "@/components/workbench/graph-navigator";
import { GraphScopeControl } from "@/components/workbench/graph-scope-control";
import { GraphSearch } from "@/components/workbench/graph-search";
import { GraphViewControl, type GraphViewMode } from "@/components/workbench/graph-view-control";
import { MarkdownViewer } from "@/components/workbench/markdown-viewer";
import {
  buildHierarchyGraph,
  buildRelationGraph,
  classificationForNode,
  domainLabel,
  GRAPH_STAGES
} from "@/lib/graph-hierarchy";
import {
  deriveTaskFocusGraph,
  layoutGraphSnapshot,
  nodeIdsForGraphReason,
  traceUpstreamPath,
  type GraphNodeData
} from "@/lib/graph-layout";
import {
  ServerAPI,
  type GraphNodeDocument,
  type GraphScope,
  type GraphSnapshot,
  type GraphSnapshotNode,
  type GraphStage,
  type GraphStreamStatus
} from "@/lib/server-api";

type ReaderState =
  | { status: "idle" }
  | { status: "ready"; nodeId: string; document: GraphNodeDocument }
  | { status: "error"; nodeId: string };

type GraphStatus = "loading" | "ready" | "empty" | "error";

type NavigationState = {
  view: GraphViewMode;
  scope: GraphScope;
  stage: GraphStage | null;
  domain: string | null;
  includeSecondary: boolean;
  status: string;
  category: string;
  node: string | null;
};

const DEFAULT_NAVIGATION: NavigationState = {
  view: "flow",
  scope: "all",
  stage: null,
  domain: null,
  includeSecondary: false,
  status: "",
  category: "",
  node: null
};

const graphStatusLabels: Record<GraphStatus, string> = {
  loading: "GRAPH SYNCING",
  ready: "GRAPH SYNC ACTIVE",
  empty: "GRAPH EMPTY",
  error: "GRAPH SYNC OFFLINE"
};

const streamStatusLabels: Record<GraphStreamStatus, string> = {
  connecting: "STREAM CONNECTING",
  connected: "GRAPH SYNC ACTIVE",
  offline: "STREAM OFFLINE"
};

const SEMANTIC_ZOOM_THRESHOLD = 0.4;

function validView(value: string | null): GraphViewMode {
  return value === "relations" || value === "task" || value === "raw" ? value : "flow";
}

function validScope(value: string | null): GraphScope {
  return value === "vault" || value === "repo" ? value : "all";
}

function validStage(value: string | null): GraphStage | null {
  return GRAPH_STAGES.some((stage) => stage.id === value) ? value as GraphStage : null;
}

function readNavigation(): NavigationState {
  if (typeof window === "undefined") {
    return DEFAULT_NAVIGATION;
  }
  const params = new URLSearchParams(window.location.search);
  return {
    view: validView(params.get("view")),
    scope: validScope(params.get("scope")),
    stage: validStage(params.get("stage")),
    domain: params.get("domain") || null,
    includeSecondary: params.get("content") === "all",
    status: params.get("status") || "",
    category: params.get("category") || "",
    node: params.get("node") || null
  };
}

function navigationUrl(navigation: NavigationState) {
  const url = new URL(window.location.href);
  const params = url.searchParams;
  const entries: Array<[string, string | null]> = [
    ["view", navigation.view === "flow" ? null : navigation.view],
    ["scope", navigation.scope === "all" ? null : navigation.scope],
    ["stage", navigation.stage],
    ["domain", navigation.domain],
    ["content", navigation.includeSecondary ? "all" : null],
    ["status", navigation.status || null],
    ["category", navigation.category || null],
    ["node", navigation.node]
  ];
  for (const [key, value] of entries) {
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
  }
  return `${url.pathname}${params.size ? `?${params.toString()}` : ""}`;
}

function emptySnapshot(): GraphSnapshot {
  return {
    version: "empty",
    generatedAt: new Date(0).toISOString(),
    nodes: [],
    edges: [],
    stats: { nodeCount: 0, edgeCount: 0, missingCount: 0, classificationWarningCount: 0 }
  };
}

function InkdeskGraphCanvas() {
  const [navigation, setNavigation] = useState<NavigationState>(() => readNavigation());
  const [snapshot, setSnapshot] = useState<GraphSnapshot>(() => emptySnapshot());
  const [graphStatus, setGraphStatus] = useState<GraphStatus>("loading");
  const [streamStatus, setStreamStatus] = useState<GraphStreamStatus>("connecting");
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [searchedNodeId, setSearchedNodeId] = useState<string | null>(null);
  const [streamActiveNodeIds, setStreamActiveNodeIds] = useState<Set<string>>(() => new Set());
  const [taskFocusRootId, setTaskFocusRootId] = useState<string | null>(null);
  const [readerState, setReaderState] = useState<ReaderState>({ status: "idle" });
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const graphRequestRef = useRef(0);
  const pulseTimerRef = useRef<number | null>(null);
  const navigationReadyRef = useRef(typeof window !== "undefined");
  const zoom = useStore((state) => state.transform[2]);

  const nodeTypes = useMemo(
    () => ({
      concept: ConceptNode,
      entity: EntityNode,
      action: ActionNode,
      module: ModuleGroupNode,
      hierarchy: HierarchyNode
    }),
    []
  );

  useEffect(() => {
    const onPopState = () => setNavigation(readNavigation());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const updateNavigation = useCallback((updates: Partial<NavigationState>, replace = false) => {
    setNavigation((current) => {
      const next = { ...current, ...updates };
      if (navigationReadyRef.current) {
        const url = navigationUrl(next);
        window.history[replace ? "replaceState" : "pushState"]({}, "", url);
      }
      return next;
    });
  }, []);

  const rawLayout = useMemo(() => layoutGraphSnapshot(snapshot), [snapshot]);
  const rawNodeById = useMemo(() => new Map(rawLayout.nodes.map((node) => [node.id, node])), [rawLayout.nodes]);
  const rawDocumentById = useMemo(() => new Map(snapshot.nodes.map((node) => [node.id, node])), [snapshot.nodes]);
  const selectedNode = navigation.node ? rawNodeById.get(navigation.node) ?? null : null;
  const hierarchyOptions = useMemo(
    () => ({
      stage: navigation.stage,
      domain: navigation.domain,
      includeSecondary: navigation.includeSecondary,
      status: navigation.status || null,
      category: navigation.category || null,
      pinnedNodeId: navigation.node
    }),
    [navigation]
  );
  const hierarchyGraph = useMemo(() => buildHierarchyGraph(snapshot, hierarchyOptions), [hierarchyOptions, snapshot]);
  const relationGraph = useMemo(() => buildRelationGraph(snapshot, hierarchyOptions), [hierarchyOptions, snapshot]);
  const taskRootId = useMemo(() => {
    const candidates = [
      taskFocusRootId,
      selectedNode?.data.kind === "solution" ? selectedNode.id : null,
      rawLayout.nodes.find((node) => node.data.kind === "solution")?.id ?? null
    ];
    return candidates.find((nodeId) => nodeId && rawLayout.nodes.some((node) => node.id === nodeId && node.data.kind === "solution")) ?? null;
  }, [rawLayout.nodes, selectedNode, taskFocusRootId]);
  const taskGraph = useMemo(
    () => deriveTaskFocusGraph(rawLayout.nodes, rawLayout.edges, taskRootId),
    [rawLayout.edges, rawLayout.nodes, taskRootId]
  );
  const viewGraph = useMemo(() => {
    if (navigation.view === "relations") {
      return relationGraph;
    }
    if (navigation.view === "task") {
      return taskGraph;
    }
    if (navigation.view === "raw") {
      return rawLayout;
    }
    return hierarchyGraph;
  }, [hierarchyGraph, navigation.view, rawLayout, relationGraph, taskGraph]);
  const searchNodes = useMemo(
    () => rawLayout.nodes.filter((node) => node.data.documentId && node.data.classification?.visibility !== "hidden"),
    [rawLayout.nodes]
  );
  const focusedNodeId = hoveredNodeId ?? searchedNodeId ?? selectedNode?.id ?? null;
  const interactionFocusedNodeId = viewGraph.nodes.some((node) => node.id === focusedNodeId) ? focusedNodeId : null;
  const focusedPath = useMemo(
    () => traceUpstreamPath(interactionFocusedNodeId, viewGraph.edges),
    [interactionFocusedNodeId, viewGraph.edges]
  );
  const visibleNodes = useMemo(() => viewGraph.nodes.map((node) => {
    const dimmed = interactionFocusedNodeId && !focusedPath.nodeIds.has(node.id);
    const hiddenAtDistance = navigation.view === "raw" && zoom < SEMANTIC_ZOOM_THRESHOLD && Boolean(node.parentId);
    return {
      ...node,
      className: [
        node.className,
        "transition-opacity duration-200 motion-reduce:transition-none",
        hiddenAtDistance ? "pointer-events-none opacity-0" : "",
        dimmed ? "opacity-25" : interactionFocusedNodeId ? "z-10 opacity-100" : ""
      ].filter(Boolean).join(" "),
      data: {
        ...node.data,
        isActive: node.id === interactionFocusedNodeId || streamActiveNodeIds.has(node.id)
      }
    };
  }), [focusedPath.nodeIds, interactionFocusedNodeId, navigation.view, streamActiveNodeIds, viewGraph.nodes, zoom]);
  const visibleEdges = useMemo(() => {
    if (navigation.view === "raw" && zoom < SEMANTIC_ZOOM_THRESHOLD) {
      return [];
    }
    if (!interactionFocusedNodeId) {
      return viewGraph.edges;
    }
    return viewGraph.edges.map((edge) => {
      const isFocused = focusedPath.edgeIds.has(edge.id);
      return {
        ...edge,
        animated: isFocused,
        style: {
          ...edge.style,
          stroke: isFocused ? "#059669" : "#CBD5E0",
          strokeWidth: isFocused ? 2.5 : edge.style?.strokeWidth,
          opacity: isFocused ? 1 : 0.12,
          transition: "stroke 200ms ease-out, stroke-width 200ms ease-out, opacity 200ms ease-out"
        }
      };
    });
  }, [focusedPath.edgeIds, interactionFocusedNodeId, navigation.view, viewGraph.edges, zoom]);

  const pulseNodes = useCallback((nodeIds: string[]) => {
    if (!nodeIds.length) {
      return;
    }
    setStreamActiveNodeIds(new Set(nodeIds));
    if (pulseTimerRef.current !== null) {
      window.clearTimeout(pulseTimerRef.current);
    }
    pulseTimerRef.current = window.setTimeout(() => {
      setStreamActiveNodeIds(new Set());
      pulseTimerRef.current = null;
    }, 3000);
  }, []);

  const applyGraphSnapshot = useCallback((nextSnapshot: GraphSnapshot) => {
    setSnapshot(nextSnapshot);
    setGraphStatus(nextSnapshot.nodes.length ? "ready" : "empty");
    setNavigation((current) => current.node && !nextSnapshot.nodes.some((node) => node.id === current.node)
      ? { ...current, node: null }
      : current);
  }, []);

  const syncGraph = useCallback(async () => {
    const requestId = graphRequestRef.current + 1;
    graphRequestRef.current = requestId;
    setGraphStatus("loading");
    try {
      const nextSnapshot = await ServerAPI.fetchGraphTopology(navigation.scope);
      if (graphRequestRef.current === requestId) {
        applyGraphSnapshot(nextSnapshot);
      }
    } catch {
      if (graphRequestRef.current === requestId) {
        setSnapshot(emptySnapshot());
        setGraphStatus("error");
      }
    }
  }, [applyGraphSnapshot, navigation.scope]);

  useEffect(() => {
    const timer = window.setTimeout(() => void syncGraph(), 0);
    return () => {
      window.clearTimeout(timer);
      graphRequestRef.current += 1;
    };
  }, [syncGraph]);

  useEffect(() => {
    const unsubscribe = ServerAPI.subscribeToGraphEvents(
      (event) => {
        if (event.type === "node.active") {
          pulseNodes([event.nodeId]);
          setTaskFocusRootId(event.nodeId);
          return;
        }
        if (event.type === "node.idle") {
          setStreamActiveNodeIds((current) => {
            const next = new Set(current);
            next.delete(event.nodeId);
            return next;
          });
          return;
        }
        graphRequestRef.current += 1;
        applyGraphSnapshot(event.snapshot);
        if (event.type === "graph.updated") {
          pulseNodes(nodeIdsForGraphReason(event.snapshot, event.reason));
        }
      },
      setStreamStatus,
      navigation.scope
    );
    return () => {
      unsubscribe();
      if (pulseTimerRef.current !== null) {
        window.clearTimeout(pulseTimerRef.current);
      }
    };
  }, [applyGraphSnapshot, navigation.scope, pulseNodes]);

  const openDocument = useCallback((document: GraphSnapshotNode, pushHistory = true) => {
    const node = rawNodeById.get(document.id);
    if (!node?.data.documentId) {
      return;
    }
    const classification = classificationForNode(document);
    setSearchedNodeId(node.id);
    if (node.data.kind === "solution") {
      setTaskFocusRootId(node.id);
    }
    updateNavigation(
      {
        stage: classification.stage,
        domain: classification.domain,
        node: document.id,
        view: navigation.view === "raw" || navigation.view === "task" ? navigation.view : "flow"
      },
      !pushHistory
    );
  }, [navigation.view, rawNodeById, updateNavigation]);

  const closeReader = useCallback(() => {
    setSearchedNodeId(null);
    updateNavigation({ node: null });
  }, [updateNavigation]);

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node<GraphNodeData>) => {
    if (node.data.role === "stage" && node.data.stage) {
      updateNavigation({ stage: node.data.stage, domain: null, node: null });
      return;
    }
    if (node.data.role === "domain" && node.data.domain) {
      updateNavigation({ domain: node.data.domain, node: null });
      return;
    }
    const document = rawDocumentById.get(node.id);
    if (document) {
      openDocument(document);
    }
  }, [openDocument, rawDocumentById, updateNavigation]);

  const onGraphKeyDown = useCallback((event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    const nodeId = (event.target as HTMLElement).closest<HTMLElement>(".react-flow__node")?.dataset.id;
    const node = viewGraph.nodes.find((candidate) => candidate.id === nodeId);
    if (!node) {
      return;
    }
    event.preventDefault();
    onNodeClick(event as unknown as React.MouseEvent, node);
  }, [onNodeClick, viewGraph.nodes]);

  useEffect(() => {
    const documentId = selectedNode?.data.documentId;
    if (!documentId) {
      return;
    }
    let active = true;
    ServerAPI.fetchNodeDocument(documentId)
      .then((document) => {
        if (active) {
          setReaderState({ status: "ready", nodeId: documentId, document });
        }
      })
      .catch(() => {
        if (active) {
          setReaderState({ status: "error", nodeId: documentId });
        }
      });
    return () => {
      active = false;
    };
  }, [selectedNode]);

  useEffect(() => {
    if (!selectedNode) {
      return;
    }
    closeButtonRef.current?.focus({ preventScroll: true });
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeReader();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [closeReader, selectedNode]);

  const baseStatusLabel = graphStatus === "ready" ? streamStatusLabels[streamStatus] : graphStatusLabels[graphStatus];
  const statusLabel = graphStatus === "ready" ? `${baseStatusLabel} / ${snapshot.stats.nodeCount} DOCUMENTS` : baseStatusLabel;
  const statusColor = graphStatus === "error" || (graphStatus === "ready" && streamStatus === "offline")
    ? "bg-rose-500"
    : graphStatus === "ready" && streamStatus === "connected"
      ? "bg-emerald-500"
      : "bg-amber-400";
  const statuses = useMemo(() => [...new Set(snapshot.nodes.filter((node) => node.kind !== "missing").map((node) => node.status))].sort(), [snapshot.nodes]);
  const categories = useMemo(() => [...new Set(snapshot.nodes.filter((node) => node.kind !== "missing").map((node) => classificationForNode(node).category))].sort(), [snapshot.nodes]);
  const navigatorDocuments = useMemo(() => snapshot.nodes.filter((node) => {
    const classification = classificationForNode(node);
    return node.kind !== "missing"
      && classification.visibility !== "hidden"
      && (navigation.includeSecondary || classification.visibility === "primary");
  }), [navigation.includeSecondary, snapshot.nodes]);
  const stageLabel = navigation.stage ? GRAPH_STAGES.find((stage) => stage.id === navigation.stage)?.label : null;
  const activeReaderState = selectedNode?.data.documentId && readerState.status !== "idle" && readerState.nodeId === selectedNode.data.documentId
    ? readerState
    : selectedNode ? { status: "loading" as const } : { status: "idle" as const };

  return (
    <main className="flex h-dvh w-full max-w-full overflow-hidden bg-[#F8FAFC] text-slate-900">
      <aside data-testid="desktop-navigator" className="hidden w-72 shrink-0 border-r border-slate-200 bg-white md:block">
        <GraphNavigator
          documents={navigatorDocuments}
          stage={navigation.stage}
          domain={navigation.domain}
          onStageChange={(stage) => updateNavigation({ stage, domain: null, node: null })}
          onDomainChange={(domain) => updateNavigation({ domain, node: null })}
          onDocumentOpen={openDocument}
        />
      </aside>

      <section className="relative flex min-w-0 flex-1 flex-col">
        <header className="relative z-20 flex min-h-20 shrink-0 flex-wrap items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 lg:px-6">
          <div className="min-w-44 shrink-0">
            <h1 className="text-lg font-bold text-slate-900">
              NEU<span className="font-light text-slate-400">WEAVE</span>
            </h1>
            <p aria-live="polite" className="mt-1 flex items-center gap-2 font-mono text-[10px] text-slate-500">
              <span className={`h-1.5 w-1.5 rounded-full ${statusColor} ${graphStatus !== "error" && streamStatus !== "offline" ? "animate-pulse motion-reduce:animate-none" : ""}`} />
              {statusLabel}
            </p>
          </div>

          <GraphSearch
            nodes={searchNodes}
            disabled={graphStatus !== "ready"}
            centerOnSelect={false}
            className="relative order-last w-full min-w-0 flex-1 sm:order-none sm:min-w-64"
            onNodeFocus={setSearchedNodeId}
            onNodeSelect={(node) => {
              const document = rawDocumentById.get(node.id);
              if (document) {
                openDocument(document);
              }
            }}
          />

          <div className="ml-auto flex max-w-full flex-wrap items-center justify-end gap-2">
            <GraphScopeControl
              value={navigation.scope}
              disabled={graphStatus === "loading"}
              className="relative flex border border-slate-300 bg-white"
              onChange={(scope) => updateNavigation({ scope, stage: null, domain: null, node: null })}
            />
            <GraphViewControl
              value={navigation.view}
              disabled={graphStatus !== "ready"}
              className="relative flex border border-slate-300 bg-white"
              onChange={(view) => updateNavigation({ view })}
            />
            <GraphFilterControl
              includeSecondary={navigation.includeSecondary}
              status={navigation.status}
              category={navigation.category}
              statuses={statuses}
              categories={categories}
              onIncludeSecondaryChange={(includeSecondary) => updateNavigation({ includeSecondary })}
              onStatusChange={(status) => updateNavigation({ status })}
              onCategoryChange={(category) => updateNavigation({ category })}
            />
          </div>

          <nav aria-label="Graph breadcrumb" className="order-last flex w-full items-center gap-1 overflow-x-auto text-xs text-slate-500">
            <button type="button" onClick={() => updateNavigation({ stage: null, domain: null, node: null })} className="min-h-8 shrink-0 px-1 font-medium hover:text-slate-950 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600">
              研发地图
            </button>
            {stageLabel ? <><ChevronRight className="h-3.5 w-3.5 shrink-0" aria-hidden="true" /><button type="button" onClick={() => updateNavigation({ domain: null, node: null })} className="min-h-8 shrink-0 px-1 font-medium hover:text-slate-950 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600">{stageLabel}</button></> : null}
            {navigation.domain ? <><ChevronRight className="h-3.5 w-3.5 shrink-0" aria-hidden="true" /><span className="shrink-0 px-1 font-semibold text-slate-800">{domainLabel(navigation.domain)}</span></> : null}
            {navigation.node ? <><ChevronRight className="h-3.5 w-3.5 shrink-0" aria-hidden="true" /><span className="max-w-64 truncate px-1 text-slate-700">{rawDocumentById.get(navigation.node)?.label}</span></> : null}
          </nav>
        </header>

        <div className="relative min-h-0 flex-1">
          <div className="absolute inset-0 hidden md:block" onKeyDown={onGraphKeyDown}>
            <ReactFlow
              key={`${navigation.scope}:${navigation.view}:${snapshot.version}:${navigation.stage ?? "all"}:${navigation.domain ?? "all"}:${navigation.includeSecondary}:${navigation.status}:${navigation.category}`}
              aria-label="Inkdesk knowledge graph"
              nodes={visibleNodes}
              edges={visibleEdges}
              onNodeClick={onNodeClick}
              onNodeMouseEnter={(_event, node) => setHoveredNodeId(node.id)}
              onNodeMouseLeave={(_event, node) => setHoveredNodeId((current) => current === node.id ? null : current)}
              onPaneClick={() => setSearchedNodeId(null)}
              nodeTypes={nodeTypes}
              nodesConnectable={false}
              nodesDraggable={false}
              fitView
              fitViewOptions={{ nodes: visibleNodes, padding: 0.18 }}
              minZoom={0.2}
              maxZoom={1.6}
              proOptions={{ hideAttribution: true }}
            >
              <Background variant={BackgroundVariant.Dots} gap={24} size={1.25} color="#CBD5E0" />
              <Controls showInteractive={false} className="rounded-none border-none opacity-50 shadow-none hover:opacity-100 [&_.react-flow__controls-button]:rounded-none [&_.react-flow__controls-button]:border-slate-200 [&_.react-flow__controls-button]:shadow-none" />
            </ReactFlow>
            {graphStatus === "ready" && (navigation.view === "relations" || (navigation.view === "flow" && hierarchyGraph.level === "document")) && relationGraph.totalDocumentCount > 30 ? (
              <p className="pointer-events-none absolute bottom-4 right-4 border border-slate-200 bg-white px-3 py-2 font-mono text-[10px] text-slate-500">
                SHOWING 30 OF {relationGraph.totalDocumentCount} / USE NAVIGATOR OR SEARCH
              </p>
            ) : null}
          </div>

          <div data-testid="mobile-navigator" className="absolute inset-0 overflow-y-auto bg-[#F8FAFC] md:hidden">
            <GraphNavigator
              documents={navigatorDocuments}
              stage={navigation.stage}
              domain={navigation.domain}
              onStageChange={(stage) => updateNavigation({ stage, domain: null, node: null })}
              onDomainChange={(domain) => updateNavigation({ domain, node: null })}
              onDocumentOpen={openDocument}
            />
          </div>

          {graphStatus !== "ready" ? (
            <div className="pointer-events-none absolute inset-0 z-10 grid place-items-center px-6 text-center">
              {graphStatus === "loading" ? <p role="status" className="font-mono text-xs text-slate-500">SYNCING KNOWLEDGE GRAPH</p> : null}
              {graphStatus === "empty" ? <div><p className="font-mono text-sm font-semibold text-slate-800">GRAPH SCOPE IS EMPTY</p><p className="mt-2 text-xs text-slate-500">Select another scope or add indexed Markdown.</p></div> : null}
              {graphStatus === "error" ? <div className="pointer-events-auto"><p role="alert" className="font-mono text-sm font-semibold text-slate-800">GRAPH SYNC UNAVAILABLE</p><button type="button" onClick={() => void syncGraph()} className="mt-4 inline-flex h-11 items-center gap-2 border border-slate-300 bg-white px-4 font-mono text-xs font-semibold text-slate-700 hover:border-slate-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600"><RotateCw className="h-4 w-4" aria-hidden="true" strokeWidth={1.5} />RETRY SYNC</button></div> : null}
            </div>
          ) : null}
        </div>
      </section>

      <aside
        aria-hidden={!selectedNode}
        aria-labelledby="graph-reader-title"
        role="dialog"
        className={`fixed inset-y-0 right-0 z-40 flex w-full flex-col border-l border-slate-200 bg-white transition-transform duration-200 ease-out motion-reduce:transition-none sm:w-[30rem] xl:relative xl:inset-auto xl:z-20 xl:shrink-0 xl:transition-[width] ${selectedNode ? "translate-x-0 xl:w-[30rem]" : "translate-x-full xl:w-0 xl:translate-x-0 xl:border-l-0"}`}
      >
        {selectedNode ? (
          <>
            <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
              <div className="min-w-0">
                <p className="font-mono text-[10px] font-semibold uppercase text-emerald-700">
                  {selectedNode.data.stage ?? "knowledge"} / {selectedNode.data.category ?? selectedNode.data.kind} / {selectedNode.data.status}
                </p>
                <h2 id="graph-reader-title" className="mt-1 break-words text-lg font-bold text-slate-900">{selectedNode.data.label}</h2>
              </div>
              <button ref={closeButtonRef} type="button" aria-label="关闭阅读器" onClick={closeReader} className="grid h-11 w-11 shrink-0 place-items-center text-slate-500 hover:bg-slate-100 hover:text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600"><X className="h-5 w-5" aria-hidden="true" strokeWidth={1.5} /></button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
              {activeReaderState.status === "ready" ? <><p className="mb-5 break-all font-mono text-[10px] text-slate-500">{activeReaderState.document.sourcePath}</p><MarkdownViewer content={activeReaderState.document.content} isLoading={false} /></> : null}
              {activeReaderState.status === "loading" ? <MarkdownViewer content="" isLoading /> : null}
              {activeReaderState.status === "error" ? <p role="alert" className="text-sm leading-6 text-slate-600">Vault Markdown 暂不可读。请确认文件仍存在于当前图谱快照中。</p> : null}
            </div>
          </>
        ) : null}
      </aside>

      <style jsx global>{`
        @media (prefers-reduced-motion: reduce) {
          .react-flow__edge.animated path { animation: none; }
        }
      `}</style>
    </main>
  );
}

export default function InkdeskGraphBoard() {
  return <ReactFlowProvider><InkdeskGraphCanvas /></ReactFlowProvider>;
}
