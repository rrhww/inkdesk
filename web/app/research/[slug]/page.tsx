import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { PublicArticleListItem } from "@/components/public/public-article-list-item";
import { ResearchTopicCard } from "@/components/public/research-topic-card";
import { getPublicResearchParams, getPublicResearchTopicBySlug, getPublicResearchTopics } from "@/lib/public";

type ResearchPageProps = {
  params: Promise<{
    slug: string;
  }>;
};

export async function generateStaticParams() {
  return getPublicResearchParams();
}

export async function generateMetadata({ params }: ResearchPageProps): Promise<Metadata> {
  const { slug } = await params;
  const topic = await getPublicResearchTopicBySlug(slug);

  if (!topic) {
    return {
      title: "研究主题不存在 | Inkdesk"
    };
  }

  return {
    title: `${topic.title} | Inkdesk Research`,
    description: topic.summary,
    alternates: {
      canonical: `/research/${slug}`
    },
    openGraph: {
      title: `${topic.title} | Inkdesk Research`,
      description: topic.summary,
      type: "website"
    }
  };
}

export default async function ResearchTopicPage({ params }: ResearchPageProps) {
  const { slug } = await params;
  const topic = await getPublicResearchTopicBySlug(slug);

  if (!topic) {
    notFound();
  }

  const otherTopics = (await getPublicResearchTopics()).filter((entry) => entry.slug !== slug);

  return (
    <main className="mx-auto max-w-[76rem] px-6 py-16 md:px-10">
      <div className="mb-8">
        <Link href="/" className="text-sm text-ink-primary">
          返回作者首页
        </Link>
      </div>

      <header className="grid gap-8 border-b public-soft-rule pb-12 lg:grid-cols-[minmax(0,1.12fr)_320px]">
        <div>
          <div className="public-eyebrow">研究主题</div>
          <h1 className="mt-5 font-headline text-5xl font-extrabold tracking-tight text-ink-text md:text-6xl">{topic.title}</h1>
          <p className="mt-6 max-w-3xl font-body text-[1.25rem] leading-[1.85] text-[#2e3536]">{topic.summary}</p>
        </div>

        <div className="public-panel p-6">
          <div className="public-eyebrow">为什么重要</div>
          <p className="mt-4 text-[1.02rem] leading-8 text-ink-muted">{topic.purpose}</p>
        </div>
      </header>

      <section className="mt-14 grid gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-8">
          {topic.featuredArticle ? (
            <section>
              <div className="public-eyebrow">代表文章</div>
              <div className="mt-5">
                <PublicArticleListItem article={topic.featuredArticle} />
              </div>
            </section>
          ) : null}

          <section>
            <div className="public-eyebrow">相关文章</div>
            {topic.relatedArticles.length > 0 ? (
              <div className="mt-5 space-y-4">
                {topic.relatedArticles.map((article) => (
                  <PublicArticleListItem key={article.id} article={article} />
                ))}
              </div>
            ) : (
              <div className="mt-5 rounded-[24px] border border-black/5 bg-white/65 px-6 py-5 text-sm leading-7 text-ink-muted">
                这个主题的公开写作还在继续整理，后续会补充更多相关文章。
              </div>
            )}
          </section>
        </div>

        <aside className="space-y-6">
          <section className="public-panel p-6">
            <div className="public-eyebrow">相关项目</div>
            <div className="mt-5 space-y-3">
              {topic.relatedProjects.map((project) => (
                <a key={project.name} href={project.href} className="block rounded-[22px] border border-black/5 bg-white/70 px-4 py-4">
                  <div className="public-eyebrow">{project.kind}</div>
                  <div className="mt-2 font-headline text-xl font-bold tracking-tight text-ink-text">{project.name}</div>
                  <p className="mt-3 text-sm leading-7 text-ink-muted">{project.description}</p>
                </a>
              ))}
            </div>
          </section>

          <section className="public-panel p-6">
            <div className="public-eyebrow">其他研究主题</div>
            <div className="mt-5 space-y-3">
              {otherTopics.map((entry) => (
                <ResearchTopicCard key={entry.slug} topic={entry} />
              ))}
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
