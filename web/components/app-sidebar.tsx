"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ConversationHistoryRail } from "@/components/shell/conversation-history-rail";
import type { DevRunSummary, ResearchDashboard } from "@/lib/types";

export function AppSidebarContent({ pathname, snapshot, devRuns }: { pathname: string; snapshot: ResearchDashboard; devRuns: DevRunSummary[] }) {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-72 flex-col bg-ink-low px-4 py-8 lg:flex">
      <div className="mb-8 flex items-center gap-3 px-2">
        <Link className="flex items-center gap-3" href="/app">
          <div className="flex h-9 w-9 items-center justify-center rounded-sm bg-ink-primary text-white">
            <span aria-hidden="true" className="material-symbols-outlined text-sm">
              rocket_launch
            </span>
          </div>
          <div>
            <div className="font-headline text-lg font-extrabold tracking-tight text-ink-primary">Inkdesk</div>
            <div className="font-headline text-[10px] uppercase tracking-[0.22em] text-ink-muted">Dev Run</div>
          </div>
        </Link>
      </div>

      <div className="min-h-0 flex-1">
        <ConversationHistoryRail pathname={pathname} snapshot={snapshot} devRuns={devRuns} />
      </div>
    </aside>
  );
}

export function AppSidebar({ snapshot, devRuns }: { snapshot: ResearchDashboard; devRuns: DevRunSummary[] }) {
  const pathname = usePathname();

  return <AppSidebarContent pathname={pathname} snapshot={snapshot} devRuns={devRuns} />;
}
