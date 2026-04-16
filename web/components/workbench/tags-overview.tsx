import Link from "next/link";

import { PanelCard } from "@/components/ui/panel-card";
import { SectionHeading } from "@/components/ui/section-heading";
import { StatCard } from "@/components/ui/stat-card";
import { StatusPill } from "@/components/ui/status-pill";
import type { TagRecord } from "@/lib/types";

type TagsOverviewProps = {
  tags: TagRecord[];
};

export function TagsOverview({ tags }: TagsOverviewProps) {
  const totalConnections = tags.reduce((sum, tag) => sum + tag.noteIds.length + tag.planIds.length + tag.articleSlugs.length, 0);

  return (
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      <section className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <SectionHeading
          eyebrow="标签"
          title="标签总览"
          description="标签页把知识资产、计划与公开内容重新组织成一个交叉索引，方便从主题而不是单页进入工作流。"
        />
        <div className="rounded-[24px] bg-white px-5 py-4 shadow-paper">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">当前主题数</div>
          <div className="mt-3 font-headline text-2xl font-extrabold tracking-tight text-ink-text">{tags.length}</div>
        </div>
      </section>

      <section className="mb-8 grid gap-4 md:grid-cols-3">
        <StatCard detail="当前已经形成索引的主题标签" eyebrow="标签总览" value={tags.length} />
        <StatCard detail="知识、计划与公开内容之间的主题连接数" eyebrow="使用次数" value={totalConnections} />
        <StatCard detail="能够直接进入公共内容的标签数量" eyebrow="公开内容" value={tags.filter((tag) => tag.articleSlugs.length > 0).length} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          {tags.map((tag) => (
            <PanelCard key={tag.id} className="p-6">
              <div className="flex flex-wrap items-center gap-3">
                <StatusPill tone={tag.id === "tag-agent" ? "soft" : tag.id === "tag-public" ? "warm" : "neutral"}>{tag.label}</StatusPill>
                <span className="text-sm text-ink-muted">使用次数 {tag.usageCount}</span>
              </div>
              <p className="mt-4 text-sm leading-7 text-ink-muted">{tag.description}</p>
              <div className="mt-5 grid gap-3 md:grid-cols-3">
                <div className="rounded-[20px] bg-ink-low px-4 py-4 text-sm text-ink-muted">关联知识 {tag.noteIds.length} 篇</div>
                <div className="rounded-[20px] bg-ink-low px-4 py-4 text-sm text-ink-muted">关联计划 {tag.planIds.length} 项</div>
                <div className="rounded-[20px] bg-ink-low px-4 py-4 text-sm text-ink-muted">公开内容 {tag.articleSlugs.length} 篇</div>
              </div>
              <div className="mt-5 flex flex-wrap gap-3">
                <Link href={`/app/library?tag=${encodeURIComponent(tag.label)}`} className="rounded-sm bg-ink-primary px-4 py-3 text-sm font-semibold text-white">
                  进入知识库
                </Link>
                <Link href={`/app/search?q=${encodeURIComponent(tag.label)}`} className="rounded-sm bg-white px-4 py-3 text-sm font-semibold text-ink-text shadow-paper">
                  进入检索
                </Link>
              </div>
            </PanelCard>
          ))}
        </div>

        <aside className="space-y-6">
          <PanelCard className="p-6">
            <SectionHeading eyebrow="标签说明" title="让主题成为第二入口" description="除了按页面进入模块，也可以按主题直接回到知识、计划和公开内容之间的交叉点。" />
          </PanelCard>
        </aside>
      </section>
    </main>
  );
}
