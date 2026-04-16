import type { ReactNode } from "react";

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
    <header className="sticky top-0 z-30 border-b border-black/5 bg-white/80 backdrop-blur-lg">
      <div className="flex min-h-16 items-center justify-between gap-6 px-6 py-4 lg:px-8">
        <div>
          <h1 className="font-headline text-xl font-extrabold tracking-tight text-ink-text">{title}</h1>
          {subtitle ? <p className="mt-1 text-sm text-ink-muted">{subtitle}</p> : null}
        </div>
        {action}
      </div>
      {contextItems?.length ? (
        <div className="border-t border-black/5 px-6 py-3 lg:px-8">
          <div className="flex flex-wrap gap-3">
            {contextItems.map((item) => (
              <div key={item.label} className="rounded-full bg-ink-low px-4 py-2 text-sm text-ink-muted">
                <span className="font-semibold text-ink-text">{item.value}</span>
                <span className="ml-2">{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </header>
  );
}
