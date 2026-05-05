import Link from "next/link";

import type { PublicArticleSummary } from "@/lib/types";

type PublicArticleListItemProps = {
  article: PublicArticleSummary;
  indexLabel?: string;
};

export function PublicArticleListItem({ article, indexLabel }: PublicArticleListItemProps) {
  return (
    <Link href={`/articles/${article.slug}`} className="public-list-item block">
      <div className={indexLabel ? "grid gap-5 md:grid-cols-[72px_minmax(0,1fr)] md:items-start" : ""}>
        {indexLabel ? (
          <div className="border-b border-black/5 pb-3 text-left md:border-b-0 md:border-r md:pb-0 md:pr-4">
            <div className="font-headline text-3xl font-extrabold tracking-tight text-ink-primary/75">{indexLabel}</div>
          </div>
        ) : null}
        <div>
          <div className="flex flex-wrap items-center gap-3 text-sm text-ink-muted">
            <span>{article.updatedAt}</span>
            <span>{article.readingMinutes} 分钟阅读</span>
            <span>{article.folder}</span>
          </div>
          <h3 className="mt-4 font-headline text-2xl font-bold tracking-tight text-ink-text">{article.title}</h3>
          <p className="mt-3 max-w-3xl text-[1.02rem] leading-8 text-ink-muted">{article.excerpt}</p>
        </div>
      </div>
    </Link>
  );
}
