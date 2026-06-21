import Link from "next/link";

import { EmptyState } from "@/components/ui/empty-state";
import { PageShell } from "@/components/workbench/page-shell";
import { getCompileQueue } from "@/lib/research";
import type { CompileTaskSummary } from "@/lib/types";

const STATUS_LABELS: Record<string, string> = {
  PENDING: "排队中",
  RUNNING: "运行中",
  COMPLETED: "已完成",
  FAILED: "失败",
};

const STATUS_COLORS: Record<string, string> = {
  PENDING: "bg-ink-low text-ink-muted",
  RUNNING: "bg-ink-primarySoft text-ink-primary",
  COMPLETED: "bg-green-100 text-green-700",
  FAILED: "bg-ink-errorSoft text-ink-errorText",
};

const STATUS_ICONS: Record<string, string> = {
  PENDING: "schedule",
  RUNNING: "progress_activity",
  COMPLETED: "check_circle",
  FAILED: "error",
};

function CompileTaskRow({ task }: { task: CompileTaskSummary }) {
  return (
    <Link
      href={`/app/compile/${task.id}`}
      className="paper-card p-5 hover:shadow-paper block"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${STATUS_COLORS[task.status] ?? "bg-ink-low text-ink-muted"}`}>
              <span className="material-symbols-outlined text-[14px]">{STATUS_ICONS[task.status] ?? "help"}</span>
              {STATUS_LABELS[task.status] ?? task.status}
            </span>
          </div>
          <h3 className="font-headline text-base font-bold tracking-tight text-ink-text truncate">
            {task.sourceTitle ?? "未命名来源"}
          </h3>
          <p className="mt-1 text-xs text-ink-muted">
            {task.createdAt ? new Date(task.createdAt).toLocaleString("zh-CN") : "—"} 创建
            {task.completedAt ? ` · ${new Date(task.completedAt).toLocaleString("zh-CN")} 完成` : ""}
          </p>
        </div>
        <span className="material-symbols-outlined text-ink-muted text-[20px] shrink-0">chevron_right</span>
      </div>
    </Link>
  );
}

export default async function CompileQueuePage() {
  const tasks = await getCompileQueue().catch(() => []);

  return (
    <PageShell
      eyebrow="compile"
      title="编译流水线"
      description="每条 raw 材料导入后自动进入五步编译流水线（Insight → Evidence → Router → Conflict → Patch），结果进入审阅队列。只有你接受后才写入 wiki。"
    >
      <div className="mt-8 space-y-3">
        {tasks.length === 0 ? (
          <EmptyState
            eyebrow="compile empty"
            title="暂无编译任务"
            description="导入 raw 材料后会自动触发编译流水线，或对已导入的 raw 手动发起编译。"
            actionLabel="补充 raw"
            href="/app/raw"
          />
        ) : (
          tasks.map((task) => (
            <CompileTaskRow key={task.id} task={task} />
          ))
        )}
      </div>
    </PageShell>
  );
}
