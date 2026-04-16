"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/app", label: "Agent", icon: "smart_toy", matchers: ["/app"] },
  { href: "/app/library", label: "笔记", icon: "book_5", matchers: ["/app/library", "/app/notes"] },
  { href: "/app/plans", label: "任务与计划", icon: "checklist", matchers: ["/app/plans"] },
  { href: "/app/search", label: "检索", icon: "search", matchers: ["/app/search"] },
  { href: "/app/publish", label: "发布", icon: "publish", matchers: ["/app/publish"] }
];

const utilityItems = [
  { href: "/app/tags", label: "标签", icon: "sell", matchers: ["/app/tags"] },
  { href: "/app/settings", label: "设置", icon: "settings", matchers: ["/app/settings"] }
];

function matchesPath(pathname: string, matchers: string[]) {
  return matchers.some((matcher) => pathname === matcher || pathname.startsWith(`${matcher}/`));
}

type NavLinksProps = {
  pathname: string;
  mobile?: boolean;
};

function NavLinks({ pathname, mobile = false }: NavLinksProps) {
  return navItems.map((item) => {
    const active = matchesPath(pathname, item.matchers);

    return (
      <NavItem key={item.href} active={active} href={item.href} icon={item.icon} label={item.label} mobile={mobile} />
    );
  });
}

function NavItem({
  active,
  href,
  icon,
  label,
  mobile = false
}: {
  active: boolean;
  href: string;
  icon: string;
  label: string;
  mobile?: boolean;
}) {
  return (
    <Link
      aria-current={active ? "page" : undefined}
      className={
        mobile
          ? `flex shrink-0 items-center gap-2 rounded-full px-4 py-2 text-sm ${
              active ? "bg-ink-primary text-white shadow-paper" : "bg-white text-ink-muted"
            }`
          : `flex items-center gap-3 rounded-sm px-4 py-3 text-sm transition ${
              active ? "bg-white text-ink-text shadow-paper" : "text-ink-muted hover:bg-white hover:text-ink-text"
            }`
      }
      href={href}
    >
      <span className="material-symbols-outlined text-base">{icon}</span>
      <span className="font-headline font-medium">{label}</span>
    </Link>
  );
}

export function AppSidebarContent({ pathname }: { pathname: string }) {
  return (
    <>
      <div className="sticky top-0 z-30 border-b border-black/5 bg-ink-low/90 px-6 py-4 backdrop-blur lg:hidden">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">主系统导航</div>
        <div className="mt-3 flex gap-2 overflow-x-auto pb-1 hide-scrollbar">
          <NavLinks pathname={pathname} mobile />
        </div>
      </div>

      <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col bg-ink-low px-4 py-8 lg:flex">
        <div className="mb-10 flex items-center gap-3 px-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-sm bg-ink-primary text-white">
            <span className="material-symbols-outlined text-sm">edit_note</span>
          </div>
          <div>
            <div className="font-headline text-lg font-extrabold tracking-tight text-ink-primary">Inkdesk</div>
            <div className="font-headline text-[10px] uppercase tracking-[0.22em] text-ink-muted">超级个人工作台</div>
          </div>
        </div>

        <Link
          className="mb-6 flex items-center justify-center gap-2 rounded-sm bg-ink-primary px-4 py-3 font-headline text-sm font-semibold text-white"
          href="/app/notes/new"
        >
          <span className="material-symbols-outlined text-base">add</span>
          新建资产
        </Link>

        <nav aria-label="主系统导航" className="space-y-1">
          <NavLinks pathname={pathname} />
        </nav>

        <div className="mt-6 border-t border-black/5 pt-6">
          <div className="mb-3 px-4 text-[11px] uppercase tracking-[0.2em] text-ink-muted">扩展模块</div>
          <div className="space-y-1">
            {utilityItems.map((item) => (
              <NavItem
                key={item.href}
                active={matchesPath(pathname, item.matchers)}
                href={item.href}
                icon={item.icon}
                label={item.label}
              />
            ))}
          </div>
        </div>

        <div className="mt-auto border-t border-black/5 pt-6">
          <div className="rounded-[24px] bg-white px-4 py-4 text-sm leading-6 text-ink-muted shadow-paper">
            主系统围绕 Agent、笔记与任务计划协同运转。发布能力保留为面向公开输出的次级模块。
          </div>
        </div>
      </aside>
    </>
  );
}

export function AppSidebar() {
  const pathname = usePathname();

  return <AppSidebarContent pathname={pathname} />;
}
