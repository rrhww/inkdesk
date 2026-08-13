import type { ComponentType } from "react";
import {
  AlertTriangle,
  Blocks,
  BookOpen,
  ClipboardList,
  Database,
  DraftingCompass,
  FileText,
  PackageCheck,
  ShieldCheck
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { Handle, Position, type NodeProps } from "reactflow";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

type ConceptNodeData = {
  label: string;
  isActive?: boolean;
  kind?: string;
  status?: string;
  category?: string;
  module?: string;
};

type EntityNodeData = {
  label: string;
  module?: string;
  isActive?: boolean;
  kind?: string;
  status?: string;
  category?: string;
};

type ActionNodeData = {
  label: string;
  isActive?: boolean;
  kind?: string;
  status?: string;
  category?: string;
  module?: string;
};

type ModuleGroupNodeData = {
  label: string;
};

type HierarchyNodeData = {
  label: string;
  summary?: string;
  role?: "stage" | "domain" | "health";
  stage?: string;
  primaryCount?: number;
  secondaryCount?: number;
  issueCount?: number;
  totalCount?: number;
  isActive?: boolean;
};

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

type DocumentNodeData = ConceptNodeData & EntityNodeData & ActionNodeData;

function DocumentNode({ data }: NodeProps<DocumentNodeData>) {
  return (
    <div
      data-state={data.isActive ? "active" : "idle"}
      className={cn(
        "group relative w-[244px] border bg-white transition-[border-color,box-shadow] duration-200 motion-reduce:transition-none",
        data.isActive
          ? "border-emerald-600 shadow-[0_0_0_3px_rgba(16,185,129,0.16)]"
          : "border-slate-300 hover:border-slate-500"
      )}
    >
      <GraphHandles />
      {data.isActive ? (
        <span aria-hidden="true" className="absolute right-2 top-2 h-1.5 w-1.5 bg-emerald-500 motion-safe:animate-pulse" />
      ) : null}
      <div className="flex min-h-[76px] items-start gap-3 px-3 py-3">
        <FileText className={cn("mt-0.5 h-4 w-4 shrink-0", data.isActive ? "text-emerald-700" : "text-slate-500")} aria-hidden="true" strokeWidth={1.5} />
        <div className="min-w-0">
          <p className="break-words text-sm font-semibold leading-5 text-slate-900">{data.label}</p>
          <p className="mt-1 font-mono text-[9px] uppercase text-slate-500">
            {data.category || data.kind || "document"} / {data.status || "indexed"}
          </p>
          {data.module ? <p className="mt-1 truncate text-[10px] text-slate-500">{data.module}</p> : null}
        </div>
      </div>
    </div>
  );
}

export const ConceptNode: ComponentType<NodeProps<ConceptNodeData>> = DocumentNode;
export const EntityNode: ComponentType<NodeProps<EntityNodeData>> = DocumentNode;
export const ActionNode: ComponentType<NodeProps<ActionNodeData>> = DocumentNode;

const STAGE_ICONS = {
  requirements: ClipboardList,
  design: DraftingCompass,
  implementation: Blocks,
  verification: ShieldCheck,
  delivery: PackageCheck,
  knowledge: BookOpen
} as const;

export const HierarchyNode: ComponentType<NodeProps<HierarchyNodeData>> = ({ data }) => {
  const StageIcon = data.stage && data.stage in STAGE_ICONS
    ? STAGE_ICONS[data.stage as keyof typeof STAGE_ICONS]
    : data.role === "health"
      ? AlertTriangle
      : Database;
  const isHealth = data.role === "health";
  return (
    <div
      data-state={data.isActive ? "active" : "idle"}
      className={cn(
        "group relative w-[248px] border bg-white transition-[border-color,box-shadow,background-color] duration-200 motion-reduce:transition-none",
        data.role === "stage" ? "min-h-[112px]" : "min-h-[88px]",
        isHealth ? "border-rose-300 bg-rose-50" : "border-slate-300",
        data.isActive
          ? "border-emerald-600 shadow-[0_0_0_3px_rgba(16,185,129,0.16)]"
          : isHealth ? "hover:border-rose-500" : "hover:border-slate-500 hover:bg-slate-50"
      )}
    >
      <GraphHandles />
      <div className="px-4 py-3">
        <div className="flex items-start gap-3">
          <StageIcon className={cn("mt-0.5 h-4 w-4 shrink-0", isHealth ? "text-rose-700" : "text-slate-700")} aria-hidden="true" strokeWidth={1.5} />
          <div className="min-w-0">
            <p className="break-words text-sm font-semibold leading-5 text-slate-900">{data.label}</p>
            {data.summary ? <p className="mt-1 text-[11px] leading-4 text-slate-500">{data.summary}</p> : null}
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 border-t border-slate-200 pt-2 font-mono text-[9px] uppercase text-slate-500">
          {typeof data.primaryCount === "number" ? <span>CORE {data.primaryCount}</span> : null}
          {typeof data.secondaryCount === "number" ? <span>MORE {data.secondaryCount}</span> : null}
          {typeof data.totalCount === "number" && data.role !== "stage" ? <span>TOTAL {data.totalCount}</span> : null}
          {data.issueCount ? <span className="text-rose-700">ISSUES {data.issueCount}</span> : null}
        </div>
      </div>
    </div>
  );
};

export const ModuleGroupNode: ComponentType<NodeProps<ModuleGroupNodeData>> = ({ data }) => {
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
