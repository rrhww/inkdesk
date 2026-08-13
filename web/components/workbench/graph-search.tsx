"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Search } from "lucide-react";
import type { Node } from "reactflow";
import { useReactFlow } from "reactflow";

import { findGraphNodes } from "@/lib/graph-search";
import { graphNodeDimensions, type GraphNodeData } from "@/lib/graph-layout";

type GraphSearchProps = {
  nodes: readonly Node<GraphNodeData>[];
  onNodeFocus: (nodeId: string) => void;
  onNodeSelect?: (node: Node<GraphNodeData>) => void;
  centerOnSelect?: boolean;
  disabled?: boolean;
  className?: string;
};

export function GraphSearch({
  nodes,
  onNodeFocus,
  onNodeSelect,
  centerOnSelect = true,
  disabled = false,
  className
}: GraphSearchProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const { setCenter } = useReactFlow();
  const results = useMemo(() => findGraphNodes(nodes, searchTerm), [nodes, searchTerm]);
  const hasQuery = searchTerm.trim().length > 0;

  const focusNode = useCallback(
    (node: Node<GraphNodeData>) => {
      if (centerOnSelect) {
        const dimensions = graphNodeDimensions(node.type);
        const width = node.width ?? dimensions.width;
        const height = node.height ?? dimensions.height;
        const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
        setCenter(node.position.x + width / 2, node.position.y + height / 2, {
          zoom: 1.2,
          duration: reduceMotion ? 0 : 240
        });
      }
      onNodeSelect?.(node);
      onNodeFocus(node.id);
      setSearchTerm("");
      setActiveIndex(-1);
    },
    [centerOnSelect, onNodeFocus, onNodeSelect, setCenter]
  );

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if (disabled || event.key.toLocaleLowerCase() !== "k" || (!event.metaKey && !event.ctrlKey) || event.altKey) {
        return;
      }
      event.preventDefault();
      inputRef.current?.focus();
      inputRef.current?.select();
    };
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, [disabled]);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      setSearchTerm("");
      setActiveIndex(-1);
      inputRef.current?.blur();
      return;
    }
    if (!results.length) {
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((current) => (current + 1) % results.length);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) => (current <= 0 ? results.length - 1 : current - 1));
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      focusNode(results[activeIndex >= 0 ? activeIndex : 0]);
    }
  };

  return (
    <div className={className ?? "absolute left-1/2 top-20 z-10 w-[min(22rem,calc(100vw-2rem))] -translate-x-1/2 sm:top-6"}>
      <label htmlFor="graph-search" className="sr-only">
        Search graph nodes
      </label>
      <div className="relative">
        <Search
          aria-hidden="true"
          strokeWidth={1.5}
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500"
        />
        <input
          ref={inputRef}
          id="graph-search"
          type="search"
          role="combobox"
          aria-label="Search graph nodes"
          aria-keyshortcuts="Control+K Meta+K"
          aria-autocomplete="list"
          aria-expanded={hasQuery}
          aria-controls="graph-search-results"
          aria-activedescendant={activeIndex >= 0 ? `graph-search-option-${activeIndex}` : undefined}
          autoComplete="off"
          disabled={disabled}
          placeholder="Search graph"
          value={searchTerm}
          onChange={(event) => {
            setSearchTerm(event.target.value);
            setActiveIndex(-1);
          }}
          onKeyDown={handleKeyDown}
          className="h-11 w-full rounded-none border border-slate-300 bg-white pl-10 pr-3 font-mono text-base text-slate-800 outline-none transition-colors duration-200 placeholder:text-slate-500 hover:border-slate-500 focus:border-emerald-600 focus-visible:ring-2 focus-visible:ring-emerald-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400 motion-reduce:transition-none sm:text-sm"
        />
      </div>

      {hasQuery ? (
        <div id="graph-search-results" role="listbox" className="mt-1 border border-slate-300 bg-white">
          {results.length ? (
            results.map((node, index) => (
              <button
                key={node.id}
                id={`graph-search-option-${index}`}
                type="button"
                role="option"
                aria-selected={index === activeIndex}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => focusNode(node)}
                className={`flex min-h-11 w-full items-center justify-between gap-4 border-b border-slate-100 px-3 py-2 text-left last:border-b-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-emerald-600 ${
                  index === activeIndex ? "bg-emerald-50" : "bg-white hover:bg-slate-50"
                }`}
              >
                <span className="min-w-0 truncate font-mono text-xs font-semibold text-slate-800">{node.data.label}</span>
                <span className="shrink-0 text-right font-mono text-[10px] uppercase text-slate-500">
                  {node.data.stage && node.data.domain ? `${node.data.stage} / ${node.data.domain}` : node.data.kind}
                </span>
              </button>
            ))
          ) : (
            <p role="status" className="m-0 px-3 py-4 text-center font-mono text-xs tracking-widest text-slate-500">
              NO MATCHING NODES
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}
