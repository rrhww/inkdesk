"use client";

import { useState } from "react";
import { generateContextPack, extractContextPackSummary } from "@/lib/research";
import type { DevRun, DevRunStageStatus } from "@/lib/types";
import { PanelCard } from "@/components/ui/panel-card";

type ContextStagePanelProps = {
  run: DevRun;
  stageStatus: DevRunStageStatus;
  onRunUpdate: (run: DevRun) => void;
};

export function ContextStagePanel({ run, stageStatus, onRunUpdate }: ContextStagePanelProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const summary = extractContextPackSummary(run);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const updated = await generateContextPack(run.id);
      onRunUpdate(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成上下文失败");
    } finally {
      setLoading(false);
    }
  };

  if (stageStatus === "pending") {
    return (
      <PanelCard className="p-6">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">上下文阶段</div>
        <p className="text-sm text-ink-muted mb-4">
          点击下方按钮，系统将为当前任务生成上下文包，包括关联的 wiki 页面、历史 Ask 记录和待审阅项。
        </p>
        {error && (
          <div className="mb-4 rounded-2xl bg-ink-errorSoft px-4 py-3 text-sm text-ink-errorText">{error}</div>
        )}
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="rounded-full bg-ink-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-ink-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? "生成中…" : "生成上下文包"}
        </button>
      </PanelCard>
    );
  }

  if (summary) {
    return (
      <PanelCard className="p-6">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">
          上下文摘要
          {stageStatus === "completed" && <span className="ml-2 text-green-600">已完成</span>}
        </div>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center">
            <div className="text-2xl font-headline font-extrabold text-ink-text">{summary.askHistoryCount}</div>
            <div className="mt-1 text-xs text-ink-muted">Ask 历史</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-headline font-extrabold text-ink-text">{summary.pendingReviewCount}</div>
            <div className="mt-1 text-xs text-ink-muted">待审阅项</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-headline font-extrabold text-ink-text">{summary.wikiPageCount}</div>
            <div className="mt-1 text-xs text-ink-muted">Wiki 关联</div>
          </div>
        </div>
        {summary.pendingReviewCount === 0 && summary.askHistoryCount === 0 && (
          <div className="rounded-2xl bg-[#fff4ec] px-4 py-3 text-sm text-ink-tertiary">
            上下文不足。建议先在 <a href="/app/ask" className="underline">Context Ask</a> 中提问，或导入 raw 材料。
          </div>
        )}
      </PanelCard>
    );
  }

  return (
    <PanelCard className="p-6">
      <p className="text-sm text-ink-muted">暂无上下文数据</p>
    </PanelCard>
  );
}
