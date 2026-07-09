"use client";

import { useState } from "react";
import { generateSolution, extractSolutionDraft } from "@/lib/research";
import type { DevRun, DevRunStageStatus } from "@/lib/types";
import { PanelCard } from "@/components/ui/panel-card";

type SolutionStagePanelProps = {
  run: DevRun;
  stageStatus: DevRunStageStatus;
  onRunUpdate: (run: DevRun) => void;
};

export function SolutionStagePanel({ run, stageStatus, onRunUpdate }: SolutionStagePanelProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const draft = extractSolutionDraft(run);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const updated = await generateSolution(run.id);
      onRunUpdate(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成方案失败");
    } finally {
      setLoading(false);
    }
  };

  if (stageStatus === "pending" || !draft) {
    return (
      <PanelCard className="p-6">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">方案阶段</div>
        <p className="text-sm text-ink-muted mb-4">
          基于任务目标和上下文，生成技术方案草案。包括实现路径、关键文件和步骤建议。
        </p>
        {error && (
          <div className="mb-4 rounded-2xl bg-ink-errorSoft px-4 py-3 text-sm text-ink-errorText">{error}</div>
        )}
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="rounded-full bg-ink-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-ink-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? "生成中…" : "生成方案草案"}
        </button>
      </PanelCard>
    );
  }

  return (
    <PanelCard className="p-6">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">
        方案草案
        {stageStatus === "completed" && <span className="ml-2 text-green-600">已完成</span>}
      </div>

      <div className="prose prose-sm max-w-none mb-4">
        <pre className="whitespace-pre-wrap text-sm text-ink-text font-sans bg-ink-low rounded-2xl p-4">
{draft.draft}
        </pre>
      </div>

      {draft.risks.length > 0 && (
        <div className="mt-4">
          <div className="text-xs text-ink-muted mb-2">风险点</div>
          <ul className="space-y-1">
            {draft.risks.map((risk, i) => (
              <li key={i} className="text-sm text-ink-tertiary flex items-start gap-2">
                <span className="material-symbols-outlined text-[16px] text-amber-500 mt-0.5">warning</span>
                <span>{risk}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {stageStatus === "awaiting_review" && (
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="mt-4 rounded-full bg-ink-low px-5 py-2.5 text-sm font-medium text-ink-text hover:bg-white disabled:opacity-40"
        >
          {loading ? "生成中…" : "重新生成"}
        </button>
      )}
    </PanelCard>
  );
}
