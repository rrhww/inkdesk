import Link from "next/link";

import { PanelCard } from "@/components/ui/panel-card";
import { SectionHeading } from "@/components/ui/section-heading";
import { StatCard } from "@/components/ui/stat-card";
import { StatusPill } from "@/components/ui/status-pill";
import type { KnowledgeHubData } from "@/lib/types";

type KnowledgeHubProps = {
  data: KnowledgeHubData;
  activeFilter: string;
  activeTag?: string;
};

export function KnowledgeHub({ data, activeFilter, activeTag }: KnowledgeHubProps) {
  const filteredNotes = activeTag ? data.notes.filter((note) => note.tags.includes(activeTag)) : data.notes;

  return (
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      <section className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <SectionHeading
          eyebrow="笔记与知识库"
          title="长期知识资产"
          description="这里保存主系统的事实来源。Agent、任务计划与公开输出都会回到这些知识资产上来获取上下文。"
        />
        <div className="flex gap-3">
          <div className="rounded-sm bg-ink-low px-4 py-3 text-sm font-semibold text-ink-text">已公开 {data.summary.publicNotes} 篇</div>
          <Link href="/app/notes/new" className="rounded-sm bg-ink-primary px-4 py-3 text-sm font-semibold text-white">
            新建笔记
          </Link>
        </div>
      </section>

      <section className="mb-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard detail="全部知识资产" eyebrow="知识摘要" value={data.summary.totalNotes} />
        <StatCard detail="仍在内部整理中的知识" eyebrow="仅主系统" value={data.summary.privateNotes} />
        <StatCard detail="已经对外发布的资产" eyebrow="已发布" value={data.summary.publicNotes} />
        <StatCard detail="正在进入当前工作流的资产" eyebrow="被计划与 Agent 调用" value={data.summary.linkedNotes} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div>
          <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">当前筛选</div>
              <div className="mt-2 font-headline text-2xl font-extrabold tracking-tight text-ink-text">
                {data.filters.find((item) => item.value === activeFilter)?.label ?? "全部"}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {data.filters.map((item) => (
                <Link
                  key={item.value}
                  href={`/app/library?filter=${item.value}`}
                  className={`rounded-full px-4 py-2 text-sm ${
                    item.value === activeFilter ? "bg-ink-primary text-white shadow-paper" : "bg-white text-ink-muted shadow-paper"
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>

          {activeTag ? (
            <div className="mb-5 flex items-center gap-3">
              <StatusPill tone="soft">按主题筛选</StatusPill>
              <span className="text-sm text-ink-muted">{activeTag}</span>
              <Link href={`/app/library?filter=${activeFilter}`} className="text-sm text-ink-primary">
                清除主题筛选
              </Link>
            </div>
          ) : null}

          <div className="space-y-4">
            {filteredNotes.map((note) => (
              <Link key={note.id} href={`/app/notes/${note.id}${note.published ? "?state=published" : ""}`} className="paper-card block px-6 py-6 hover:-translate-y-0.5">
                <div className="flex flex-wrap items-center gap-3">
                  <StatusPill tone={note.visibility === "public" ? "soft" : "neutral"}>{note.visibilityLabel}</StatusPill>
                  <span className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{note.knowledgeStateLabel}</span>
                </div>
                <div className="mt-4 flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                  <div className="max-w-3xl">
                    <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{note.folder}</div>
                    <h3 className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{note.title}</h3>
                    <p className="mt-4 text-sm leading-7 text-ink-muted">{note.excerpt}</p>
                  </div>
                  <div className="text-sm text-ink-muted">{note.updatedAt}</div>
                </div>
                <div className="mt-5 flex flex-wrap items-center gap-2">
                  {note.tags.map((tag) => (
                    <span key={tag} className="rounded-full bg-ink-low px-3 py-1 text-sm text-ink-muted">
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="mt-5 text-sm text-ink-muted">
                  {note.relatedPlanIds.length > 0 ? `关联 ${note.relatedPlanIds.length} 个计划，Agent 会优先召回 ${note.relatedSearchTerms[0]}` : `当前主要用于 ${note.relatedSearchTerms.join(" / ")}`}
                </div>
              </Link>
            ))}
          </div>
        </div>

        <aside className="space-y-6">
          <PanelCard className="p-6">
            <SectionHeading eyebrow="标签高频主题" title="按主题重新进入知识资产" description="标签页已经单独存在，这里保留高频主题入口，方便从知识中枢回到同一批资产。" />
            <div className="mt-5 flex flex-wrap gap-2">
              {data.tagHighlights.map((tag) => (
                <Link key={tag.id} href={`/app/library?filter=${activeFilter}&tag=${encodeURIComponent(tag.label)}`} className="rounded-full bg-ink-low px-4 py-2 text-sm text-ink-muted">
                  {tag.label}
                </Link>
              ))}
            </div>
          </PanelCard>

          <PanelCard className="p-6">
            <SectionHeading eyebrow="最近活动" title="最新进入工作流的知识轨迹" description="帮助你从最近变化而不是静态列表重新进入知识流。" />
            <div className="mt-5 space-y-3">
              {data.recentActivity.map((item) => (
                <div key={item} className="rounded-[20px] bg-ink-low px-4 py-4 text-sm text-ink-muted">
                  {item}
                </div>
              ))}
            </div>
          </PanelCard>
        </aside>
      </section>
    </main>
  );
}
