import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { PublicArticleListItem } from "@/components/public/public-article-list-item";
import { getPublicProjectBySlug, getPublicProjectParams } from "@/lib/public";

type ProjectPageProps = {
  params: Promise<{
    slug: string;
  }>;
};

export async function generateStaticParams() {
  return getPublicProjectParams();
}

export async function generateMetadata({ params }: ProjectPageProps): Promise<Metadata> {
  const { slug } = await params;
  const project = await getPublicProjectBySlug(slug);

  if (!project) {
    return {
      title: "项目不存在 | Inkdesk"
    };
  }

  return {
    title: `${project.title} | Inkdesk Projects`,
    description: project.summary,
    alternates: {
      canonical: `/projects/${slug}`
    },
    openGraph: {
      title: `${project.title} | Inkdesk Projects`,
      description: project.summary,
      type: "website"
    }
  };
}

export default async function ProjectPage({ params }: ProjectPageProps) {
  const { slug } = await params;
  const project = await getPublicProjectBySlug(slug);

  if (!project) {
    notFound();
  }

  return (
    <main className="mx-auto max-w-[78rem] px-6 py-16 md:px-10">
      <div className="mb-8">
        <Link href="/" className="text-sm text-ink-primary">
          返回公开输出
        </Link>
      </div>

      <header className="grid gap-8 border-b public-soft-rule pb-12 lg:grid-cols-[minmax(0,1.1fr)_320px]">
        <div>
          <div className="public-section-label">项目</div>
          <h1 className="mt-5 font-headline text-5xl font-extrabold tracking-tight text-ink-text md:text-6xl">{project.title}</h1>
          <p className="mt-6 max-w-3xl font-body text-[1.22rem] leading-[1.85] text-[#2e3536]">{project.summary}</p>
        </div>

        <aside className="space-y-4">
          <div className="public-panel p-6">
            <div className="public-section-label">当前阶段</div>
            <p className="mt-4 text-[1.02rem] leading-8 text-ink-text">{project.statusLabel}</p>
            <p className="mt-4 text-sm leading-7 text-ink-muted">{project.updatedAt}</p>
          </div>
          <div className="public-panel p-6">
            <div className="public-section-label">技术栈</div>
            <div className="mt-5 flex flex-wrap gap-2">
              {project.stack.map((entry) => (
                <span key={entry} className="public-chip">
                  {entry}
                </span>
              ))}
            </div>
          </div>
        </aside>
      </header>

      <section className="mt-14 grid gap-10 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-8">
          <section>
            <div className="public-section-label">亮点与方法</div>
            <div className="mt-5 grid gap-4 md:grid-cols-3">
              {project.highlights.map((entry) => (
                <div key={entry} className="rounded-[24px] border border-black/5 bg-white/70 px-5 py-5 text-sm leading-7 text-ink-muted">
                  {entry}
                </div>
              ))}
            </div>
          </section>

          <section>
            <div className="public-section-label">相关笔记</div>
            <div className="mt-5 space-y-4">
              {project.relatedArticles.map((article, index) => (
                <PublicArticleListItem key={article.id} article={article} indexLabel={String(index + 1).padStart(2, "0")} />
              ))}
            </div>
          </section>
        </div>

        <aside className="space-y-6">
          <section className="public-panel p-6">
            <div className="public-section-label">相关分类</div>
            <div className="mt-5 space-y-3">
              {project.relatedBuckets.map((bucket) => (
                <Link key={bucket.slug} href={`/topics/${bucket.slug}`} className="block rounded-[22px] border border-black/5 bg-white/70 px-4 py-4">
                  <div className="public-eyebrow">知识分类</div>
                  <div className="mt-2 font-headline text-2xl font-bold tracking-tight text-ink-text">{bucket.title}</div>
                  <p className="mt-3 text-sm leading-7 text-ink-muted">{bucket.summary}</p>
                </Link>
              ))}
            </div>
          </section>

          <section className="public-panel p-6">
            <div className="public-section-label">项目链接</div>
            <div className="mt-5 space-y-3">
              <a href={project.primaryHref} className="flex items-center justify-between rounded-[20px] border border-black/5 bg-white/70 px-4 py-3 text-sm text-ink-text">
                <span>项目入口</span>
                <span className="text-ink-muted">打开</span>
              </a>
              {project.repoHref ? (
                <a href={project.repoHref} className="flex items-center justify-between rounded-[20px] border border-black/5 bg-white/70 px-4 py-3 text-sm text-ink-text">
                  <span>代码仓库</span>
                  <span className="text-ink-muted">打开</span>
                </a>
              ) : null}
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
