"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createDevRun, getDevRuns } from "@/lib/research";
import type { DevRunSummary, DevRunType } from "@/lib/types";

const TYPE_LABELS: Record<DevRunType, string> = {
  PRD: "PRD",
  BUG: "Bug",
  REFACTOR: "改造",
};

const STAGE_LABELS: Record<string, string> = {
  context: "上下文",
  solution: "方案",
  review: "审阅",
  coding: "编码",
  testing: "测试",
  deposit: "沉淀",
};

export function DevRunConsole() {
  const router = useRouter();
  const [runs, setRuns] = useState<DevRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [formType, setFormType] = useState<DevRunType>("PRD");
  const [formTitle, setFormTitle] = useState("");
  const [formGoal, setFormGoal] = useState("");
  const [formRepo, setFormRepo] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    try {
      const data = await getDevRuns();
      setRuns(data);
    } catch {
      setError("加载任务列表失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim() || !formGoal.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const run = await createDevRun({
        type: formType,
        title: formTitle.trim(),
        goal: formGoal.trim(),
        repoContext: formRepo.trim() || undefined,
      });
      setRuns((prev) => [
        {
          id: run.id,
          type: run.type,
          title: run.title,
          status: run.status,
          currentStage: run.currentStage,
          stageStatus: run.stageStatus,
          createdAt: run.createdAt,
        },
        ...prev,
      ]);
      setShowCreate(false);
      setFormTitle("");
      setFormGoal("");
      setFormRepo("");
    } catch {
      setError("创建任务失败");
    } finally {
      setSubmitting(false);
    }
  };

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      active: "bg-blue-100 text-blue-800",
      awaiting_review: "bg-yellow-100 text-yellow-800",
      blocked: "bg-red-100 text-red-800",
      completed: "bg-green-100 text-green-800",
      cancelled: "bg-gray-100 text-gray-500",
    };
    const labels: Record<string, string> = {
      active: "进行中",
      awaiting_review: "待确认",
      blocked: "阻塞",
      completed: "完成",
      cancelled: "取消",
    };
    return (
      <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${map[status] ?? "bg-gray-100 text-gray-600"}`}>
        {labels[status] ?? status}
      </span>
    );
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
      )}

      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Dev Run 任务</h2>
          <p className="text-sm text-gray-500 mt-1">从 PRD / Bug / 改造任务出发，每个阶段推进可追踪</p>
        </div>
        <button
          onClick={() => setShowCreate((v) => !v)}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors"
        >
          <span className="material-symbols-outlined text-[18px]">add</span>
          新建任务
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="mb-6 p-4 bg-white border border-gray-200 rounded-xl space-y-4">
          <div className="flex gap-3">
            {(["PRD", "BUG", "REFACTOR"] as DevRunType[]).map((t) => (
              <label key={t} className={`flex items-center gap-1.5 text-sm cursor-pointer px-3 py-1.5 rounded-lg border ${formType === t ? "border-gray-900 bg-gray-50 text-gray-900" : "border-gray-200 text-gray-500"}`}>
                <input
                  type="radio"
                  name="runType"
                  value={t}
                  checked={formType === t}
                  onChange={() => setFormType(t)}
                  className="sr-only"
                />
                {TYPE_LABELS[t]}
              </label>
            ))}
          </div>
          <input
            type="text"
            placeholder="任务标题"
            value={formTitle}
            onChange={(e) => setFormTitle(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10 focus:border-gray-300"
            required
          />
          <textarea
            placeholder="任务目标"
            value={formGoal}
            onChange={(e) => setFormGoal(e.target.value)}
            rows={2}
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10 focus:border-gray-300 resize-none"
            required
          />
          <input
            type="text"
            placeholder="仓库上下文（可选）"
            value={formRepo}
            onChange={(e) => setFormRepo(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10 focus:border-gray-300"
          />
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={submitting || !formTitle.trim() || !formGoal.trim()}
              className="px-4 py-1.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {submitting ? "创建中…" : "创建"}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="text-sm text-gray-400 py-12 text-center">加载中…</div>
      ) : runs.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-4xl mb-3 text-gray-300">
            <span className="material-symbols-outlined text-[48px]">rocket_launch</span>
          </div>
          <p className="text-gray-500 text-sm mb-1">还没有 Dev Run 任务</p>
          <p className="text-gray-400 text-xs">点击「新建任务」创建第一个研发任务</p>
        </div>
      ) : (
        <div className="space-y-3">
          {runs.map((run) => (
            <div
              key={run.id}
              onClick={() => router.push(`/app/runs/${run.id}`)}
              className="block p-4 bg-white border border-gray-200 rounded-xl hover:border-gray-300 hover:shadow-sm transition-all cursor-pointer"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[11px] font-medium text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                      {TYPE_LABELS[run.type]}
                    </span>
                    {statusBadge(run.status)}
                  </div>
                  <h3 className="text-sm font-medium text-gray-900 truncate">{run.title}</h3>
                </div>
                <div className="text-xs text-gray-400 shrink-0 flex items-center gap-1">
                  <span className="material-symbols-outlined text-[14px]">flag</span>
                  {STAGE_LABELS[run.currentStage] ?? run.currentStage}
                </div>
              </div>
              {run.stageStatus === "awaiting_review" && (
                <div className="mt-2 flex items-center gap-1.5 text-xs text-yellow-700 bg-yellow-50 rounded-lg px-2.5 py-1.5">
                  <span className="material-symbols-outlined text-[14px]">rate_review</span>
                  有待确认的输出
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="mt-8 p-4 bg-white border border-gray-200 rounded-xl">
        <h3 className="text-sm font-medium text-gray-700 mb-3">可用能力</h3>
        <div className="grid grid-cols-2 gap-3">
          <a href="/app/ask" className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg text-sm text-gray-700 hover:bg-gray-100 transition-colors">
            <span className="material-symbols-outlined text-[18px] text-gray-400">psychology</span>
            Context Ask
          </a>
          <a href="/app/raw" className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg text-sm text-gray-700 hover:bg-gray-100 transition-colors">
            <span className="material-symbols-outlined text-[18px] text-gray-400">description</span>
            资料导入
          </a>
          <a href="/app/ingest" className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg text-sm text-gray-700 hover:bg-gray-100 transition-colors">
            <span className="material-symbols-outlined text-[18px] text-gray-400">fact_check</span>
            审阅队列
          </a>
          <a href="/app/wiki" className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg text-sm text-gray-700 hover:bg-gray-100 transition-colors">
            <span className="material-symbols-outlined text-[18px] text-gray-400">book</span>
            知识库
          </a>
        </div>
      </div>
    </div>
  );
}
