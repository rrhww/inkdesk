import { StatusPill } from "@/components/ui/status-pill";
import type { ResearchSourceRecord } from "@/lib/types";

type SourceCardProps = {
  source: ResearchSourceRecord;
};

export function SourceCard({ source }: SourceCardProps) {
  return (
    <article className="paper-card p-6">
      <div className="flex flex-wrap items-center gap-3">
        <StatusPill>{source.kind}</StatusPill>
        <StatusPill tone="soft">{source.status}</StatusPill>
      </div>
      <h2 className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{source.title}</h2>
      <p className="mt-3 text-sm leading-7 text-ink-muted">{source.excerpt}</p>
      <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2">
        <div className="rounded-[18px] bg-ink-low px-4 py-3">
          <dt className="text-[11px] uppercase tracking-[0.18em] text-ink-muted">locator</dt>
          <dd className="mt-2 break-words text-ink-text">{source.locator || "未记录来源位置"}</dd>
        </div>
        <div className="rounded-[18px] bg-ink-low px-4 py-3">
          <dt className="text-[11px] uppercase tracking-[0.18em] text-ink-muted">vaultPath</dt>
          <dd className="mt-2 break-words text-ink-primary">{source.vaultPath || "等待写入 raw vault"}</dd>
        </div>
      </dl>
    </article>
  );
}
