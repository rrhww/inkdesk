"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const topTabs = [
  { href: "/app", label: "问答", matchers: ["/app", "/app/ask"] },
  { href: "/app/raw", label: "资料", matchers: ["/app/raw", "/app/inbox", "/app/sources"] },
  { href: "/app/ingest", label: "审阅", matchers: ["/app/ingest", "/app/review"] },
  { href: "/app/wiki", label: "知识库", matchers: ["/app/wiki", "/app/topics"] }
];

function matchesPath(pathname: string, matchers: string[]) {
  return matchers.some((matcher) => pathname === matcher || pathname.startsWith(`${matcher}/`));
}

export function TopSectionTabs() {
  const pathname = usePathname() ?? "/app";

  return (
    <nav aria-label="主分区" className="overflow-x-auto">
      <div className="flex min-w-max items-center gap-2">
        {topTabs.map((tab) => {
          const active = matchesPath(pathname, tab.matchers);

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
