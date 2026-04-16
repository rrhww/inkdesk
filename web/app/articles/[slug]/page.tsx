import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { PanelCard } from "@/components/ui/panel-card";
import { SectionHeading } from "@/components/ui/section-heading";
import { getOtherPublicArticleSummaries, getPublicArticleBySlug, getPublicArticleParams, getPublicResearchTopicsForArticleSlug } from "@/lib/public";

type ArticlePageProps = {
  params: Promise<{
    slug: string;
  }>;
};

export async function generateStaticParams() {
  return getPublicArticleParams();
}

export async function generateMetadata({ params }: ArticlePageProps): Promise<Metadata> {
  const { slug } = await params;
  const article = await getPublicArticleBySlug(slug);

  if (!article) {
    return {
      title: "文章不存在 | Inkdesk"
    };
  }

  return {
    title: `${article.title} | Inkdesk`,
    description: article.excerpt,
    alternates: {
      canonical: `/articles/${slug}`
    },
    openGraph: {
      title: article.title,
      description: article.excerpt,
      type: "article"
    }
  };
}

export default async function ArticlePage({ params }: ArticlePageProps) {
  const { slug } = await params;
  const article = await getPublicArticleBySlug(slug);

  if (!article) {
    notFound();
  }

  const otherArticles = await getOtherPublicArticleSummaries(slug);
  const relatedTopics = await getPublicResearchTopicsForArticleSlug(slug);

  return (
    <main className="mx-auto max-w-reading px-6 py-14 md:px-0">
      <div className="mb-8">
        <Link href="/" className="text-sm text-ink-primary">
          返回公开输出
        </Link>
      </div>

      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">公开文章</div>
      <div className="mt-3 text-sm text-ink-muted">{article.folder}</div>
      <h1 className="mt-5 font-headline text-5xl font-extrabold tracking-tight text-ink-text md:text-6xl">{article.title}</h1>
      <div className="mt-6 flex flex-wrap gap-4 text-sm text-ink-muted">
        <span>{article.updatedAt}</span>
        <span>{article.readingMinutes} 分钟阅读</span>
      </div>
      {article.excerpt ? <p className="mt-6 max-w-3xl text-lg leading-8 text-ink-text/80">{article.excerpt}</p> : null}
      <p className="mt-6 max-w-3xl text-sm leading-7 text-ink-muted">{article.provenance}</p>
      <div className="mt-6 flex flex-wrap gap-2">
        {article.tags.map((tag) => (
          <span key={tag} className="rounded-full bg-ink-low px-4 py-2 text-sm text-ink-muted">
            {tag}
          </span>
        ))}
      </div>

      <article className="reading-prose mt-12 space-y-8 font-body">
        {article.body.map((paragraph, index) =>
          index === 1 ? <blockquote key={paragraph}>{paragraph}</blockquote> : <p key={paragraph}>{paragraph}</p>
        )}
      </article>

      <section className="mt-16 grid gap-6 border-t border-black/5 pt-8 md:grid-cols-[minmax(0,1fr)_320px]">
        <div>
          <SectionHeading
            eyebrow="继续探索此研究方向"
            title={relatedTopics[0]?.title ?? "继续探索相关研究主题"}
            description={relatedTopics[0]?.summary ?? "这篇文章属于正在持续整理中的长期研究脉络，你可以继续沿着主题页查看相关写作与项目背景。"}
          />
          {relatedTopics.length > 0 ? (
            <div className="mt-5 space-y-3">
              {relatedTopics.map((topic) => (
                <Link key={topic.slug} href={`/research/${topic.slug}`} className="block rounded-[22px] border border-black/5 bg-white/70 px-5 py-4">
                  <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">研究主题</div>
                  <div className="mt-2 font-headline text-xl font-bold tracking-tight text-ink-text">{topic.title}</div>
                  <p className="mt-3 text-sm leading-7 text-ink-muted">{topic.purpose}</p>
                </Link>
              ))}
            </div>
          ) : null}
        </div>

        <PanelCard className="p-6">
          <SectionHeading eyebrow="继续阅读" title="继续阅读" />
          <div className="mt-4 space-y-4">
            {otherArticles.map((item) => (
              <Link key={item.id} href={`/articles/${item.slug}`} className="block rounded-[20px] bg-ink-low px-4 py-4">
                <div className="font-headline text-lg font-bold tracking-tight text-ink-text">{item.title}</div>
                <div className="mt-2 text-sm text-ink-muted">{item.updatedAt}</div>
              </Link>
            ))}
          </div>
        </PanelCard>
      </section>
    </main>
  );
}
