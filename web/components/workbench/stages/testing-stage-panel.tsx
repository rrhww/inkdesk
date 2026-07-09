"use client";

import { useState } from "react";
import { generateTestingChecklist, extractTestingChecklist } from "@/lib/research";
import type { DevRun, DevRunStageStatus } from "@/lib/types";
import { PanelCard } from "@/components/ui/panel-card";

type TestingStagePanelProps = {
  run: DevRun;
  stageStatus: DevRunStageStatus;
  onRunUpdate: (run: DevRun) => void;
};

export function TestingStagePanel({ run, stageStatus, onRunUpdate }: TestingStagePanelProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checkedItems, setCheckedItems] = useState<Set<number>>(new Set());
  const testing = extractTestingChecklist(run);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const updated = await generateTestingChecklist(run.id);
      onRunUpdate(updated);
      setCheckedItems(new Set());
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成测试清单失败");
    } finally {
      setLoading(false);
    }
  };

  const toggleItem = (idx: number) => {
    setCheckedItems((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  if (stageStatus === "pending" || !testing) {
    return (
      <PanelCard className="p-6">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">测试阶段</div>
        <p className="text-sm text-ink-muted mb-4">
          基于编码产出生成测试清单，逐项确认后推进到归档阶段。
        </p>
        {error && (
          <div className="mb-4 rounded-2xl bg-ink-errorSoft px-4 py-3 text-sm text-ink-errorText">{error}</div>
        )}
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="rounded-full bg-ink-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-ink-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? "生成中…" : "生成测试清单"}
        </button>
      </PanelCard>
    );
  }

  const allChecked = testing.checklist.length > 0 && checkedItems.size === testing.checklist.length;

  return (
    <PanelCard className="p-6">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">
        测试清单
        {stageStatus === "completed" && <span className="ml-2 text-green-600">已完成</span>}
      </div>

      {testing.summary && (
        <p className="text-sm text-ink-tertiary mb-4">{testing.summary}</p>
      )}

      <ul className="space-y-2 mb-4">
        {testing.checklist.map((item, i) => (
          <li
            key={i}
            className="flex items-start gap-3 p-3 rounded-2xl bg-ink-low cursor-pointer hover:bg-white transition-colors"
            onClick={() => toggleItem(i)}
          >
            <span className={`material-symbols-outlined text-[20px] mt-0.5 ${checkedItems.has(i) ? "text-green-600" : "text-ink-muted"}`}>
              {checkedItems.has(i) ? "check_box" : "check_box_outline_blank"}
            </span>
            <span className={`text-sm ${checkedItems.has(i) ? "text-ink-muted line-through" : "text-ink-text"}`}>
              {item}
            </span>
          </li>
        ))}
      </ul>

      {stageStatus === "awaiting_review" && (
        <div className="flex items-center gap-3">
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="rounded-full bg-ink-low px-5 py-2.5 text-sm font-medium text-ink-text hover:bg-white disabled:opacity-40"
          >
            {loading ? "生成中…" : "重新生成"}
          </button>
          {allChecked && (
            <span className="text-sm text-green-600 flex items-center gap-1">
              <span className="material-symbols-outlined text-[16px]">check_circle</span>
              全部已确认，可以推进
            </span>
          )}
        </div>
      )}
    </PanelCard>
  );
}
