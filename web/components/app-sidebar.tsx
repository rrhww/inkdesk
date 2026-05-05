"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ConversationHistoryRail } from "@/components/shell/conversation-history-rail";
import type { ResearchDashboard } from "@/lib/types";

export function AppSidebarContent({ pathname, snapshot }: { pathname: string; snapshot: ResearchDashboard }) {
  return (
    <>
      <div className="sticky top-0 z-30 border-b border-black/5 bg-ink-low/90 px-6 py-4 backdrop-blur lg:hidden">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">对话入口</div>
        <button
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-full bg-ink-primary px-4 py-3 text-sm font-semibold text-white"
          type="button"
        >
          <span aria-hidden="true" className="material-symbols-outlined text-base">
            add_comment
          </span>
          发起对话
        </button>
      </div>

      <aside className="fixed inset-y-0 left-0 z-40 hidden w-72 flex-col bg-ink-low px-4 py-8 lg:flex">
        <div className="mb-8 flex items-center gap-3 px-2">
          <Link className="flex items-center gap-3" href="/app">
            <div className="flex h-9 w-9 items-center justify-center rounded-sm bg-ink-primary text-white">
              <span aria-hidden="true" className="material-symbols-outlined text-sm">
                edit_note
              </span>
            </div>
            <div>
              <div className="font-headline text-lg font-extrabold tracking-tight text-ink-primary">Inkvault</div>
              <div className="font-headline text-[10px] uppercase tracking-[0.22em] text-ink-muted">LLM Wiki</div>
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
