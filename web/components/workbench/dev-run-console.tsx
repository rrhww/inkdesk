"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createDevRun, getDevRuns, getVaultHealth } from "@/lib/research";
import type { DevRunSummary, DevRunType, HealthResponse } from "@/lib/types";

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

function HealthDigest({ health }: { health: HealthResponse }) {
  const { summary } = health;
  const totalIssues = summary.brokenLinkCount + summary.orphanPageCount + summary.missingFrontmatterCount + summary.missingSourceCount;
  const hasIssues = totalIssues > 0;

  return (
    <Link
      href="/app/health"
      className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition ${
        hasIssues
          ? "bg-[#fff4ec] text-ink-tertiary hover:bg-[#ffe8d6]"
          : "bg-green-50 text-green-700 hover:bg-green-100"
      }`}
    >
      <span className="material-symbols-outlined text-[16px]">
        {hasIssues ? "warning" : "verified"}
      </span>
      {hasIssues ? `${totalIssues} 个结构问题` : "知识库结构健康"}
    </Link>
  );
}

export function DevRunConsole() {
  const router = useRouter();
  const [runs, setRuns] = useState<DevRunSummary[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
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
      const [data, healthData] = await Promise.all([
        getDevRuns(),
        getVaultHealth().catch(() => null),
      ]);
      setRuns(data);
      setHealth(healthData);
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
      active: "bg-ink-primarySoft text-ink-primary",
      awaiting_review: "bg-[#fff4ec] text-ink-tertiary",
      blocked: "bg-ink-errorSoft text-ink-errorText",
      completed: "bg-ink-primarySoft text-ink-primary",
      cancelled: "bg-ink-low text-ink-muted",
    };
    const labels: Record<string, string> = {
      active: "进行中",
      awaiting_review: "待确认",
      blocked: "阻塞",
      completed: "完成",
      cancelled: "取消",
    };
    return (
      <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${map[status] ?? "bg-ink-low text-ink-muted"}`}>
        {labels[status] ?? status}
      </span>
    );
  };

  const typeBadge = (type: DevRunType) => {
    const map: Record<DevRunType, string> = {
      PRD: "bg-ink-primarySoft text-ink-primary",
      BUG: "bg-ink-errorSoft text-ink-errorText",
      REFACTOR: "bg-ink-low text-ink-text",
    };
    return (
      <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${map[type]}`}>
        {TYPE_LABELS[type]}
      </span>
    );
  };

  return (
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      {error && (
        <div className="mb-6 rounded-xl bg-ink-errorSoft px-4 py-3 text-sm text-ink-errorText">{error}</div>
      )}

      <div className="flex items-start justify-between gap-6 mb-8">
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">任务</div>
          <h2 className="mt-3 font-headline text-4xl font-extrabold tracking-tight text-ink-text">Dev Run 任务</h2>
        </div>
        <div className="flex items-center gap-3">
          {health && (
            <HealthDigest health={health} />
          )}
          <button
            onClick={() => setShowCreate((v) => !v)}
            className="shrink-0 inline-flex items-center gap-1.5 rounded-full bg-ink-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-ink-primary/90"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            新建任务
          </button>
        </div>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="paper-card p-6 mb-8 space-y-4">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">任务类型</div>
          <div className="flex gap-3">
            {(["PRD", "BUG", "REFACTOR"] as DevRunType[]).map((t) => (
              <label key={t} className={`flex items-center gap-1.5 text-sm cursor-pointer px-4 py-2 rounded-full border transition ${
                formType === t
                  ? "border-ink-primary bg-ink-primarySoft text-ink-text"
                  : "border-ink-high bg-white text-ink-muted hover:border-ink-line"
              }`}>
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
            className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none focus:ring-2 focus:ring-ink-primary/20"
            required
          />
          <textarea
            placeholder="任务目标"
            value={formGoal}
            onChange={(e) => setFormGoal(e.target.value)}
            rows={2}
            className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm leading-7 text-ink-text outline-none focus:ring-2 focus:ring-ink-primary/20 resize-none"
            required
          />
          <input
            type="text"
            placeholder="仓库上下文（可选）"
            value={formRepo}
            onChange={(e) => setFormRepo(e.target.value)}
            className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none focus:ring-2 focus:ring-ink-primary/20"
          />
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="rounded-full bg-ink-low px-5 py-2.5 text-sm font-semibold text-ink-muted hover:text-ink-text"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={submitting || !formTitle.trim() || !formGoal.trim()}
              className="rounded-full bg-ink-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-ink-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {submitting ? "创建中…" : "创建"}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="text-sm text-ink-muted py-12 text-center">加载中…</div>
      ) : runs.length === 0 ? (
        <div className="paper-card p-12 text-center">
          <div className="text-4xl mb-4">
            <span className="material-symbols-outlined text-[48px] text-ink-muted">rocket_launch</span>
          </div>
          <h3 className="font-headline text-2xl font-extrabold tracking-tight text-ink-text">还没有 Dev Run 任务</h3>
          <p className="mt-2 text-sm text-ink-muted">点击「新建任务」创建第一个研发任务</p>
        </div>
      ) : (
        <div className="space-y-3">
          {runs.map((run) => (
            <div
              key={run.id}
              onClick={() => router.push(`/app/runs/${run.id}`)}
              className="paper-card p-5 hover:shadow-paper cursor-pointer"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    {typeBadge(run.type)}
                    {statusBadge(run.status)}
                  </div>
                  <h3 className="font-headline text-base font-bold tracking-tight text-ink-text truncate">{run.title}</h3>
                  {run.stageStatus === "awaiting_review" && (
                    <div className="mt-3 flex items-center gap-1.5 text-xs text-ink-tertiary bg-[#fff4ec] rounded-2xl px-3 py-1.5">
                      <span className="material-symbols-outlined text-[14px]">rate_review</span>
                      有待确认的输出
                    </div>
                  )}
                </div>
                <div className="text-xs text-ink-muted shrink-0 flex items-center gap-1">
                  <span className="material-symbols-outlined text-[14px]">flag</span>
                  {STAGE_LABELS[run.currentStage] ?? run.currentStage}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {runs.length > 0 && (
        <div className="mt-8 paper-card p-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">任务概览</div>
          <div className="grid grid-cols-5 gap-4">
            {([
              ["active", "进行中", "play_arrow"],
              ["awaiting_review", "待确认", "rate_review"],
              ["blocked", "阻塞", "block"],
              ["completed", "完成", "check_circle"],
              ["cancelled", "取消", "cancel"],
            ] as const).map(([status, label, icon]) => {
              const count = runs.filter((r) => r.status === status).length;
              return (
                <div key={status} className="text-center">
                  <div className="text-2xl font-headline font-extrabold text-ink-text">{count}</div>
                  <div className="mt-1 flex items-center justify-center gap-1 text-xs text-ink-muted">
                    <span className="material-symbols-outlined text-[14px]">{icon}</span>
                    {label}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </main>
  );
}
