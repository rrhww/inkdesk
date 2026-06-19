"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getDevRun } from "@/lib/research";
import type { DevRun } from "@/lib/types";

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

  if (loading) {
    return <div className="max-w-4xl mx-auto px-6 py-8 text-sm text-gray-400">加载中…</div>;
  }

  if (error || !run) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8 text-center">
        <p className="text-gray-500 text-sm mb-3">{error ?? "任务不存在"}</p>
        <button onClick={() => router.push("/app")} className="text-sm text-gray-900 underline">
          返回任务列表
        </button>
      </div>
    );
  }

  const typeBadge = (type: string) => {
    const map: Record<string, string> = {
      PRD: "bg-purple-100 text-purple-800",
      BUG: "bg-red-100 text-red-800",
      REFACTOR: "bg-blue-100 text-blue-800",
    };
    return (
      <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${map[type] ?? "bg-gray-100 text-gray-600"}`}>
        {type}
      </span>
    );
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <button onClick={() => router.push("/app")} className="text-sm text-gray-400 hover:text-gray-600 mb-4 flex items-center gap-1">
        <span className="material-symbols-outlined text-[16px]">arrow_back</span>
        返回任务列表
      </button>

      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          {typeBadge(run.type)}
          <span className="text-xs text-gray-400">{run.id}</span>
        </div>
        <h1 className="text-xl font-semibold text-gray-900">{run.title}</h1>
        <p className="text-sm text-gray-500 mt-1">{run.goal}</p>
      </div>

      {/* Stage timeline */}
      <div className="mb-8">
        <h2 className="text-sm font-medium text-gray-700 mb-3">阶段轨道</h2>
        <div className="flex items-center gap-2">
          {STAGE_ORDER.map((stage, i) => {
            const info = run.stages.find((s) => s.name === stage);
            const st = info?.status ?? "pending";
            const isActive = stage === run.currentStage;
            const isCompleted = st === "completed";
            const isSkipped = st === "skipped";

            let dotClass = "bg-gray-200";
            if (isCompleted) dotClass = "bg-green-500";
            else if (isSkipped) dotClass = "bg-gray-400";
            else if (isActive) dotClass = "bg-blue-500 ring-2 ring-blue-200";

            return (
              <div key={stage} className="flex items-center gap-2 flex-1 last:flex-[0_0_auto]">
                <div className="flex flex-col items-center gap-1 min-w-0">
                  <div className={`w-3 h-3 rounded-full ${dotClass} shrink-0`} />
                  <span className={`text-[11px] whitespace-nowrap ${isActive ? "text-gray-900 font-medium" : isCompleted ? "text-gray-500" : "text-gray-400"}`}>
                    {STAGE_LABELS[stage]}
                  </span>
                  {isSkipped && <span className="text-[10px] text-gray-400">跳过</span>}
                </div>
                {i < STAGE_ORDER.length - 1 && (
                  <div className={`flex-1 h-px ${isCompleted ? "bg-green-300" : "bg-gray-200"}`} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Events */}
      <div className="mb-8">
        <h2 className="text-sm font-medium text-gray-700 mb-3">事件记录</h2>
        {run.events.length === 0 ? (
          <p className="text-xs text-gray-400">暂无事件</p>
        ) : (
          <div className="space-y-2">
            {run.events.map((event) => (
              <div key={event.id} className="flex gap-3 p-3 bg-white border border-gray-100 rounded-lg text-sm">
                <span className="text-xs text-gray-400 shrink-0 w-14">
                  {new Date(event.createdAt).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}
                </span>
                <span className="text-xs font-medium text-gray-600 shrink-0 w-24">
                  {event.stage ? `${STAGE_LABELS[event.stage] ?? event.stage}` : "—"}
                </span>
                <span className="text-xs text-gray-500 flex-1">
                  {event.eventType}
                  {event.payload && Object.keys(event.payload).length > 0
                    ? `: ${JSON.stringify(event.payload)}`
                    : ""}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center gap-3 text-sm text-gray-400">
        <span>创建于 {new Date(run.createdAt).toLocaleString("zh-CN")}</span>
        {run.completedAt && <span>完成于 {new Date(run.completedAt).toLocaleString("zh-CN")}</span>}
        {run.cancelledAt && <span>取消于 {new Date(run.cancelledAt).toLocaleString("zh-CN")}</span>}
      </div>
    </div>
  );
}
