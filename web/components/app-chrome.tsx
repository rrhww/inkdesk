"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import { AppHeader } from "@/components/app-header";
import { AppSidebarContent } from "@/components/app-sidebar";
import { getAppRouteChrome } from "@/lib/app-shell";
import type { ResearchDashboard } from "@/lib/types";

type AppChromeProps = {
  children: ReactNode;
  logoutAction: () => Promise<void>;
  snapshot: ResearchDashboard;
};

export function AppChrome({ children, logoutAction, snapshot }: AppChromeProps) {
  const pathname = usePathname() ?? "/app";
  const chrome = getAppRouteChrome(pathname, snapshot);

  return (
    <div className="min-h-screen">
      <AppSidebarContent pathname={pathname} snapshot={snapshot} />
      <div className="lg:ml-80">
        <AppHeader
          title={chrome.title}
          subtitle={chrome.subtitle}
          contextItems={chrome.contextItems}
          action={
            <form action={logoutAction}>
              <button className="rounded-full border border-black/10 bg-white/70 px-4 py-3 text-sm font-semibold text-ink-text" type="submit">
                退出
              </button>
            </form>
          }
        />
        {children}
      </div>
    </div>
  );
}
