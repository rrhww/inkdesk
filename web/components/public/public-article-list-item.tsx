import Link from "next/link";

import type { PublicArticleSummary } from "@/lib/types";

type PublicArticleListItemProps = {
  article: PublicArticleSummary;
};

export function PublicArticleListItem({ article }: PublicArticleListItemProps) {
  return (
    <Link href={`/articles/${article.slug}`} className="public-list-item block">
      <div className="flex flex-wrap items-center gap-3 text-sm text-ink-muted">
        <span>{article.updatedAt}</span>
        <span>{article.readingMinutes} 分钟阅读</span>
        <span>{article.folder}</span>
      </div>
      <h3 className="mt-4 font-headline text-2xl font-bold tracking-tight text-ink-text">{article.title}</h3>
      <p className="mt-3 max-w-3xl text-[1.02rem] leading-8 text-ink-muted">{article.excerpt}</p>
    </Link>
  );
}
