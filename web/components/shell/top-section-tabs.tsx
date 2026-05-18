"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { PRIMARY_SECTIONS, pathnameMatchesSection } from "@/lib/app-shell";

export function TopSectionTabs() {
  const pathname = usePathname() ?? "/app";

  return (
    <nav aria-label="主分区" className="hide-scrollbar overflow-x-auto">
      <div className="flex min-w-max items-center gap-2 pb-1">
        {PRIMARY_SECTIONS.map((tab) => {
          const active = pathnameMatchesSection(pathname, tab);

          return (
            <Link
              key={tab.href}
              aria-current={active ? "page" : undefined}
              className={`rounded-full border px-4 py-2.5 text-sm font-medium transition ${
                active
                  ? "border-ink-primary bg-ink-primary text-white shadow-paper"
                  : "border-black/10 bg-white/70 text-ink-muted hover:-translate-y-px hover:border-ink-primary/30 hover:bg-white hover:text-ink-text"
              }`}
              href={tab.href}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
