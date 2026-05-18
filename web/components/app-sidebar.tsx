"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ConversationHistoryRail } from "@/components/shell/conversation-history-rail";
import type { ResearchDashboard } from "@/lib/types";

export function AppSidebarContent({ pathname, snapshot }: { pathname: string; snapshot: ResearchDashboard }) {
  return (
    <>
      <div className="sticky top-0 z-30 border-b border-black/10 bg-[rgba(243,237,226,0.92)] px-4 py-3 backdrop-blur lg:hidden">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">桌面工具</div>
            <div className="mt-1 font-headline text-lg font-bold tracking-[-0.02em] text-ink-text">快速入口</div>
          </div>
          <button
            className="inline-flex items-center gap-2 rounded-full border border-ink-primary/20 bg-ink-primary px-4 py-2.5 text-sm font-semibold text-white shadow-paper"
            type="button"
          >
            <span aria-hidden="true" className="material-symbols-outlined text-base">
              add_comment
            </span>
            发起对话
          </button>
        </div>
      </div>

      <aside className="fixed inset-y-0 left-0 z-40 hidden w-80 flex-col border-r border-black/10 bg-[rgba(236,227,212,0.76)] px-5 py-6 lg:flex">
        <div className="mb-6">
          <Link className="paper-card block px-5 py-5" href="/app">
            <div className="flex items-start gap-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-md bg-ink-primary text-white shadow-paper">
                <span aria-hidden="true" className="material-symbols-outlined text-base">
                  edit_note
                </span>
              </div>
              <div className="min-w-0">
                <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">研究索引</div>
                <div className="mt-2 font-headline text-[1.6rem] font-bold tracking-[-0.03em] text-ink-primary">Inkvault</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.24em] text-ink-muted">LLM Wiki</div>
                <p className="mt-3 text-sm leading-7 text-ink-muted">把问答、raw、审阅与知识页收回到一张私人研究桌面上。</p>
              </div>
            </div>
          </Link>
        </div>

        <div className="min-h-0 flex-1">
          <ConversationHistoryRail pathname={pathname} snapshot={snapshot} />
        </div>
      </aside>
    </>
  );
}

export function AppSidebar({ snapshot }: { snapshot: ResearchDashboard }) {
  const pathname = usePathname();

  return <AppSidebarContent pathname={pathname} snapshot={snapshot} />;
}
