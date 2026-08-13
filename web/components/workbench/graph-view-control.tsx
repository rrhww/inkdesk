"use client";

import { Ellipsis, GitMerge, LayoutTemplate, Network } from "lucide-react";

export type GraphViewMode = "flow" | "relations" | "task" | "raw";

type GraphViewControlProps = {
  value: GraphViewMode;
  onChange: (mode: GraphViewMode) => void;
  disabled: boolean;
  className?: string;
};

const viewOptions: Array<{ value: GraphViewMode; label: string; accessibleLabel: string; icon: typeof LayoutTemplate }> = [
  { value: "flow", label: "FLOW", accessibleLabel: "Research flow", icon: LayoutTemplate },
  { value: "relations", label: "RELATIONS", accessibleLabel: "Local relations", icon: Network },
  { value: "task", label: "TASK", accessibleLabel: "Task focus graph", icon: GitMerge }
];

export function GraphViewControl({ value, onChange, disabled, className }: GraphViewControlProps) {
  return (
    <div
      role="group"
      aria-label="Graph view"
      className={className ?? "absolute left-1/2 top-52 z-10 flex -translate-x-1/2 border border-slate-300 bg-white lg:left-auto lg:right-6 lg:top-20 lg:translate-x-0"}
    >
      {viewOptions.map((option) => {
        const selected = option.value === value;
        const Icon = option.icon;
        return (
          <button
            key={option.value}
            type="button"
            aria-label={option.accessibleLabel}
            aria-pressed={selected}
            disabled={disabled}
            onClick={() => onChange(option.value)}
            title={option.accessibleLabel}
            className={`flex h-10 items-center gap-2 border-r border-slate-300 px-3 font-mono text-[10px] font-semibold tracking-wider transition-colors duration-200 last:border-r-0 focus-visible:z-10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 disabled:cursor-wait disabled:opacity-50 motion-reduce:transition-none ${
              selected ? "bg-slate-900 text-white" : "bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-950"
            }`}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden="true" strokeWidth={1.5} />
            {option.label}
          </button>
        );
      })}
      <details className="relative">
        <summary className="flex h-10 cursor-pointer list-none items-center gap-2 px-3 font-mono text-[10px] font-semibold tracking-wider text-slate-600 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600">
          <Ellipsis className="h-3.5 w-3.5" aria-hidden="true" strokeWidth={1.5} />
          ADVANCED
        </summary>
        <div className="absolute right-0 top-full z-30 mt-1 min-w-40 border border-slate-300 bg-white p-1 shadow-lg">
          <button
            type="button"
            aria-label="Raw graph"
            aria-pressed={value === "raw"}
            disabled={disabled}
            onClick={() => onChange("raw")}
            className={`flex h-10 w-full items-center gap-2 px-3 text-left font-mono text-[10px] font-semibold tracking-wider focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-emerald-600 disabled:opacity-50 ${
              value === "raw" ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-50 hover:text-slate-950"
            }`}
          >
            <Network className="h-3.5 w-3.5" aria-hidden="true" strokeWidth={1.5} />
            RAW GRAPH
          </button>
        </div>
      </details>
    </div>
  );
}
