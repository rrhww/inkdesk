import type { ComponentType } from "react";
import { Database, FileText, Zap } from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { Handle, Position, type NodeProps } from "reactflow";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

type ConceptNodeData = {
  label: string;
};

type EntityNodeData = {
  label: string;
  module?: string;
};

type ActionNodeData = {
  label: string;
};

export const ConceptNode: ComponentType<NodeProps<ConceptNodeData>> = ({ data }) => {
  return (
    <div className="group relative flex h-24 w-24 items-center justify-center rounded-full border-2 border-slate-900 bg-slate-900 transition-colors hover:bg-slate-800">
      <Handle type="target" position={Position.Top} className="opacity-0 group-hover:opacity-100" />
      <div className="flex flex-col items-center justify-center px-2 text-center">
        <Database className="mb-1 h-4 w-4 text-slate-300" strokeWidth={1.5} aria-hidden="true" />
        <span className="text-[10px] font-medium uppercase tracking-wider text-white">{data.label}</span>
      </div>
      <Handle
        id="source-left"
        type="source"
        position={Position.Bottom}
        style={{ left: "34%" }}
        className="opacity-0 group-hover:opacity-100"
      />
      <Handle
        id="source-right"
        type="source"
        position={Position.Bottom}
        style={{ left: "66%" }}
        className="opacity-0 group-hover:opacity-100"
      />
    </div>
  );
};

export const EntityNode: ComponentType<NodeProps<EntityNodeData>> = ({ data }) => {
  return (
    <div className="group relative min-w-[140px] rounded-none border-2 border-slate-300 bg-white transition-colors hover:border-slate-500">
      <Handle
        id="target-left"
        type="target"
        position={Position.Top}
        style={{ left: "25%" }}
        className="bg-slate-400 opacity-0 group-hover:opacity-100"
      />
      <Handle
        id="target-center"
        type="target"
        position={Position.Top}
        className="bg-slate-400 opacity-0 group-hover:opacity-100"
      />
      <Handle
        id="target-right"
        type="target"
        position={Position.Top}
        style={{ left: "75%" }}
        className="bg-slate-400 opacity-0 group-hover:opacity-100"
      />
      <div className="border-b border-slate-100 bg-slate-50 px-3 py-2">
        <span className="font-mono text-[9px] uppercase text-slate-500">{data.module || "UNKNOWN MODULE"}</span>
      </div>
      <div className="flex items-center gap-2 px-3 py-3">
        <FileText className="h-4 w-4 text-slate-700" strokeWidth={1.5} aria-hidden="true" />
        <span className="font-mono text-xs font-semibold tracking-tight text-slate-800">{data.label}</span>
      </div>
      <Handle
        id="source"
        type="source"
        position={Position.Bottom}
        className="bg-slate-400 opacity-0 group-hover:opacity-100"
      />
    </div>
  );
};

export const ActionNode: ComponentType<NodeProps<ActionNodeData>> = ({ data }) => {
  return (
    <div className="group relative w-[280px] rounded-none border-2 border-dashed border-emerald-500 bg-emerald-50">
      <Handle
        id="target-left"
        type="target"
        position={Position.Top}
        style={{ left: "30%" }}
        className="bg-emerald-500 opacity-0 group-hover:opacity-100"
      />
      <Handle
        id="target-right"
        type="target"
        position={Position.Top}
        style={{ left: "70%" }}
        className="bg-emerald-500 opacity-0 group-hover:opacity-100"
      />
      <div className="flex items-center gap-2 px-4 py-3">
        <Zap className="h-4 w-4 fill-emerald-100 text-emerald-600" strokeWidth={1.5} aria-hidden="true" />
        <span className="text-xs font-bold tracking-wide text-emerald-800">{data.label}</span>
      </div>
      <Handle
        id="source"
        type="source"
        position={Position.Bottom}
        className="bg-emerald-500 opacity-0 group-hover:opacity-100"
      />
    </div>
  );
};
