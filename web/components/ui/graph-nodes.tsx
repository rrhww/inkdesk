import type { ComponentType } from "react";
import { Database, FileText, Zap } from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

type ConceptNodeData = {
  label: string;
  isActive?: boolean;
};

type EntityNodeData = {
  label: string;
  module?: string;
  isActive?: boolean;
};

type ActionNodeData = {
  label: string;
  isActive?: boolean;
};

type ModuleGroupNodeData = {
  label: string;
};

type ConceptNodeType = Node<ConceptNodeData, "concept">;
type EntityNodeType = Node<EntityNodeData, "entity">;
type ActionNodeType = Node<ActionNodeData, "action">;
type ModuleGroupNodeType = Node<ModuleGroupNodeData, "module">;

const HANDLE_OFFSETS = ["16.667%", "33.333%", "50%", "66.667%", "83.333%"] as const;

function GraphHandles() {
  return (
    <>
      {HANDLE_OFFSETS.map((left, index) => (
        <Handle
          key={`target-${index}`}
          id={`target-${index}`}
          type="target"
          position={Position.Top}
          style={{
            left,
            width: 1,
            height: 1,
            minWidth: 0,
            minHeight: 0,
            border: 0,
            background: "transparent",
            opacity: 0,
            pointerEvents: "none"
          }}
        />
      ))}
      {HANDLE_OFFSETS.map((left, index) => (
        <Handle
          key={`source-${index}`}
          id={`source-${index}`}
          type="source"
          position={Position.Bottom}
          style={{
            left,
            width: 1,
            height: 1,
            minWidth: 0,
            minHeight: 0,
            border: 0,
            background: "transparent",
            opacity: 0,
            pointerEvents: "none"
          }}
        />
      ))}
    </>
  );
}

export const ConceptNode: ComponentType<NodeProps<ConceptNodeType>> = ({ data }) => {
  return (
    <div
      data-state={data.isActive ? "active" : "idle"}
      className={cn(
        "group relative flex h-24 w-24 items-center justify-center rounded-full border-2 bg-slate-900 transition-[background-color,border-color,outline-color] duration-200 motion-reduce:transition-none",
        data.isActive
          ? "border-emerald-400 outline outline-2 outline-offset-4 outline-emerald-200"
          : "border-slate-900 hover:bg-slate-800"
      )}
    >
      <GraphHandles />
      {data.isActive ? (
        <span aria-hidden="true" className="absolute right-3 top-3 h-1.5 w-1.5 bg-emerald-400 motion-safe:animate-pulse" />
      ) : null}
      <div className="flex flex-col items-center justify-center px-2 text-center">
        <Database
          className={cn("mb-1 h-4 w-4", data.isActive ? "text-emerald-300" : "text-slate-300")}
          strokeWidth={1.5}
          aria-hidden="true"
        />
        <span className="text-[10px] font-medium uppercase tracking-wider text-white">{data.label}</span>
      </div>
    </div>
  );
};

export const EntityNode: ComponentType<NodeProps<EntityNodeType>> = ({ data }) => {
  return (
    <div
      data-state={data.isActive ? "active" : "idle"}
      className={cn(
        "group relative min-w-[140px] rounded-none border-2 bg-white transition-[border-color,outline-color] duration-200 motion-reduce:transition-none",
        data.isActive
          ? "border-emerald-500 outline outline-1 outline-offset-2 outline-emerald-200"
          : "border-slate-300 hover:border-slate-500"
      )}
    >
      <GraphHandles />
      {data.isActive ? (
        <span aria-hidden="true" className="absolute right-2 top-2 h-1.5 w-1.5 bg-emerald-500 motion-safe:animate-pulse" />
      ) : null}
      <div className={cn("border-b px-3 py-2", data.isActive ? "border-emerald-200 bg-emerald-50" : "border-slate-100 bg-slate-50")}>
        <span className="font-mono text-[9px] uppercase text-slate-500">{data.module || "UNKNOWN MODULE"}</span>
      </div>
      <div className="flex items-center gap-2 px-3 py-3">
        <FileText
          className={cn("h-4 w-4", data.isActive ? "text-emerald-700" : "text-slate-700")}
          strokeWidth={1.5}
          aria-hidden="true"
        />
        <span className="font-mono text-xs font-semibold tracking-tight text-slate-800">{data.label}</span>
      </div>
    </div>
  );
};

export const ActionNode: ComponentType<NodeProps<ActionNodeType>> = ({ data }) => {
  return (
    <div
      data-state={data.isActive ? "active" : "idle"}
      className={cn(
        "group relative w-[280px] rounded-none border-2 bg-emerald-50 transition-[background-color,border-color,outline-color] duration-200 motion-reduce:transition-none",
        data.isActive
          ? "border-solid border-emerald-600 bg-emerald-100 outline outline-1 outline-offset-2 outline-emerald-200"
          : "border-dashed border-emerald-500 hover:bg-emerald-100"
      )}
    >
      <GraphHandles />
      {data.isActive ? (
        <span aria-hidden="true" className="absolute right-2 top-2 h-1.5 w-1.5 bg-emerald-600 motion-safe:animate-pulse" />
      ) : null}
      <div className="flex items-center gap-2 px-4 py-3">
        <Zap
          className={cn(
            "h-4 w-4 fill-emerald-100",
            data.isActive ? "text-emerald-700" : "text-emerald-600"
          )}
          strokeWidth={1.5}
          aria-hidden="true"
        />
        <span className="text-xs font-bold tracking-wide text-emerald-800">{data.label}</span>
      </div>
    </div>
  );
};

export const ModuleGroupNode: ComponentType<NodeProps<ModuleGroupNodeType>> = ({ data }) => {
  return (
    <div className="relative h-full w-full border-2 border-dashed border-slate-300 bg-slate-100/40">
      <div className="absolute -top-3 left-4 bg-[#F8FAFC] px-2">
        <span className="flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-widest text-slate-500">
          <Database className="h-3 w-3" aria-hidden="true" strokeWidth={1.5} />
          {data.label}
        </span>
      </div>
    </div>
  );
};
