import Link from "next/link";

import type { PublicArticleSummary, PublicKnowledgeBucket } from "@/lib/types";

type KnowledgeBucketCardProps = {
  bucket: PublicKnowledgeBucket;
  featuredArticle?: PublicArticleSummary;
  indexLabel?: string;
  compact?: boolean;
};

export function KnowledgeBucketCard({ bucket, featuredArticle, indexLabel, compact = false }: KnowledgeBucketCardProps) {
  return (
    <Link href={`/topics/${bucket.slug}`} className={`bucket-card block ${compact ? "bucket-card-compact" : ""}`.trim()}>
      <div className="flex items-start justify-between gap-4">
        <div className="public-eyebrow">知识分类</div>
        {indexLabel ? <div className="font-headline text-xl font-extrabold tracking-tight text-ink-primary/75">{indexLabel}</div> : null}
      </div>
      <h3 className={`font-headline font-bold tracking-tight text-ink-text ${compact ? "mt-3 text-2xl" : "mt-4 text-3xl"}`}>{bucket.title}</h3>
      <p className={`text-ink-muted ${compact ? "mt-2 text-sm leading-7" : "mt-3 text-[1.02rem] leading-8"}`}>{bucket.summary}</p>
      <div className={`flex flex-wrap gap-2 ${compact ? "mt-4" : "mt-5"}`}>
        {bucket.subtopics.map((entry) => (
          <span key={entry} className="public-chip">
            {entry}
          </span>
        ))}
      </div>
      {featuredArticle ? (
        <div className="mt-6 border-t border-black/5 pt-4 text-sm leading-7 text-ink-muted">
          <span className="font-semibold text-ink-text">代表文章</span>
          <span className="ml-2">{featuredArticle.title}</span>
        </div>
      ) : null}
    </Link>
  );
}
