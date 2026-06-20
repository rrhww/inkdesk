"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { PRIMARY_SECTIONS, pathnameMatchesSection } from "@/lib/app-shell";

type AppHeaderProps = {
  title: string;
  subtitle?: string;
};

export function AppHeader({ title, subtitle }: AppHeaderProps) {
  const pathname = usePathname() ?? "/app";

  return (
    <header className="sticky top-0 z-30 border-b border-black/5 bg-white/80 backdrop-blur-lg">
      <div className="flex items-center justify-center px-6 py-2.5 lg:px-8">
        <nav aria-label="主分区" className="w-full">
          <div className="flex items-center gap-4">
            {PRIMARY_SECTIONS.map((tab) => {
              const active = pathnameMatchesSection(pathname, tab);

              return (
                <Link
                  key={tab.href}
                  aria-current={active ? "page" : undefined}
                  className={`rounded-full px-5 py-2.5 text-center text-sm font-medium transition ${
                    active
                      ? "bg-ink-primary text-white shadow-paper"
                      : "text-ink-muted hover:bg-ink-low hover:text-ink-text"
                  }`}
                  href={tab.href}
                >
                  {tab.label}
                </Link>
              );
            })}
          </div>
        </nav>
      </div>

      <div className="flex items-center justify-between gap-6 px-6 py-3 lg:px-8">
        <div className="min-w-0">
          <h1 className="font-headline text-xl font-extrabold tracking-tight text-ink-text">{title}</h1>
          {subtitle ? <p className="mt-1 text-sm text-ink-muted line-clamp-1">{subtitle}</p> : null}
        </div>
      </div>
    </header>
  );
}
