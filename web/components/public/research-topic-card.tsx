import Link from "next/link";

import type { PublicArticleSummary, PublicResearchTopic } from "@/lib/types";

type ResearchTopicCardProps = {
  topic: PublicResearchTopic;
  featuredArticle?: PublicArticleSummary;
};

export function ResearchTopicCard({ topic, featuredArticle }: ResearchTopicCardProps) {
  return (
    <Link href={`/research/${topic.slug}`} className="research-card block">
      <div className="public-eyebrow">研究主题</div>
      <h3 className="mt-4 font-headline text-2xl font-bold tracking-tight text-ink-text">{topic.title}</h3>
      <p className="mt-3 text-[1.02rem] leading-8 text-ink-muted">{topic.summary}</p>
      {featuredArticle ? (
        <div className="mt-6 border-t border-black/5 pt-4 text-sm text-ink-muted">
          <span className="font-semibold text-ink-text">代表文章</span>
          <span className="ml-2">{featuredArticle.title}</span>
        </div>
      ) : null}
    </Link>
  );
}
