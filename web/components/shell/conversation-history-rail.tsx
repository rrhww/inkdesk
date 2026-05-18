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
      <div className="paper-card px-4 py-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">今日研究桌</div>
            <p className="mt-2 text-sm leading-7 text-ink-muted">从最靠前的线索卡片继续，不让研究上下文掉地上。</p>
          </div>
          <span className="stamp">Ask-first</span>
        </div>
        <button
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-full bg-ink-primary px-4 py-3 text-sm font-semibold text-white shadow-paper"
          type="button"
        >
          <span aria-hidden="true" className="material-symbols-outlined text-base">
            add_comment
          </span>
          新建对话
        </button>
      </div>

      <div className="paper-card mt-6 flex-1 px-4 py-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="slip">桌面标签</div>
            <h2 className="mt-3 font-headline text-2xl font-bold tracking-[-0.03em] text-ink-text">最近对话</h2>
            <p className="mt-2 text-sm leading-7 text-ink-muted">先看知识健康，再回到最近的脉络继续修复。</p>
          </div>
          <span className="slip">{historyItems.length} 条</span>
        </div>

        <div className="mt-4 space-y-3">
          {historyItems.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);

            return (
              <Link
                key={`${item.href}-${item.title}`}
                aria-current={active ? "page" : undefined}
                className={`desk-lift block rounded-[24px] border px-4 py-4 transition ${
                  active
                    ? "border-ink-primary/40 bg-ink-primarySoft/90 text-ink-text"
                    : "border-black/10 bg-white/70 text-ink-muted hover:border-ink-primary/30 hover:bg-white"
                }`}
                href={item.href}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="text-[11px] uppercase tracking-[0.2em]">{item.title}</div>
                  <span className={active ? "stamp-soft" : "slip"}>{active ? "当前页" : "线索"}</span>
                </div>
                <div className="mt-3 font-headline text-xl font-bold tracking-[-0.03em] text-ink-text">{item.preview}</div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
