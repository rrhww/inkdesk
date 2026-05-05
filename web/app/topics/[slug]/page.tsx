import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { KnowledgeBucketCard } from "@/components/public/knowledge-bucket-card";
import { PublicArticleListItem } from "@/components/public/public-article-list-item";
import { getPublicKnowledgeBucketBySlug, getPublicKnowledgeBucketParams, getPublicKnowledgeBuckets } from "@/lib/public";

type TopicPageProps = {
  params: Promise<{
    slug: string;
  }>;
};

export async function generateStaticParams() {
  return getPublicKnowledgeBucketParams();
}

export async function generateMetadata({ params }: TopicPageProps): Promise<Metadata> {
  const { slug } = await params;
  const bucket = await getPublicKnowledgeBucketBySlug(slug);

  if (!bucket) {
    return {
      title: "分类不存在 | Inkdesk"
    };
  }

  return {
    title: `${bucket.title} | Inkdesk Topics`,
    description: bucket.summary,
    alternates: {
      canonical: `/topics/${slug}`
    },
    openGraph: {
      title: `${bucket.title} | Inkdesk Topics`,
      description: bucket.summary,
      type: "website"
    }
  };
}

export default async function TopicPage({ params }: TopicPageProps) {
  const { slug } = await params;
  const bucket = await getPublicKnowledgeBucketBySlug(slug);

  if (!bucket) {
    notFound();
  }

  const otherBuckets = (await getPublicKnowledgeBuckets()).filter((entry) => entry.slug !== slug);

  return (
    <main className="mx-auto max-w-[78rem] px-6 py-16 md:px-10">
      <div className="mb-8">
        <Link href="/" className="text-sm text-ink-primary">
          返回公开输出
        </Link>
      </div>

      <header className="grid gap-8 border-b public-soft-rule pb-12 lg:grid-cols-[minmax(0,1.1fr)_320px]">
        <div>
          <div className="public-section-label">分类</div>
          <h1 className="mt-5 font-headline text-5xl font-extrabold tracking-tight text-ink-text md:text-6xl">{bucket.title}</h1>
          <p className="mt-6 max-w-3xl font-body text-[1.22rem] leading-[1.85] text-[#2e3536]">{bucket.summary}</p>
          <p className="mt-6 max-w-3xl text-[1.02rem] leading-8 text-ink-muted">{bucket.intro}</p>
        </div>

        <aside className="space-y-4">
          <div className="public-panel p-6">
            <div className="public-section-label">细分方向</div>
            <div className="mt-5 flex flex-wrap gap-2">
              {bucket.subtopics.map((entry) => (
                <span key={entry} className="public-chip">
                  {entry}
                </span>
              ))}
            </div>
          </div>
          <div className="public-panel p-6">
            <div className="public-section-label">浏览方式</div>
            <p className="mt-4 text-sm leading-7 text-ink-muted">先看代表文章建立上下文，再顺着相关文章和相关项目继续展开，会更容易看到这一类内容是怎样互相连接的。</p>
          </div>
        </aside>
      </header>

      <section className="mt-14 grid gap-10 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-8">
          {bucket.featuredArticle ? (
            <section>
              <div className="public-section-label">代表文章</div>
              <div className="mt-5">
                <PublicArticleListItem article={bucket.featuredArticle} indexLabel="01" />
              </div>
            </section>
          ) : null}

          <section>
            <div className="public-section-label">相关文章</div>
            {bucket.relatedArticles.length > 0 ? (
              <div className="mt-5 space-y-4">
                {bucket.relatedArticles.map((article, index) => (
                  <PublicArticleListItem key={article.id} article={article} indexLabel={String(index + 2).padStart(2, "0")} />
                ))}
              </div>
            ) : (
              <div className="mt-5 rounded-[24px] border border-black/5 bg-white/65 px-6 py-5 text-sm leading-7 text-ink-muted">
                这个分类的公开内容还在继续整理，后面会再补充更多文章与笔记。
              </div>
            )}
          </section>
        </div>

        <aside className="space-y-6">
          <section className="public-panel p-6">
            <div className="public-section-label">相关项目</div>
            <div className="mt-5 space-y-4">
              {bucket.relatedProjects.map((project) => (
                <Link key={project.slug} href={`/projects/${project.slug}`} className="block rounded-[22px] border border-black/5 bg-white/70 px-4 py-4">
                  <div className="public-eyebrow">{project.kind}</div>
                  <div className="mt-2 font-headline text-2xl font-bold tracking-tight text-ink-text">{project.title}</div>
                  <p className="mt-3 text-sm leading-7 text-ink-muted">{project.summary}</p>
                </Link>
              ))}
            </div>
          </section>

          <section className="public-panel p-6">
            <div className="public-section-label">其他分类</div>
            <div className="mt-5 space-y-4">
              {otherBuckets.map((entry, index) => (
                <KnowledgeBucketCard key={entry.slug} bucket={entry} indexLabel={String(index + 2).padStart(2, "0")} compact />
              ))}
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
