"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getDevRun } from "@/lib/research";
import { postInkdeskJson } from "@/lib/server-api";
import type { DevRun } from "@/lib/types";
import { PanelCard } from "@/components/ui/panel-card";
import { PageShell } from "@/components/workbench/page-shell";

const STAGE_LABELS: Record<string, string> = {
  context: "上下文",
  solution: "方案",
  review: "审阅",
  coding: "编码",
  testing: "测试",
  deposit: "沉淀",
};

const STAGE_ORDER = ["context", "solution", "review", "coding", "testing", "deposit"];

export default function DevRunDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [run, setRun] = useState<DevRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function refreshRun() {
    if (!params.id) return;
    try {
      const data = await getDevRun(params.id);
      setRun(data);
    } catch {
      setError("任务不存在或无法访问");
    }
  }

  useEffect(() => {
    if (!params.id) return;
    (async () => {
      try {
        const data = await getDevRun(params.id);
        setRun(data);
      } catch {
        setError("任务不存在或无法访问");
      } finally {
        setLoading(false);
      }
    })();
  }, [params.id]);

  async function handleAction(action: "approve" | "complete" | "cancel") {
    if (!run) return;
    setSubmitting(true);
    setActionError(null);
    try {
      if (action === "cancel") {
        await postInkdeskJson(`/runs/${run.id}/cancel`, {});
      } else {
        await postInkdeskJson(`/runs/${run.id}/advance`, { action });
      }
      await refreshRun();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "操作失败";
      setActionError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
        <div className="text-sm text-ink-muted">加载中…</div>
      </main>
    );
  }

  if (error || !run) {
    return (
      <main className="mx-auto max-w-shell px-6 py-10 lg:px-8 text-center">
        <div className="paper-card p-12">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-3">任务不存在</div>
          <p className="text-ink-muted text-sm mb-4">{error ?? "任务不存在"}</p>
          <button onClick={() => router.push("/app")} className="rounded-full bg-ink-primary px-5 py-2.5 text-sm font-semibold text-white">
            返回任务列表
          </button>
        </div>
      </main>
    );
  }

  const typeBadge = (type: string) => {
    const map: Record<string, string> = {
      PRD: "bg-ink-primarySoft text-ink-primary",
      BUG: "bg-ink-errorSoft text-ink-errorText",
      REFACTOR: "bg-ink-low text-ink-text",
    };
    return (
      <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${map[type] ?? "bg-ink-low text-ink-muted"}`}>
        {type}
      </span>
    );
  };

  return (
    <PageShell
      eyebrow="Dev Run"
      title={run.title}
      description={run.goal}
    >
      <button onClick={() => router.push("/app")} className="text-sm text-ink-muted hover:text-ink-text mb-4 flex items-center gap-1">
        <span className="material-symbols-outlined text-[16px]">arrow_back</span>
        返回任务列表
      </button>

      <div className="flex items-center gap-3 mb-4">
        {typeBadge(run.type)}
        <span className="text-xs text-ink-muted">{run.id}</span>
      </div>

      {/* Stage timeline */}
      <PanelCard className="p-6 mb-6">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">阶段轨道</div>
        <div className="flex items-center gap-2">
          {STAGE_ORDER.map((stage, i) => {
            const info = run.stages.find((s) => s.name === stage);
            const st = info?.status ?? "pending";
            const isActive = stage === run.currentStage;
            const isCompleted = st === "completed";
            const isSkipped = st === "skipped";

            let dotClass = "bg-ink-high";
            if (isCompleted) dotClass = "bg-ink-primary";
            else if (isSkipped) dotClass = "bg-ink-muted";
            else if (isActive) dotClass = "bg-ink-primary ring-2 ring-ink-primarySoft";

            return (
              <div key={stage} className="flex items-center gap-2 flex-1 last:flex-[0_0_auto]">
                <div className="flex flex-col items-center gap-1 min-w-0">
                  <div className={`w-3 h-3 rounded-full ${dotClass} shrink-0`} />
                  <span className={`text-[11px] whitespace-nowrap ${isActive ? "text-ink-text font-semibold" : isCompleted ? "text-ink-muted" : "text-ink-muted/60"}`}>
                    {STAGE_LABELS[stage]}
                  </span>
                  {isSkipped && <span className="text-[10px] text-ink-muted/60">跳过</span>}
                </div>
                {i < STAGE_ORDER.length - 1 && (
                  <div className={`flex-1 h-px ${isCompleted ? "bg-ink-primary/30" : "bg-ink-high"}`} />
                )}
              </div>
            );
          })}
        </div>
      </PanelCard>

      {/* Events */}
      <PanelCard className="p-6 mb-6">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">事件记录</div>
        {run.events.length === 0 ? (
          <p className="text-xs text-ink-muted">暂无事件</p>
        ) : (
          <div className="space-y-2">
            {run.events.map((event) => (
              <div key={event.id} className="flex gap-3 p-3 rounded-2xl bg-ink-low text-sm">
                <span className="text-xs text-ink-muted shrink-0 w-14">
                  {new Date(event.createdAt).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}
                </span>
                <span className="text-xs font-medium text-ink-text shrink-0 w-24">
                  {event.stage ? `${STAGE_LABELS[event.stage] ?? event.stage}` : "—"}
                </span>
                <span className="text-xs text-ink-muted flex-1">
                  {event.eventType}
                  {event.payload && Object.keys(event.payload).length > 0
                    ? `: ${JSON.stringify(event.payload)}`
                    : ""}
                </span>
              </div>
            ))}
          </div>
        )}
      </PanelCard>

      <div className="flex items-center gap-4 text-xs text-ink-muted">
        <span>创建于 {new Date(run.createdAt).toLocaleString("zh-CN")}</span>
        {run.completedAt && <span>完成于 {new Date(run.completedAt).toLocaleString("zh-CN")}</span>}
        {run.cancelledAt && <span>取消于 {new Date(run.cancelledAt).toLocaleString("zh-CN")}</span>}
      </div>

      {run.status !== "completed" && run.status !== "cancelled" && (
        <PanelCard className="p-6 mt-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">操作</div>
          <div className="flex flex-wrap items-center gap-3">
            {run.stageStatus === "awaiting_review" && (
              <button
                onClick={() => handleAction("approve")}
                disabled={submitting}
                className="rounded-full bg-ink-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-ink-primary/90 disabled:opacity-40"
              >
                批准推进
              </button>
            )}
            {run.currentStage === "deposit" && run.stageStatus === "awaiting_review" && (
              <button
                onClick={() => handleAction("complete")}
                disabled={submitting}
                className="rounded-full bg-green-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-40"
              >
                完成任务
              </button>
            )}
            <button
              onClick={() => handleAction("cancel")}
              disabled={submitting}
              className="rounded-full bg-ink-errorSoft px-5 py-2.5 text-sm font-semibold text-ink-errorText hover:bg-ink-errorSoft/70 disabled:opacity-40"
            >
              取消任务
            </button>
            <a
              href={`/app/ask?runId=${run.id}`}
              className="rounded-full bg-ink-low px-5 py-2.5 text-sm font-medium text-ink-text hover:bg-white inline-block"
            >
              Ask 追问
            </a>
          </div>
          {actionError && (
            <div className="mt-4 rounded-2xl bg-ink-errorSoft px-4 py-3 text-sm text-ink-errorText">{actionError}</div>
          )}
        </PanelCard>
      )}
    </PageShell>
  );
}
