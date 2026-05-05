import Link from "next/link";

import type { PublicUpdateItem } from "@/lib/types";

type PublicUpdateListItemProps = {
  item: PublicUpdateItem;
  indexLabel?: string;
};

export function PublicUpdateListItem({ item, indexLabel }: PublicUpdateListItemProps) {
  return (
    <Link href={item.href} className="update-list-item block">
      <div className="grid gap-5 md:grid-cols-[72px_minmax(0,1fr)]">
        <div className="border-b border-black/5 pb-3 md:border-b-0 md:border-r md:pb-0 md:pr-4">
          <div className="font-headline text-3xl font-extrabold tracking-tight text-ink-primary/75">{indexLabel ?? "00"}</div>
        </div>
        <div>
          <div className="flex flex-wrap items-center gap-3 text-sm text-ink-muted">
            <span>{item.label}</span>
            <span>{item.updatedAt}</span>
          </div>
          <h3 className="mt-4 font-headline text-2xl font-bold tracking-tight text-ink-text">{item.title}</h3>
          <p className="mt-3 max-w-3xl text-[1.02rem] leading-8 text-ink-muted">{item.summary}</p>
        </div>
      </div>
    </Link>
  );
}
