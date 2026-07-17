"use client";

import { useCallback, useMemo, useState } from "react";
import ReactFlow, {
  applyEdgeChanges,
  applyNodeChanges,
  Background,
  BackgroundVariant,
  Controls,
  type EdgeChange,
  type NodeChange
} from "reactflow";
import "reactflow/dist/style.css";

import { ActionNode, ConceptNode, EntityNode } from "@/components/ui/graph-nodes";
import { initialEdges, initialNodes } from "@/lib/mock/research-fixtures";

export default function InkdeskGraphBoard() {
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);

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

  return (
    <main className="relative h-dvh w-screen overflow-hidden bg-[#F8FAFC]">
      <ReactFlow
        aria-label="Inkdesk knowledge graph"
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
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

      <div className="pointer-events-none absolute left-8 top-6">
        <h1 className="text-xl font-bold tracking-tight text-slate-900">
          NEU<span className="font-light text-slate-400">WEAVE</span>
        </h1>
        <p className="mt-1 flex items-center gap-2 font-mono text-[10px] tracking-widest text-slate-500">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500 motion-reduce:animate-none" />
          GRAPH SYNC ACTIVE
        </p>
      </div>

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
