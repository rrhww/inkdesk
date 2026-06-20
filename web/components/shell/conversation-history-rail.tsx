import Link from "next/link";

import type { DevRunSummary, ResearchDashboard } from "@/lib/types";

type ConversationHistoryRailProps = {
  pathname: string;
  snapshot: ResearchDashboard;
  devRuns: DevRunSummary[];
};

const STAGE_LABELS: Record<string, string> = {
  context: "上下文",
  solution: "方案",
  review: "审阅",
  coding: "编码",
  testing: "测试",
  deposit: "沉淀",
};

function getHistoryItems(snapshot: ResearchDashboard, devRuns: DevRunSummary[]) {
  const items: { href: string; title: string; subtitle: string; icon: string }[] = [];

  const activeRuns = devRuns.filter((r) => r.status === "active" || r.status === "awaiting_review" || r.status === "blocked");
  for (const run of activeRuns.slice(0, 3)) {
    const stageLabel = STAGE_LABELS[run.currentStage] ?? run.currentStage;
    items.push({
      href: `/app/runs/${run.id}`,
      title: run.title,
      subtitle: `${run.type} · ${stageLabel}${run.stageStatus === "awaiting_review" ? " · 待确认" : ""}`,
      icon: "rocket_launch",
    });
  }

  if (snapshot.pendingReviews.length > 0) {
    items.push({
      href: "/app/ingest",
      title: `待确认 · ${snapshot.pendingReviews.length} 条 ingest`,
      subtitle: snapshot.pendingReviews[0].title,
      icon: "fact_check",
    });
  }

  return items;
}

export function ConversationHistoryRail({ pathname, snapshot, devRuns }: ConversationHistoryRailProps) {
  const historyItems = getHistoryItems(snapshot, devRuns);

  return (
    <div className="flex h-full flex-col">
      <div className="rounded-[28px] bg-white p-4 shadow-paper">
        <a
          className="flex w-full items-center justify-center gap-2 rounded-full bg-ink-primary px-4 py-3 text-sm font-semibold text-white"
          href="/app"
        >
          <span aria-hidden="true" className="material-symbols-outlined text-base">
            rocket_launch
          </span>
          新建任务
        </a>
      </div>

      <div className="mt-6 flex-1 rounded-[32px] bg-white/92 p-4 shadow-paper">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-headline text-base font-bold text-ink-text">Dev Run</h2>
            <p className="mt-1 text-sm text-ink-muted">任务 & 待办追踪</p>
          </div>
          <span className="rounded-full bg-ink-low px-3 py-1 text-xs text-ink-muted">{historyItems.length} 条</span>
        </div>

        <div className="mt-4 space-y-3">
          {historyItems.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);

            return (
              <Link
                key={`${item.href}-${item.title}`}
                aria-current={active ? "page" : undefined}
                className={`block rounded-[24px] border px-4 py-3 transition ${
                  active
                    ? "border-ink-primary bg-ink-low text-ink-text"
                    : "border-black/5 text-ink-muted hover:border-ink-primary/30 hover:bg-ink-low/70"
                }`}
                href={item.href}
              >
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-ink-muted">{item.icon}</span>
                  <span className="text-sm font-medium text-ink-text">{item.title}</span>
                </div>
                <div className="mt-1.5 ml-[24px] text-xs text-ink-muted">{item.subtitle}</div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
