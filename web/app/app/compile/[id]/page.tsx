import Link from "next/link";
import { revalidatePath } from "next/cache";

import { EmptyState } from "@/components/ui/empty-state";
import { PanelCard } from "@/components/ui/panel-card";
import { PageShell } from "@/components/workbench/page-shell";
import { getCompileTask, retryCompileTask } from "@/lib/research";
import type { CompileStepResponse } from "@/lib/types";

const STEP_LABELS: Record<string, string> = {
  INSIGHT: "信息提取",
  EVIDENCE: "证据绑定",
  ROUTER: "主题路由",
  CONFLICT: "冲突检查",
  PATCH: "补丁生成",
};

const STEP_STATUS_LABELS: Record<string, string> = {
  PENDING: "待执行",
  RUNNING: "执行中",
  COMPLETED: "已完成",
  FAILED: "失败",
};

const STEP_STATUS_COLORS: Record<string, string> = {
  PENDING: "bg-ink-low text-ink-muted",
  RUNNING: "bg-ink-primarySoft text-ink-primary",
  COMPLETED: "bg-green-100 text-green-700",
  FAILED: "bg-ink-errorSoft text-ink-errorText",
};

const STEP_STATUS_ICONS: Record<string, string> = {
  PENDING: "radio_button_unchecked",
  RUNNING: "progress_activity",
  COMPLETED: "check_circle",
  FAILED: "error",
};

const TASK_STATUS_LABELS: Record<string, string> = {
  PENDING: "排队中",
  RUNNING: "运行中",
  COMPLETED: "已完成",
  FAILED: "失败",
};

async function retryAction(formData: FormData) {
  "use server";
  const taskId = String(formData.get("taskId") ?? "").trim();
  if (!taskId) return;
  await retryCompileTask(taskId);
  revalidatePath(`/app/compile/${taskId}`);
  revalidatePath("/app/compile");
}

function CompileStepRow({ step, isLast }: { step: CompileStepResponse; isLast: boolean }) {
  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center">
        <span className={`material-symbols-outlined text-[24px] ${step.status === "RUNNING" ? "text-ink-primary animate-spin" : step.status === "COMPLETED" ? "text-green-600" : step.status === "FAILED" ? "text-ink-errorText" : "text-ink-muted"}`}>
          {STEP_STATUS_ICONS[step.status] ?? "help"}
        </span>
        {!isLast && <div className="w-px flex-1 bg-ink-high mt-1 mb-1" />}
      </div>
      <div className={`pb-6 min-w-0 flex-1 ${isLast ? "" : ""}`}>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-semibold text-ink-text">
            {step.sortOrder}. {STEP_LABELS[step.stepName] ?? step.stepName}
          </span>
          <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${STEP_STATUS_COLORS[step.status] ?? "bg-ink-low text-ink-muted"}`}>
            {STEP_STATUS_LABELS[step.status] ?? step.status}
          </span>
        </div>
        {step.errorMessage && (
          <p className="text-xs text-ink-errorText mt-1 rounded-[14px] bg-ink-errorSoft px-3 py-2">{step.errorMessage}</p>
        )}
        {step.completedAt && (
          <p className="text-xs text-ink-muted mt-1">
            完成于 {new Date(step.completedAt).toLocaleString("zh-CN")}
          </p>
        )}
      </div>
    </div>
  );
}

export default async function CompileTaskPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const task = await getCompileTask(id).catch(() => null);

  if (!task) {
    return (
      <PageShell eyebrow="compile" title="编译任务未找到">
        <div className="mt-8">
          <EmptyState
            eyebrow="not found"
            title="编译任务不存在"
            description="该任务可能已被删除或 ID 不正确。"
            actionLabel="返回编译队列"
            href="/app/compile"
          />
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell
      eyebrow="compile"
      title={`编译任务 ${id.slice(0, 8)}…`}
      description={`来源: ${task.sourceId ?? "—"} · 状态: ${TASK_STATUS_LABELS[task.status] ?? task.status}`}
    >
      <div className="mt-8 space-y-6">
        <div className="flex items-center gap-3">
          <Link
            href="/app/compile"
            className="inline-flex items-center gap-1 rounded-full bg-ink-low px-4 py-2 text-sm font-medium text-ink-muted hover:text-ink-text"
          >
            <span className="material-symbols-outlined text-[16px]">arrow_back</span>
            返回队列
          </Link>
          {task.status === "FAILED" && (
            <form action={retryAction}>
              <input name="taskId" type="hidden" value={task.id} />
              <button
                type="submit"
                className="inline-flex items-center gap-1.5 rounded-full bg-ink-primary px-4 py-2 text-sm font-semibold text-white hover:bg-ink-primary/90"
              >
                <span className="material-symbols-outlined text-[16px]">refresh</span>
                重试
              </button>
            </form>
          )}
        </div>

        {task.errorMessage && (
          <PanelCard className="p-5 bg-ink-errorSoft">
            <div className="flex items-start gap-3">
              <span className="material-symbols-outlined text-ink-errorText text-[20px]">error</span>
              <div className="text-sm leading-6 text-ink-errorText">{task.errorMessage}</div>
            </div>
          </PanelCard>
        )}

        <PanelCard className="p-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-6">编译步骤</div>
          <div className="space-y-1">
            {task.steps.map((step, i) => (
              <CompileStepRow key={step.id} step={step} isLast={i === task.steps.length - 1} />
            ))}
            {task.steps.length === 0 && (
              <p className="text-sm text-ink-muted py-4 text-center">编译尚未开始，步骤信息将在启动后出现。</p>
            )}
          </div>
        </PanelCard>

        <div className="flex gap-4 text-xs text-ink-muted">
          <span>创建: {new Date(task.createdAt).toLocaleString("zh-CN")}</span>
          {task.startedAt && <span>启动: {new Date(task.startedAt).toLocaleString("zh-CN")}</span>}
          {task.completedAt && <span>完成: {new Date(task.completedAt).toLocaleString("zh-CN")}</span>}
        </div>
      </div>
    </PageShell>
  );
}
