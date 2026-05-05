import { KnowledgeBucketCard } from "@/components/public/knowledge-bucket-card";
import { PublicProjectCard } from "@/components/public/public-project-card";
import { PublicUpdateListItem } from "@/components/public/public-update-list-item";
import { EmptyState } from "@/components/ui/empty-state";
import { getPublicHomeData } from "@/lib/public";

export async function PublicHomeView() {
  const { authorProfile, knowledgeBuckets, featuredProjects, recentUpdates, articles, contactLinks } = await getPublicHomeData();
  const articleBySlug = new Map(articles.map((article) => [article.slug, article]));
  const featuredProject = featuredProjects[0];
  const secondaryProjects = featuredProjects.slice(1);

  return (
    <main className="mx-auto max-w-[78rem] px-6 py-16 md:px-10">
      <header className="border-b public-soft-rule pb-16">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,1.1fr)_320px]">
          <div className="max-w-4xl">
            <div className="public-section-label">作者陈述</div>
            <div className="mt-7 text-sm uppercase tracking-[0.24em] text-ink-muted">{authorProfile.name}</div>
            <h1 className="mt-4 font-headline text-5xl font-extrabold tracking-tight text-ink-text md:text-6xl">{authorProfile.title}</h1>
            <p className="mt-6 max-w-3xl font-body text-[1.24rem] leading-[1.85] text-[#2e3536]">{authorProfile.summary}</p>
            <p className="mt-6 max-w-3xl text-[1.02rem] leading-8 text-ink-muted">{authorProfile.intro}</p>
          </div>

          <div className="space-y-4">
            <div className="public-panel p-7">
              <div className="public-section-label">当前方法</div>
              <p className="mt-4 text-[1.02rem] leading-8 text-ink-text">{authorProfile.manifesto}</p>
              <p className="mt-5 border-l-2 border-ink-primary/25 pl-4 text-sm leading-7 text-ink-muted">{authorProfile.workingNote}</p>
            </div>
            <div className="public-panel p-7">
              <div className="public-section-label">长期索引</div>
              <div className="mt-4 flex flex-wrap gap-2">
                {authorProfile.focusAreas.map((entry) => (
                  <span key={entry} className="public-chip">
                    {entry}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </header>

      <section className="mt-16">
        <div className="max-w-3xl">
          <div className="public-section-label">01 知识导航</div>
          <h2 className="mt-4 font-headline text-4xl font-extrabold tracking-tight text-ink-text">按主题浏览我的开发学习笔记</h2>
          <p className="mt-4 text-[1.02rem] leading-8 text-ink-muted">
            这里先给你一张大的内容地图。每个入口都不是静态栏目，而是一组会继续生长的学习笔记、代表文章和相关项目。
          </p>
        </div>

        <div className="mt-8 grid gap-5 lg:grid-cols-2">
          {knowledgeBuckets.map((bucket, index) => (
            <KnowledgeBucketCard
              key={bucket.slug}
              bucket={bucket}
              featuredArticle={articleBySlug.get(bucket.featuredArticleSlug)}
              indexLabel={String(index + 1).padStart(2, "0")}
            />
          ))}
        </div>
      </section>

      <section className="mt-16">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1.2fr)_360px]">
          <div>
            <div className="public-section-label">02 精选项目</div>
            <h2 className="mt-4 font-headline text-4xl font-extrabold tracking-tight text-ink-text">项目不是陈列品，而是公开工作现场</h2>
            <p className="mt-4 max-w-3xl text-[1.02rem] leading-8 text-ink-muted">
              我会把最值得被看到的项目放在前面，同时保留少量在建状态，让人能看到它们为什么存在、现在推进到哪里。
            </p>

            {featuredProject ? (
              <div className="mt-8">
                <PublicProjectCard project={featuredProject} featured />
              </div>
            ) : (
              <div className="mt-8">
                <EmptyState eyebrow="精选项目" title="项目还在整理中" description="等第一批项目卡片整理好后，这里会成为公开展示层里最重要的现场之一。" />
              </div>
            )}
          </div>

          <aside className="space-y-4">
            <div className="public-panel p-6">
              <div className="public-section-label">在建状态</div>
              <div className="mt-5 space-y-4">
                {secondaryProjects.map((project) => (
                  <PublicProjectCard key={project.slug} project={project} />
                ))}
              </div>
            </div>
          </aside>
        </div>
      </section>

      <section className="mt-16 grid gap-10 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div>
          <div className="public-section-label">03 最近更新</div>
          <h2 className="mt-4 font-headline text-4xl font-extrabold tracking-tight text-ink-text">最近更新</h2>
          <p className="mt-4 max-w-3xl text-[1.02rem] leading-8 text-ink-muted">
            这里混合展示新文章和项目更新，让整个公开侧看起来更像持续构建中的知识站，而不是一条单调的时间流。
          </p>
          <div className="mt-8 space-y-4">
            {recentUpdates.map((item, index) => (
              <PublicUpdateListItem key={item.id} item={item} indexLabel={String(index + 1).padStart(2, "0")} />
            ))}
          </div>
        </div>

        <aside className="space-y-6">
          <div className="editorial-quote">
            <div className="public-section-label">旁注</div>
            <blockquote className="mt-5">“展示页真正留住人的，往往不是热闹，而是内容之间是否会互相指路。”</blockquote>
            <cite>这也是我这次重做公开侧时最在意的一条标准。</cite>
          </div>

          <div className="public-panel p-6">
            <div className="public-section-label">04 保持联系</div>
            <p className="mt-4 text-sm leading-7 text-ink-muted">
              如果你也在做项目、记笔记或整理自己的方法体系，这里保留几个足够克制的入口。
            </p>
            <div className="mt-5 space-y-3">
              {contactLinks.map((link) => (
                <a key={link.label} href={link.href} className="flex items-center justify-between rounded-[20px] border border-black/5 bg-white/70 px-4 py-3 text-sm text-ink-text">
                  <span>{link.label}</span>
                  <span className="text-ink-muted">打开</span>
                </a>
              ))}
            </div>
          </div>
        </aside>
      </section>
    </main>
  );
}
