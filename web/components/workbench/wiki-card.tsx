import Link from "next/link";

import { PanelCard } from "@/components/ui/panel-card";
import { StatusPill } from "@/components/ui/status-pill";
import type { ResearchTopicSummary } from "@/lib/types";

type WikiCardProps = {
  topic: ResearchTopicSummary;
};

export function WikiCard({ topic }: WikiCardProps) {
  const highRiskClaimCount = topic.unsupportedClaimCount + topic.staleClaimCount;

  return (
    <PanelCard className="p-6">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">wiki page</div>
      <h2 className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{topic.title}</h2>
      <p className="mt-3 text-sm leading-7 text-ink-muted">{topic.summary}</p>
      <div className="mt-5 flex flex-wrap items-center gap-2">
        {topic.unsupportedClaimCount > 0 ? <StatusPill tone="warm">{`${topic.unsupportedClaimCount} 条缺少直接证据`}</StatusPill> : null}
        {topic.staleClaimCount > 0 ? <StatusPill tone="soft">{`${topic.staleClaimCount} 条需要重审`}</StatusPill> : null}
        {topic.conflictingClaimCount > 0 ? <StatusPill tone="neutral">{`${topic.conflictingClaimCount} 条存在冲突`}</StatusPill> : null}
        {highRiskClaimCount === 0 ? <StatusPill tone="primary">claim 风险已清空</StatusPill> : null}
      </div>
      <div className="mt-5 flex flex-wrap gap-2 text-sm text-ink-muted">
        <span>{topic.sourceCount} 条 raw 来源</span>
        <span>{topic.openQuestionCount} 个开放问题</span>
      </div>
      {topic.vaultPath ? <p className="mt-3 break-words text-sm text-ink-primary">{topic.vaultPath}</p> : null}
      <Link className="mt-6 inline-flex rounded-full bg-ink-primary px-5 py-3 text-sm font-semibold text-white" href={`/app/wiki/${topic.id}`}>
        打开 wiki
      </Link>
    </PanelCard>
  );
}
