"use client";

import type { GraphScope } from "@/lib/server-api";

type GraphScopeControlProps = {
  value: GraphScope;
  onChange: (scope: GraphScope) => void;
  disabled: boolean;
  className?: string;
};

const scopeOptions: Array<{ value: GraphScope; label: string; accessibleLabel: string }> = [
  { value: "all", label: "ALL", accessibleLabel: "All nodes" },
  { value: "vault", label: "VAULT", accessibleLabel: "Vault nodes" },
  { value: "repo", label: "REPO", accessibleLabel: "Repository nodes" }
];

export function GraphScopeControl({ value, onChange, disabled, className }: GraphScopeControlProps) {
  return (
    <div
      role="group"
      aria-label="Graph scope"
      className={className ?? "absolute left-1/2 top-36 z-10 flex -translate-x-1/2 border border-slate-300 bg-white lg:left-auto lg:right-6 lg:top-6 lg:translate-x-0"}
    >
      {scopeOptions.map((option) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            aria-label={option.accessibleLabel}
            aria-pressed={selected}
            disabled={disabled}
            onClick={() => onChange(option.value)}
            className={`h-11 min-w-14 border-r border-slate-300 px-3 font-mono text-[10px] font-semibold tracking-wider transition-colors duration-200 last:border-r-0 focus-visible:z-10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 disabled:cursor-wait disabled:opacity-50 motion-reduce:transition-none ${
              selected ? "bg-slate-900 text-white" : "bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-950"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
