"use client";

import { useState } from "react";
import { depositRun, extractDepositInfo } from "@/lib/research";
import type { DevRun, DevRunStageStatus } from "@/lib/types";
import { PanelCard } from "@/components/ui/panel-card";

type DepositStagePanelProps = {
  run: DevRun;
  stageStatus: DevRunStageStatus;
  onRunUpdate: (run: DevRun) => void;
};

export function DepositStagePanel({ run, stageStatus, onRunUpdate }: DepositStagePanelProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const depositInfo = extractDepositInfo(run);

  const handleDeposit = async () => {
    setLoading(true);
    setError(null);
    try {
      const updated = await depositRun(run.id);
      onRunUpdate(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "沉淀失败");
    } finally {
      setLoading(false);
    }
  };

  if (stageStatus === "pending" || !depositInfo) {
    return (
      <PanelCard className="p-6">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">沉淀阶段</div>
        <p className="text-sm text-ink-muted mb-4">
          将本次 Dev Run 的关键产出沉淀为知识提案，进入 ingest 审阅队列。审阅通过后将成为正式 wiki 页面。
        </p>
        {error && (
          <div className="mb-4 rounded-2xl bg-ink-errorSoft px-4 py-3 text-sm text-ink-errorText">{error}</div>
        )}
        <button
          onClick={handleDeposit}
          disabled={loading}
          className="rounded-full bg-ink-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-ink-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? "沉淀中…" : "沉淀产出"}
        </button>
      </PanelCard>
    );
  }

  return (
    <PanelCard className="p-6">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">
        沉淀结果
        {stageStatus === "completed" && <span className="ml-2 text-green-600">已完成</span>}
      </div>
      <div className="flex items-center gap-3 mb-4">
        <span className="material-symbols-outlined text-[20px] text-green-600">check_circle</span>
        <span className="text-sm text-ink-text">
          {depositInfo.isNew ? "已创建新提案" : "提案已存在（去重）"}
        </span>
      </div>
      <div className="rounded-2xl bg-ink-low px-4 py-3 text-sm text-ink-muted mb-4">
        <span className="text-ink-muted">提案 ID：</span>
        <code className="text-ink-text">{depositInfo.reviewId}</code>
      </div>
      <a
        href="/app/ingest"
        className="inline-block rounded-full bg-ink-low px-5 py-2.5 text-sm font-medium text-ink-text hover:bg-white"
      >
        前往 Ingest 队列审阅
      </a>
    </PanelCard>
  );
}
