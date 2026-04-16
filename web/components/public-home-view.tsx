import { PublicArticleListItem } from "@/components/public/public-article-list-item";
import { ResearchTopicCard } from "@/components/public/research-topic-card";
import { EmptyState } from "@/components/ui/empty-state";
import { getPublicHomeData } from "@/lib/public";

export async function PublicHomeView() {
  const { authorProfile, articles, projects, researchTopics } = await getPublicHomeData();
  const articleBySlug = new Map(articles.map((article) => [article.slug, article]));
  const contactLinks = authorProfile.contactLinks ?? [];

  return (
    <main className="mx-auto max-w-[76rem] px-6 py-16 md:px-10">
      <header className="grid gap-8 border-b public-soft-rule pb-14 lg:grid-cols-[minmax(0,1.2fr)_320px]">
        <div>
          <div className="public-eyebrow">作者</div>
          <div className="mt-6 max-w-4xl">
            <div className="text-sm uppercase tracking-[0.22em] text-ink-muted">{authorProfile.name}</div>
            <h1 className="mt-4 font-headline text-5xl font-extrabold tracking-tight text-ink-text md:text-6xl">
              {authorProfile.title}
            </h1>
            <p className="mt-6 max-w-3xl font-body text-[1.32rem] leading-[1.85] text-[#2e3536]">{authorProfile.summary}</p>
            <p className="mt-6 max-w-3xl text-[1.02rem] leading-8 text-ink-muted">
              {authorProfile.researchStatement ?? authorProfile.intro}
            </p>
          </div>
        </div>

        <div className="public-panel p-7">
          <div className="public-eyebrow">工作方法</div>
          <p className="mt-4 text-[1.02rem] leading-8 text-ink-text">{authorProfile.manifesto}</p>
          <p className="mt-5 border-l-2 border-ink-primary/25 pl-4 text-sm leading-7 text-ink-muted">
            {authorProfile.workingNote ?? authorProfile.intro}
          </p>
          <div className="mt-6 border-t public-soft-rule pt-4 text-sm leading-7 text-ink-muted">
            <span className="font-semibold text-ink-text">长期线索</span>
            <span className="ml-2">{authorProfile.focusAreas.join(" · ")}</span>
          </div>
        </div>
      </header>

      <section className="mt-14">
        <div className="max-w-3xl">
          <div className="public-eyebrow">研究主题</div>
          <h2 className="mt-4 font-headline text-4xl font-extrabold tracking-tight text-ink-text">我长期在追的问题</h2>
          <p className="mt-4 text-[1.02rem] leading-8 text-ink-muted">
            这些主题并不是栏目，而是我持续几年都在反复返回的工作现场。每个入口都会连向一组更完整的文章、项目和方法背景。
          </p>
        </div>

        {researchTopics.length > 0 ? (
          <div className="mt-8 grid gap-5 lg:grid-cols-3">
            {researchTopics.map((topic) => (
              <ResearchTopicCard key={topic.slug} topic={topic} featuredArticle={articleBySlug.get(topic.featuredArticleSlug)} />
            ))}
          </div>
        ) : (
          <div className="mt-8">
            <EmptyState
              eyebrow="研究主题"
              title="研究主题还没有整理出来"
              description="等长期主题被策展成公开索引后，这里会成为进入整站内容的第一张地图。"
            />
          </div>
        )}
      </section>

      <section className="mt-16 grid gap-10 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div>
          <div className="public-eyebrow">最近文章</div>
          <h2 className="mt-4 font-headline text-4xl font-extrabold tracking-tight text-ink-text">最近公开整理出来的判断</h2>
          <p className="mt-4 max-w-3xl text-[1.02rem] leading-8 text-ink-muted">
            这些文章来自长期工作后的整理结果。它们更像阶段性结论，而不是为了维持更新频率而写的内容。
          </p>

          {articles.length > 0 ? (
            <div className="mt-8 space-y-4">
              {articles.map((article) => (
                <PublicArticleListItem key={article.id} article={article} />
              ))}
            </div>
          ) : (
            <div className="mt-8">
              <EmptyState
                eyebrow="最近文章"
                title="还没有公开文章"
                description="等知识资产成熟并发布出去后，这里会形成一条稳定的公开阅读流。"
              />
            </div>
          )}
        </div>

        <aside className="space-y-6">
          <div className="public-panel p-6">
            <div className="public-eyebrow">方法背景</div>
            <h2 className="mt-4 font-headline text-2xl font-extrabold tracking-tight text-ink-text">这些写作背后的工作系统</h2>
            <p className="mt-4 text-sm leading-7 text-ink-muted">
              Inkdesk 在公开侧不是主角，它更像我长期工作的底层方法与环境。下面这些项目说明了这套方法如何被持续搭建和使用。
            </p>
            <div className="mt-5 space-y-3">
              {projects.map((project) => (
                <a key={project.name} href={project.href} className="block rounded-[22px] border border-black/5 bg-white/70 px-4 py-4">
                  <div className="public-eyebrow">{project.kind}</div>
                  <div className="mt-2 font-headline text-xl font-bold tracking-tight text-ink-text">{project.name}</div>
                  <p className="mt-3 text-sm leading-7 text-ink-muted">{project.description}</p>
                </a>
              ))}
            </div>
          </div>

          <div className="public-panel p-6">
            <div className="public-eyebrow">保持联系</div>
            <p className="mt-4 text-sm leading-7 text-ink-muted">
              如果你也在长期搭建自己的研究、写作或工作系统，这里保留几个足够低打扰的入口。
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
