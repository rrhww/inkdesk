"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { X } from "lucide-react";
import ReactFlow, {
  applyEdgeChanges,
  applyNodeChanges,
  Background,
  BackgroundVariant,
  Controls,
  type EdgeChange,
  type Node,
  type NodeChange
} from "reactflow";
import "reactflow/dist/style.css";

import { ActionNode, ConceptNode, EntityNode } from "@/components/ui/graph-nodes";
import { type GraphNodeData, initialEdges, initialNodes } from "@/lib/mock/research-fixtures";

type PreviewDocument = {
  sourcePath: string;
  title: string;
  content: string;
};

type ReaderState =
  | { status: "idle" | "loading" }
  | { status: "ready"; document: PreviewDocument }
  | { status: "error" };

export default function InkdeskGraphBoard() {
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node<GraphNodeData> | null>(null);
  const [readerState, setReaderState] = useState<ReaderState>({ status: "idle" });
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const nodeTypes = useMemo(
    () => ({
      concept: ConceptNode,
      entity: EntityNode,
      action: ActionNode
    }),
    []
  );

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

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node<GraphNodeData>) => {
    setReaderState({ status: "loading" });
    setSelectedNode(node);
  }, []);

  useEffect(() => {
    if (!selectedNode) {
      return;
    }

    const controller = new AbortController();

    fetch(`/graph-doc/${encodeURIComponent(selectedNode.data.documentId)}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("Preview document was not found.");
        }

        return (await response.json()) as PreviewDocument;
      })
      .then((document) => setReaderState({ status: "ready", document }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        setReaderState({ status: "error" });
      });

    return () => controller.abort();
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
      <div className="absolute inset-0">
        <ReactFlow
          aria-label="Inkdesk knowledge graph"
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
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

      <div className="pointer-events-none absolute left-8 top-6">
        <h1 className="text-xl font-bold tracking-tight text-slate-900">
          NEU<span className="font-light text-slate-400">WEAVE</span>
        </h1>
        <p className="mt-1 flex items-center gap-2 font-mono text-[10px] tracking-widest text-slate-500">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500 motion-reduce:animate-none" />
          GRAPH SYNC ACTIVE
        </p>
      </div>

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
                  {selectedNode.type} / local markdown
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
              {readerState.status === "loading" ? (
                <div aria-live="polite" className="space-y-4">
                  <p className="font-mono text-xs text-slate-500">READING LOCAL MARKDOWN</p>
                  <div className="h-32 w-full animate-pulse bg-slate-100 motion-reduce:animate-none" />
                  <div className="h-4 w-4/5 animate-pulse bg-slate-100 motion-reduce:animate-none" />
                  <div className="h-4 w-3/5 animate-pulse bg-slate-100 motion-reduce:animate-none" />
                </div>
              ) : null}

              {readerState.status === "ready" ? (
                <div>
                  <p className="mb-5 break-all font-mono text-[10px] tracking-wide text-slate-500">
                    {readerState.document.sourcePath}
                  </p>
                  <pre className="whitespace-pre-wrap break-words font-mono text-xs leading-6 text-slate-700">
                    {readerState.document.content}
                  </pre>
                </div>
              ) : null}

              {readerState.status === "error" ? (
                <p role="alert" className="font-mono text-sm leading-6 text-slate-600">
                  本地 Markdown 预览暂不可用。请确认对应的 vault 文件存在后重试。
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
