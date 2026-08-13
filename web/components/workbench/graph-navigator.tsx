"use client";

import { ChevronLeft, FileText, Layers3 } from "lucide-react";

import {
  classificationForNode,
  domainLabel,
  GRAPH_STAGES
} from "@/lib/graph-hierarchy";
import type { GraphSnapshotNode, GraphStage } from "@/lib/server-api";

type GraphNavigatorProps = {
  documents: readonly GraphSnapshotNode[];
  stage: GraphStage | null;
  domain: string | null;
  onStageChange: (stage: GraphStage | null) => void;
  onDomainChange: (domain: string | null) => void;
  onDocumentOpen: (document: GraphSnapshotNode) => void;
  className?: string;
};

export function GraphNavigator({
  documents,
  stage,
  domain,
  onStageChange,
  onDomainChange,
  onDocumentOpen,
  className
}: GraphNavigatorProps) {
  const visibleDocuments = documents.filter((document) => classificationForNode(document).visibility !== "hidden");
  const stageDocuments = stage
    ? visibleDocuments.filter((document) => classificationForNode(document).stage === stage)
    : visibleDocuments;
  const domains = [...new Set(stageDocuments.map((document) => classificationForNode(document).domain))].sort((left, right) =>
    domainLabel(left).localeCompare(domainLabel(right))
  );
  const domainDocuments = domain
    ? stageDocuments.filter((document) => classificationForNode(document).domain === domain)
    : stageDocuments;

  return (
    <nav aria-label="Knowledge hierarchy" className={className ?? "flex h-full flex-col"}>
      <div className="border-b border-slate-200 px-5 py-5">
        <div className="flex items-center gap-2 text-slate-900">
          <Layers3 className="h-4 w-4" aria-hidden="true" strokeWidth={1.5} />
          <h2 className="text-sm font-semibold">研发知识导航</h2>
        </div>
        <p className="mt-1 text-xs leading-5 text-slate-500">按研发阶段与能力领域逐层定位</p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        {stage ? (
          <button
            type="button"
            onClick={() => {
              onDomainChange(null);
              onStageChange(null);
            }}
            className="mb-2 flex min-h-11 w-full items-center gap-2 px-2 text-left text-xs font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-950 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600"
          >
            <ChevronLeft className="h-4 w-4" aria-hidden="true" strokeWidth={1.5} />
            全部研发阶段
          </button>
        ) : null}

        {stage && domain ? (
          <button
            type="button"
            onClick={() => onDomainChange(null)}
            className="mb-2 flex min-h-11 w-full items-center gap-2 px-2 text-left text-xs font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-950 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600"
          >
            <ChevronLeft className="h-4 w-4" aria-hidden="true" strokeWidth={1.5} />
            {GRAPH_STAGES.find((item) => item.id === stage)?.label ?? stage}
          </button>
        ) : null}

        {!stage ? (
          <div className="space-y-1">
            {GRAPH_STAGES.map((item) => {
              const count = visibleDocuments.filter((document) => classificationForNode(document).stage === item.id).length;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onStageChange(item.id)}
                  className="flex min-h-14 w-full items-center justify-between gap-3 border-l-2 border-transparent px-3 py-2 text-left hover:border-emerald-500 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600"
                >
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-slate-800">{item.label}</span>
                    <span className="mt-0.5 block truncate text-[11px] text-slate-500">{item.description}</span>
                  </span>
                  <span className="shrink-0 font-mono text-xs tabular-nums text-slate-500">{count}</span>
                </button>
              );
            })}
          </div>
        ) : null}

        {stage && !domain ? (
          <div className="space-y-1">
            {domains.map((item) => {
              const count = stageDocuments.filter((document) => classificationForNode(document).domain === item).length;
              return (
                <button
                  key={item}
                  type="button"
                  onClick={() => onDomainChange(item)}
                  className="flex min-h-12 w-full items-center justify-between gap-3 border-l-2 border-transparent px-3 py-2 text-left hover:border-emerald-500 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600"
                >
                  <span className="text-sm font-medium text-slate-800">{domainLabel(item)}</span>
                  <span className="font-mono text-xs tabular-nums text-slate-500">{count}</span>
                </button>
              );
            })}
          </div>
        ) : null}

        {stage && domain ? (
          <div className="space-y-1">
            {domainDocuments.map((document) => {
              const classification = classificationForNode(document);
              return (
                <button
                  key={document.id}
                  type="button"
                  onClick={() => onDocumentOpen(document)}
                  className="flex min-h-12 w-full items-start gap-3 px-3 py-2 text-left hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600"
                >
                  <FileText className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" aria-hidden="true" strokeWidth={1.5} />
                  <span className="min-w-0">
                    <span className="block break-words text-sm font-medium leading-5 text-slate-800">{document.label}</span>
                    <span className="mt-0.5 block font-mono text-[10px] uppercase text-slate-500">
                      {classification.category} / {document.status}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        ) : null}
      </div>
    </nav>
  );
}
