import { notFound } from "next/navigation";

import { PanelCard } from "@/components/ui/panel-card";
import { SectionHeading } from "@/components/ui/section-heading";
import { getRequestOwnerSession } from "@/lib/request-owner-session";
import { getWikiDetail } from "@/lib/research";

type WikiDetailPageProps = {
  params: Promise<{
    id: string;
  }>;
};

export default async function WikiDetailPage({ params }: WikiDetailPageProps) {
  const { id } = await params;
  const ownerSession = await getRequestOwnerSession();
  const topic = await getWikiDetail(id, ownerSession).catch(() => null);

  if (!topic) {
    notFound();
  }

  return (
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      <SectionHeading eyebrow="wiki detail" title={topic.title} description={topic.summary} />
      {topic.vaultPath ? <p className="mt-4 px-1 text-sm text-ink-primary">{topic.vaultPath}</p> : null}

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <PanelCard className="p-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">Current Understanding</div>
          <div className="mt-5 space-y-3">
            {topic.currentUnderstanding.map((item) => (
              <div key={item} className="rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-text">
                {item}
              </div>
            ))}
          </div>

          <div className="mt-8 text-[11px] uppercase tracking-[0.2em] text-ink-muted">Open Questions</div>
          <div className="mt-5 space-y-3">
            {topic.openQuestions.map((item) => (
              <div key={item} className="rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-text">
                {item}
              </div>
            ))}
          </div>
        </PanelCard>

        <PanelCard className="p-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">Sources</div>
          <div className="mt-5 space-y-3">
            {topic.sources.map((source) => (
              <div key={source.sourceId} className="rounded-[22px] bg-ink-low px-4 py-4">
                <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{source.kind}</div>
                <div className="mt-2 font-headline text-xl font-bold tracking-tight text-ink-text">{source.title}</div>
                {source.locator ? <p className="mt-2 text-sm text-ink-muted">{source.locator}</p> : null}
                {source.vaultPath ? <p className="mt-2 text-sm text-ink-primary">{source.vaultPath}</p> : null}
              </div>
            ))}
          </div>
        </PanelCard>
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <PanelCard className="p-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">Key Claims</div>
          <div className="mt-5 space-y-3">
            {topic.keyClaims.map((claim) => (
              <div key={claim.id} className="rounded-[22px] bg-ink-low px-4 py-4">
                <div className="text-sm leading-7 text-ink-text">{claim.statement}</div>
                <div className="mt-2 text-sm text-ink-muted">{claim.citationLabel}</div>
              </div>
            ))}
          </div>
        </PanelCard>

        <PanelCard className="p-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">Research Thread</div>
          <div className="mt-5 space-y-3">
            {topic.thread.map((entry) => (
              <div key={entry.id} className="rounded-[22px] bg-ink-low px-4 py-4">
                <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{entry.role}</div>
                <div className="mt-2 text-sm leading-7 text-ink-text">{entry.content}</div>
              </div>
            ))}
          </div>
        </PanelCard>
      </div>
    </main>
  );
}
