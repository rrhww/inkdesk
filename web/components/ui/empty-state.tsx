import Link from "next/link";

import { PanelCard } from "@/components/ui/panel-card";

type EmptyStateProps = {
  eyebrow: string;
  title: string;
  description: string;
  actionLabel?: string;
  href?: string;
};

export function EmptyState({ eyebrow, title, description, actionLabel, href }: EmptyStateProps) {
  return (
    <PanelCard className="p-8">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{eyebrow}</div>
      <h3 className="mt-4 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{title}</h3>
      <p className="mt-4 max-w-2xl text-sm leading-7 text-ink-muted">{description}</p>
      {actionLabel && href ? (
        <Link href={href} className="mt-6 inline-flex rounded-sm bg-ink-primary px-4 py-3 text-sm font-semibold text-white">
          {actionLabel}
        </Link>
      ) : null}
    </PanelCard>
  );
}
