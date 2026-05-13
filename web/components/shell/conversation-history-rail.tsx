import Link from "next/link";

import type { ResearchDashboard } from "@/lib/types";

type ConversationHistoryRailProps = {
  pathname: string;
  snapshot: ResearchDashboard;
};

function getHistoryItems(snapshot: ResearchDashboard) {
  const items = [];
  const firstSignal = snapshot.health.signals[0];

  if (firstSignal) {
    items.push({
      href: "/app",
      title: "知识健康",
      preview: firstSignal.title
    });
  }

  if (snapshot.focusTopic) {
    items.push({
      href: "/app",
      title: "当前主题",
      preview: snapshot.focusTopic.title
    });
  }

  if (snapshot.pendingReviews[0]) {
    items.push({
      href: "/app/ingest",
      title: "待审阅",
      preview: snapshot.pendingReviews[0].title
    });
  }

  if (snapshot.recentSources[0]) {
    items.push({
      href: "/app/raw",
      title: "最新资料",
      preview: snapshot.recentSources[0].title
    });
  }

  return items;
}

export function ConversationHistoryRail({ pathname, snapshot }: ConversationHistoryRailProps) {
  const historyItems = getHistoryItems(snapshot);

  return (
    <div className="flex h-full flex-col">
      <div className="rounded-[28px] bg-white p-4 shadow-paper">
        <button
          className="flex w-full items-center justify-center gap-2 rounded-full bg-ink-primary px-4 py-3 text-sm font-semibold text-white"
          type="button"
        >
          <span aria-hidden="true" className="material-symbols-outlined text-base">
            add_comment
          </span>
          新建对话
        </button>
      </div>

      <div className="mt-6 flex-1 rounded-[32px] bg-white/92 p-4 shadow-paper">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-headline text-base font-bold text-ink-text">最近对话</h2>
            <p className="mt-1 text-sm text-ink-muted">先看知识健康，再回到最近的脉络继续修复。</p>
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
                <div className="text-xs uppercase tracking-[0.18em]">{item.title}</div>
                <div className="mt-2 text-sm font-medium text-ink-text">{item.preview}</div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
