"use client";

import { SlidersHorizontal } from "lucide-react";

type GraphFilterControlProps = {
  includeSecondary: boolean;
  status: string;
  category: string;
  statuses: readonly string[];
  categories: readonly string[];
  onIncludeSecondaryChange: (value: boolean) => void;
  onStatusChange: (value: string) => void;
  onCategoryChange: (value: string) => void;
};

export function GraphFilterControl({
  includeSecondary,
  status,
  category,
  statuses,
  categories,
  onIncludeSecondaryChange,
  onStatusChange,
  onCategoryChange
}: GraphFilterControlProps) {
  return (
    <details className="relative">
      <summary className="flex h-11 cursor-pointer list-none items-center gap-2 border border-slate-300 bg-white px-3 font-mono text-[10px] font-semibold tracking-wider text-slate-600 hover:border-slate-500 hover:text-slate-950 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600">
        <SlidersHorizontal className="h-4 w-4" aria-hidden="true" strokeWidth={1.5} />
        FILTERS
      </summary>
      <div className="absolute right-0 top-full z-30 mt-1 w-64 border border-slate-300 bg-white p-4 shadow-lg">
        <label className="flex min-h-11 items-center justify-between gap-3 text-sm text-slate-700">
          <span>显示辅助内容</span>
          <input
            type="checkbox"
            checked={includeSecondary}
            onChange={(event) => onIncludeSecondaryChange(event.target.checked)}
            className="h-4 w-4 accent-emerald-600"
          />
        </label>
        <label className="mt-3 block text-xs font-medium text-slate-600">
          状态
          <select
            aria-label="Filter by status"
            value={status}
            onChange={(event) => onStatusChange(event.target.value)}
            className="mt-1 h-11 w-full border border-slate-300 bg-white px-2 text-sm text-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600"
          >
            <option value="">全部状态</option>
            {statuses.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="mt-3 block text-xs font-medium text-slate-600">
          类型
          <select
            aria-label="Filter by category"
            value={category}
            onChange={(event) => onCategoryChange(event.target.value)}
            className="mt-1 h-11 w-full border border-slate-300 bg-white px-2 text-sm text-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600"
          >
            <option value="">全部类型</option>
            {categories.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
      </div>
    </details>
  );
}
