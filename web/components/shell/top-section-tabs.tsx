"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { PRIMARY_SECTIONS, pathnameMatchesSection } from "@/lib/app-shell";

export function TopSectionTabs() {
  const pathname = usePathname() ?? "/app";

  return (
    <nav aria-label="主分区" className="overflow-x-auto">
      <div className="flex min-w-max items-center gap-2">
        {PRIMARY_SECTIONS.map((tab) => {
          const active = pathnameMatchesSection(pathname, tab);

          return (
            <Link
              key={tab.href}
              aria-current={active ? "page" : undefined}
              className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                active ? "bg-ink-primary text-white shadow-paper" : "text-ink-muted hover:bg-ink-low hover:text-ink-text"
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
