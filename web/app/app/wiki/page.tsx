import Link from "next/link";

import { PanelCard } from "@/components/ui/panel-card";
import { SectionHeading } from "@/components/ui/section-heading";
import { getRequestOwnerSession } from "@/lib/request-owner-session";
import { getWikiPages } from "@/lib/research";

export default async function WikiPage() {
  const ownerSession = await getRequestOwnerSession();
  const topics = await getWikiPages(ownerSession);

  return (
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      <SectionHeading
        eyebrow="wiki"
        title="沉淀后的知识页面"
        description="wiki/ 是正式知识层。每个页面都来自已接受的 ingest 提案，并保留 current understanding、open questions、key claims 和 raw 来源链接。"
      />

      <div className="mt-8 grid gap-4 xl:grid-cols-2">
        {topics.map((topic) => (
          <PanelCard key={topic.id} className="p-6">
            <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">wiki page</div>
            <h2 className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{topic.title}</h2>
            <p className="mt-3 text-sm leading-7 text-ink-muted">{topic.summary}</p>
            <div className="mt-5 flex flex-wrap gap-2 text-sm text-ink-muted">
              <span>{topic.sourceCount} 条 raw 来源</span>
              <span>{topic.openQuestionCount} 个开放问题</span>
            </div>
            {topic.vaultPath ? <p className="mt-3 text-sm text-ink-primary">{topic.vaultPath}</p> : null}
            <Link className="mt-6 inline-flex rounded-full bg-ink-primary px-5 py-3 text-sm font-semibold text-white" href={`/app/wiki/${topic.id}`}>
              打开 wiki
            </Link>
          </PanelCard>
        ))}
      </div>
    </main>
  );
}
