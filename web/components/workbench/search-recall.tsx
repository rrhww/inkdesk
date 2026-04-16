import Link from "next/link";

import { PanelCard } from "@/components/ui/panel-card";
import { SectionHeading } from "@/components/ui/section-heading";
import { StatusPill } from "@/components/ui/status-pill";
import type { SearchResult } from "@/lib/types";

type SearchRecallProps = {
  query: string;
  visibility: string;
  tag?: string;
  folder?: string;
  results: SearchResult[];
  recommendedTerms: string[];
  recentKnowledge: Array<{
    id: string;
    title: string;
    updatedAt: string;
    published: boolean;
  }>;
  folders: string[];
  tags: string[];
};

export function SearchRecall({
  query,
  visibility,
  tag,
  folder,
  results,
  recommendedTerms,
  recentKnowledge,
  folders,
  tags
}: SearchRecallProps) {
  const showEmpty = !query;
  const showNoResults = Boolean(query) && results.length === 0;
  const exampleSearches = ["Agent", "超级个人工作台", "发布分享"];
  const recentSearches = ["Agent", "公开输出", "定位"];

  return (
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      <section className="paper-card p-8">
        <SectionHeading eyebrow="全局检索 / 知识召回" title="让过去的判断重新回到当前工作流" description="检索在这里不是查找文件，而是给 Agent 和你自己重新补上下文。" />
        <form className="mt-6 grid gap-3 xl:grid-cols-[minmax(0,1fr)_180px_180px_180px]">
          <input className="w-full rounded-sm bg-ink-low px-5 py-4 font-headline text-2xl font-medium focus:ring-2 focus:ring-ink-primary/20" defaultValue={query} name="q" placeholder="输入关键词，重新召回你的上下文..." />
          <select className="rounded-sm bg-ink-low px-4 py-4 text-sm text-ink-text" defaultValue={visibility} name="visibility">
            <option value="all">全部可见范围</option>
            <option value="private">仅主系统</option>
            <option value="public">已发布</option>
          </select>
          <select className="rounded-sm bg-ink-low px-4 py-4 text-sm text-ink-text" defaultValue={folder ?? ""} name="folder">
            <option value="">全部分区</option>
            {folders.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <select className="rounded-sm bg-ink-low px-4 py-4 text-sm text-ink-text" defaultValue={tag ?? ""} name="tag">
            <option value="">全部标签</option>
            {tags.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </form>

        {showEmpty ? (
          <div className="mt-10 grid gap-8 xl:grid-cols-[minmax(0,1fr)_320px_280px]">
            <PanelCard className="bg-ink-low/70 p-8">
              <SectionHeading eyebrow="示例搜索" title="把过去的笔记重新带回当下" description="可以通过标题、摘要、标签和分区迅速回到过去的判断现场。" />
              <div className="mt-6 flex flex-wrap gap-2">
                {exampleSearches.map((term) => (
                  <Link key={term} href={`/app/search?q=${encodeURIComponent(term)}`} className="rounded-full bg-white px-4 py-2 text-sm text-ink-muted shadow-paper">
                    {term}
                  </Link>
                ))}
              </div>
            </PanelCard>

            <PanelCard className="p-6">
              <SectionHeading eyebrow="推荐召回" title="先回到稳定上下文" />
              <div className="mt-4 space-y-3">
                {recommendedTerms.slice(0, 4).map((term) => (
                  <Link key={term} href={`/app/search?q=${encodeURIComponent(term)}`} className="block rounded-[20px] bg-ink-low px-4 py-4 text-sm text-ink-muted">
                    {term}
                  </Link>
                ))}
              </div>
            </PanelCard>

            <div className="space-y-6">
              <PanelCard className="p-6">
                <SectionHeading eyebrow="最近搜索" title="最近搜索" />
                <div className="mt-4 flex flex-wrap gap-2">
                  {recentSearches.map((term) => (
                    <Link key={term} href={`/app/search?q=${encodeURIComponent(term)}`} className="rounded-full bg-ink-low px-4 py-2 text-sm text-ink-muted">
                      {term}
                    </Link>
                  ))}
                </div>
              </PanelCard>

              <PanelCard className="p-6">
                <SectionHeading eyebrow="近期知识" title="近期知识" />
                <div className="mt-4 space-y-4">
                  {recentKnowledge.map((note) => (
                    <Link key={note.id} href={`/app/notes/${note.id}${note.published ? "?state=published" : ""}`} className="block rounded-[20px] bg-ink-low px-4 py-4">
                      <div className="font-headline text-lg font-bold tracking-tight text-ink-text">{note.title}</div>
                      <div className="mt-2 text-sm text-ink-muted">{note.updatedAt}</div>
                    </Link>
                  ))}
                </div>
              </PanelCard>
            </div>
          </div>
        ) : showNoResults ? (
          <div className="mt-10 grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
            <div className="rounded-[28px] bg-ink-low px-6 py-8">
              <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">没有结果</div>
              <h2 className="mt-4 font-headline text-3xl font-extrabold tracking-tight text-ink-text">当前没有召回到相关上下文</h2>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-ink-muted">可以换一个关键词，或者从推荐召回里先回到最近更稳定的知识资产。</p>
            </div>
            <PanelCard className="p-6">
              <SectionHeading eyebrow="推荐召回" title="回到近处" />
              <div className="mt-4 space-y-3">
                {recommendedTerms.slice(0, 4).map((term) => (
                  <Link key={term} href={`/app/search?q=${encodeURIComponent(term)}`} className="block rounded-[20px] bg-ink-low px-4 py-4 text-sm text-ink-muted">
                    {term}
                  </Link>
                ))}
              </div>
            </PanelCard>
          </div>
        ) : (
          <div className="mt-10">
            <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="text-sm text-ink-muted">共召回 {results.length} 条结果</div>
              <div className="flex flex-wrap gap-2">
                {visibility !== "all" ? <StatusPill tone="soft">{visibility === "public" ? "已发布" : "仅主系统"}</StatusPill> : null}
                {folder ? <StatusPill>{folder}</StatusPill> : null}
                {tag ? <StatusPill>{tag}</StatusPill> : null}
              </div>
            </div>
            <div className="space-y-4">
              {results.map((result) => (
                <Link key={result.note.id} href={`/app/notes/${result.note.id}${result.note.published ? "?state=published" : ""}`} className="paper-card block px-6 py-6 hover:-translate-y-0.5">
                  <div className="flex flex-wrap items-center gap-3">
                    <StatusPill tone={result.note.visibility === "public" ? "soft" : "neutral"}>{result.note.visibilityLabel}</StatusPill>
                    <span className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{result.note.folder}</span>
                  </div>
                  <h3 className="mt-3 font-headline text-3xl font-bold tracking-tight text-ink-text">{result.note.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-ink-muted">{result.note.excerpt}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {result.note.tags.map((item) => (
                      <span key={item} className="rounded-full bg-ink-low px-3 py-1 text-sm text-ink-muted">
                        {item}
                      </span>
                    ))}
                  </div>
                  <div className="mt-5 flex flex-col gap-2 text-sm md:flex-row md:items-center md:justify-between">
                    <div className="text-ink-muted">命中来源：{result.hitLabels.join(" / ")}</div>
                    <div className="font-semibold text-ink-primary">进入知识资产</div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
