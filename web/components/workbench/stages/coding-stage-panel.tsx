"use client";

import { useState, useEffect, useRef } from "react";
import { executeCoding, getCodingStatus, extractCodingBriefing, extractCodingResult, submitStageOutput } from "@/lib/research";
import type { DevRun, DevRunStageStatus } from "@/lib/types";
import { PanelCard } from "@/components/ui/panel-card";

type CodingStagePanelProps = {
  run: DevRun;
  stageStatus: DevRunStageStatus;
  onRunUpdate: (run: DevRun) => void;
};

export function CodingStagePanel({ run, stageStatus, onRunUpdate }: CodingStagePanelProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [executing, setExecuting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const briefing = extractCodingBriefing(run);
  const result = extractCodingResult(run);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const handleSkip = async () => {
    setLoading(true);
    setError(null);
    try {
      const updated = await submitStageOutput(run.id, "coding", {
        summary: "手动跳过 coding 阶段，不调用 Claude Code CLI",
        skipped: true,
        skipReason: "用户选择手动批准",
      });
      onRunUpdate(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "跳过编码阶段失败");
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    setLoading(true);
    setError(null);
    setExecuting(true);
    try {
      const updated = await executeCoding(run.id);
      onRunUpdate(updated);
      // 如果结果还没回来（理论上 execute 是同步等待的），启动轮询
      const updatedResult = extractCodingResult(updated);
      if (!updatedResult) {
        pollRef.current = setInterval(async () => {
          try {
            const status = await getCodingStatus(run.id);
            if (status.status === "completed" || status.status === "failed") {
              if (pollRef.current) clearInterval(pollRef.current);
              pollRef.current = null;
              setExecuting(false);
              // 刷新 run 数据
              const { getDevRun } = await import("@/lib/research");
              const refreshed = await getDevRun(run.id);
              onRunUpdate(refreshed);
            }
          } catch {
            // 忽略轮询错误
          }
        }, 2000);
      } else {
        setExecuting(false);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "启动 Claude Code 失败");
      setExecuting(false);
    } finally {
      setLoading(false);
    }
  };

  // pending 状态：显示执行按钮
  if (stageStatus === "pending" || !briefing) {
    return (
      <PanelCard className="p-6">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">编码阶段</div>
        <p className="text-sm text-ink-muted mb-4">
          点击下方按钮，Inkdesk 将组装 Briefing 并启动 Claude Code CLI 子进程执行编码任务。
        </p>
        {error && (
          <div className="mb-4 rounded-2xl bg-ink-errorSoft px-4 py-3 text-sm text-ink-errorText">{error}</div>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleExecute}
            disabled={loading}
            className="rounded-full bg-ink-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-ink-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? "启动中…" : "启动 Claude Code"}
          </button>
          <button
            onClick={handleSkip}
            disabled={loading}
            className="rounded-full bg-ink-low px-5 py-2.5 text-sm font-medium text-ink-text hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed"
          >
            跳过，手动批准
          </button>
        </div>
      </PanelCard>
    );
  }

  // 执行中
  if (executing && !result) {
    return (
      <PanelCard className="p-6">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">编码阶段</div>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-5 h-5 border-2 border-ink-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-ink-text">Claude Code 执行中…</span>
        </div>
        <details className="mt-4">
          <summary className="text-xs text-ink-muted cursor-pointer">查看 Briefing</summary>
          <pre className="mt-2 whitespace-pre-wrap text-xs text-ink-text bg-ink-low rounded-2xl p-4 max-h-64 overflow-auto">
{briefing}
          </pre>
        </details>
      </PanelCard>
    );
  }

  // 有结果
  return (
    <PanelCard className="p-6">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">
        编码结果
        {stageStatus === "completed" && <span className="ml-2 text-green-600">已完成</span>}
      </div>

      {result && (
        <>
          <div className="flex items-center gap-2 mb-4">
            <span className={`material-symbols-outlined text-[20px] ${result.success ? "text-green-600" : "text-red-500"}`}>
              {result.success ? "check_circle" : "error"}
            </span>
            <span className="text-sm font-medium text-ink-text">
              {result.success ? "执行成功" : "执行失败"}
            </span>
          </div>

          {result.error && (
            <div className="mb-4 rounded-2xl bg-ink-errorSoft px-4 py-3 text-sm text-ink-errorText">
              {result.error}
            </div>
          )}

          {result.result && (
            <div className="mb-4">
              <div className="text-xs text-ink-muted mb-2">执行输出</div>
              <pre className="whitespace-pre-wrap text-sm text-ink-text bg-ink-low rounded-2xl p-4 max-h-96 overflow-auto">
{result.result}
              </pre>
            </div>
          )}

          {!result.success && (
            <button
              onClick={handleExecute}
              disabled={loading}
              className="rounded-full bg-ink-low px-5 py-2.5 text-sm font-medium text-ink-text hover:bg-white disabled:opacity-40"
            >
              {loading ? "启动中…" : "重试"}
            </button>
          )}
        </>
      )}

      <details className="mt-4">
        <summary className="text-xs text-ink-muted cursor-pointer">查看 Briefing</summary>
        <pre className="mt-2 whitespace-pre-wrap text-xs text-ink-text bg-ink-low rounded-2xl p-4 max-h-64 overflow-auto">
{briefing}
        </pre>
      </details>
    </PanelCard>
  );
}
