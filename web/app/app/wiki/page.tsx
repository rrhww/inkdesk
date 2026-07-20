"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { RotateCw, X } from "lucide-react";
import ReactFlow, {
  applyEdgeChanges,
  applyNodeChanges,
  Background,
  BackgroundVariant,
  Controls,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange
} from "reactflow";
import "reactflow/dist/style.css";

import { ActionNode, ConceptNode, EntityNode } from "@/components/ui/graph-nodes";
import { MarkdownViewer } from "@/components/workbench/markdown-viewer";
import { layoutGraphSnapshot, traceUpstreamPath, type GraphNodeData } from "@/lib/graph-layout";
import { ServerAPI, type GraphNodeDocument } from "@/lib/server-api";

type ReaderState =
  | { status: "idle" | "loading" }
  | { status: "ready"; document: GraphNodeDocument }
  | { status: "error" };

type GraphStatus = "loading" | "ready" | "empty" | "error";

const graphStatusLabels: Record<GraphStatus, string> = {
  loading: "GRAPH SYNCING",
  ready: "GRAPH SYNC ACTIVE",
  empty: "GRAPH EMPTY",
  error: "GRAPH SYNC OFFLINE"
};

export default function InkdeskGraphBoard() {
  const [nodes, setNodes] = useState<Node<GraphNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [graphStatus, setGraphStatus] = useState<GraphStatus>("loading");
  const [graphVersion, setGraphVersion] = useState("loading");
  const [selectedNode, setSelectedNode] = useState<Node<GraphNodeData> | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [readerState, setReaderState] = useState<ReaderState>({ status: "idle" });
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const graphRequestRef = useRef(0);

  const nodeTypes = useMemo(
    () => ({
      concept: ConceptNode,
      entity: EntityNode,
      action: ActionNode
    }),
    []
  );

  const focusedNodeId = hoveredNodeId ?? selectedNode?.id ?? null;
  const focusedPath = useMemo(() => traceUpstreamPath(focusedNodeId, edges), [edges, focusedNodeId]);
  const visibleNodes = useMemo(() => {
    if (!focusedNodeId) {
      return nodes;
    }

    return nodes.map((node) => ({
      ...node,
      className: `transition-opacity duration-200 motion-reduce:transition-none ${
        focusedPath.nodeIds.has(node.id) ? "z-10 opacity-100" : "opacity-25"
      }`,
      data: {
        ...node.data,
        isActive: node.id === focusedNodeId
      }
    }));
  }, [focusedNodeId, focusedPath.nodeIds, nodes]);
  const visibleEdges = useMemo(() => {
    if (!focusedNodeId) {
      return edges;
    }

    return edges.map((edge) => {
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
  }, [edges, focusedNodeId, focusedPath.edgeIds]);

  const syncGraph = useCallback(async () => {
    const requestId = graphRequestRef.current + 1;
    graphRequestRef.current = requestId;
    setGraphStatus("loading");

    try {
      const snapshot = await ServerAPI.fetchGraphTopology();
      if (graphRequestRef.current !== requestId) {
        return;
      }
      const layout = layoutGraphSnapshot(snapshot);
      setNodes(layout.nodes);
      setEdges(layout.edges);
      setGraphVersion(snapshot.version);
      setGraphStatus(layout.nodes.length > 0 ? "ready" : "empty");
    } catch {
      if (graphRequestRef.current === requestId) {
        setNodes([]);
        setEdges([]);
        setGraphStatus("error");
      }
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void syncGraph(), 0);
    return () => {
      window.clearTimeout(timer);
      graphRequestRef.current += 1;
    };
  }, [syncGraph]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((currentNodes) => applyNodeChanges(changes, currentNodes)),
    []
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((currentEdges) => applyEdgeChanges(changes, currentEdges)),
    []
  );

  const closeReader = useCallback(() => {
    setSelectedNode(null);
    setReaderState({ status: "idle" });
  }, []);

  const openReader = useCallback((node: Node<GraphNodeData>) => {
    if (!node.data.documentId) {
      return;
    }
    setReaderState({ status: "loading" });
    setSelectedNode(node);
  }, []);

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node<GraphNodeData>) => openReader(node),
    [openReader]
  );

  const onGraphKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (event.key !== "Enter" && event.key !== " ") {
        return;
      }
      const nodeId = (event.target as HTMLElement).closest<HTMLElement>(".react-flow__node")?.dataset.id;
      const node = nodes.find((candidate) => candidate.id === nodeId);
      if (!node?.data.documentId) {
        return;
      }
      event.preventDefault();
      openReader(node);
    },
    [nodes, openReader]
  );

  const onNodeMouseEnter = useCallback((_event: React.MouseEvent, node: Node<GraphNodeData>) => {
    setHoveredNodeId(node.id);
  }, []);

  const onNodeMouseLeave = useCallback((_event: React.MouseEvent, node: Node<GraphNodeData>) => {
    setHoveredNodeId((currentNodeId) => (currentNodeId === node.id ? null : currentNodeId));
  }, []);

  useEffect(() => {
    const documentId = selectedNode?.data.documentId;
    if (!documentId) {
      return;
    }

    let active = true;
    ServerAPI.fetchNodeDocument(documentId)
      .then((document) => {
        if (active) {
          setReaderState({ status: "ready", document });
        }
      })
      .catch(() => {
        if (active) {
          setReaderState({ status: "error" });
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

  return (
    <main className="relative h-dvh w-screen overflow-hidden bg-[#F8FAFC]">
      <div className="absolute inset-0" onKeyDown={onGraphKeyDown}>
        <ReactFlow
          key={graphVersion}
          aria-label="Inkdesk knowledge graph"
          nodes={visibleNodes}
          edges={visibleEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onNodeMouseEnter={onNodeMouseEnter}
          onNodeMouseLeave={onNodeMouseLeave}
          nodeTypes={nodeTypes}
          nodesConnectable={false}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.1}
          maxZoom={1.5}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} gap={24} size={1.5} color="#CBD5E0" />
          <Controls
            showInteractive={false}
            className="rounded-none border-none opacity-40 shadow-none transition-opacity hover:opacity-100 [&_.react-flow__controls-button]:rounded-none [&_.react-flow__controls-button]:border-slate-200 [&_.react-flow__controls-button]:shadow-none"
          />
        </ReactFlow>
      </div>

      <div className="pointer-events-none absolute left-8 top-6 z-10">
        <h1 className="text-xl font-bold tracking-tight text-slate-900">
          NEU<span className="font-light text-slate-400">WEAVE</span>
        </h1>
        <p className="mt-1 flex items-center gap-2 font-mono text-[10px] tracking-widest text-slate-500">
          <span
            className={`h-1.5 w-1.5 rounded-full motion-reduce:animate-none ${
              graphStatus === "ready"
                ? "animate-pulse bg-emerald-500"
                : graphStatus === "error"
                  ? "bg-rose-500"
                  : "bg-slate-400"
            }`}
          />
          {graphStatusLabels[graphStatus]}
        </p>
      </div>

      {graphStatus !== "ready" ? (
        <div className="pointer-events-none absolute inset-0 z-10 grid place-items-center px-6 text-center">
          {graphStatus === "loading" ? (
            <p role="status" className="font-mono text-xs tracking-widest text-slate-500">
              SYNCING LOCAL VAULT
            </p>
          ) : null}
          {graphStatus === "empty" ? (
            <div>
              <p className="font-mono text-sm font-semibold text-slate-800">VAULT GRAPH IS EMPTY</p>
              <p className="mt-2 font-mono text-xs text-slate-500">Add Markdown links under vault/wiki and sync again.</p>
            </div>
          ) : null}
          {graphStatus === "error" ? (
            <div className="pointer-events-auto">
              <p role="alert" className="font-mono text-sm font-semibold text-slate-800">VAULT SYNC UNAVAILABLE</p>
              <button
                type="button"
                onClick={() => void syncGraph()}
                className="mt-4 inline-flex h-11 items-center gap-2 border border-slate-300 bg-white px-4 font-mono text-xs font-semibold text-slate-700 transition-colors hover:border-slate-500 hover:text-slate-950 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600"
              >
                <RotateCw className="h-4 w-4" aria-hidden="true" strokeWidth={1.5} />
                RETRY SYNC
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

      <aside
        aria-hidden={!selectedNode}
        aria-labelledby="graph-reader-title"
        role="dialog"
        className={`absolute inset-y-0 right-0 z-20 flex w-full max-w-[30rem] flex-col border-l border-slate-200 bg-white/90 backdrop-blur-sm transition-transform duration-200 ease-out motion-reduce:transition-none sm:w-[30rem] ${
          selectedNode ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {selectedNode ? (
          <>
            <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
              <div className="min-w-0">
                <p className="font-mono text-[10px] font-semibold uppercase tracking-widest text-emerald-700">
                  {selectedNode.data.kind} / {selectedNode.data.status}
                </p>
                <h2 id="graph-reader-title" className="mt-1 break-words text-lg font-bold text-slate-900">
                  {selectedNode.data.label}
                </h2>
              </div>
              <button
                ref={closeButtonRef}
                type="button"
                aria-label="关闭阅读器"
                onClick={closeReader}
                className="grid h-11 w-11 shrink-0 place-items-center text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600"
              >
                <X className="h-5 w-5" aria-hidden="true" strokeWidth={1.5} />
              </button>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
              {readerState.status === "ready" ? (
                <>
                  <p className="mb-5 break-all font-mono text-[10px] tracking-wide text-slate-500">
                    {readerState.document.sourcePath}
                  </p>
                  <MarkdownViewer content={readerState.document.content} isLoading={false} />
                </>
              ) : null}

              {readerState.status === "loading" ? <MarkdownViewer content="" isLoading /> : null}

              {readerState.status === "error" ? (
                <p role="alert" className="font-mono text-sm leading-6 text-slate-600">
                  Vault Markdown 暂不可读。请确认文件仍存在于当前图谱快照中。
                </p>
              ) : null}
            </div>
          </>
        ) : null}
      </aside>

      <style jsx global>{`
        @media (prefers-reduced-motion: reduce) {
          .react-flow__edge.animated path {
            animation: none;
          }
        }
      `}</style>
    </main>
  );
}
