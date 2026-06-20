"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import { AppHeader } from "@/components/app-header";
import { AppSidebarContent } from "@/components/app-sidebar";
import { getAppRouteChrome } from "@/lib/app-shell";
import type { DevRunSummary, ResearchDashboard } from "@/lib/types";

type AppChromeProps = {
  children: ReactNode;
  snapshot: ResearchDashboard;
  devRuns: DevRunSummary[];
};

export function AppChrome({ children, snapshot, devRuns }: AppChromeProps) {
  const pathname = usePathname() ?? "/app";
  const chrome = getAppRouteChrome(pathname, snapshot);

  return (
    <div className="min-h-screen">
      <AppSidebarContent pathname={pathname} snapshot={snapshot} devRuns={devRuns} />
      <div className="lg:ml-72">
        <AppHeader
          title={chrome.title}
          subtitle={chrome.subtitle}
        />
        {children}
      </div>
    </div>
  );
}
