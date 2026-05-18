import type { ReactNode } from "react";

import { TopSectionTabs } from "@/components/shell/top-section-tabs";

type AppHeaderContextItem = {
  label: string;
  value: string;
};

type AppHeaderProps = {
  title: string;
  subtitle?: string;
  contextItems?: AppHeaderContextItem[];
  action?: ReactNode;
};

export function AppHeader({ title, subtitle, contextItems, action }: AppHeaderProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-black/10 bg-[rgba(247,243,236,0.86)] backdrop-blur-xl">
      <div className="border-b border-black/10 px-5 py-3 lg:px-8">
        <div className="flex flex-col gap-3">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">分区导航</div>
          <TopSectionTabs />
        </div>
      </div>
      <div className="px-5 py-5 lg:px-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0 max-w-3xl">
            <div className="slip">当前页眉</div>
            <h1 className="mt-4 font-headline text-[clamp(2rem,3.2vw,3rem)] font-bold leading-[1.05] tracking-[-0.03em] text-ink-text">
              {title}
            </h1>
            {subtitle ? <p className="mt-3 text-sm leading-7 text-ink-muted">{subtitle}</p> : null}
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </div>
      </div>
      {contextItems?.length ? (
        <div className="border-t border-black/10 px-5 py-4 lg:px-8">
          <div className="flex flex-wrap gap-3">
            {contextItems.map((item) => (
              <div key={item.label} className="desk-panel px-4 py-3">
                <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{item.label}</div>
                <div className="mt-2 font-headline text-xl font-bold tracking-[-0.02em] text-ink-text">{item.value}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </header>
  );
}
