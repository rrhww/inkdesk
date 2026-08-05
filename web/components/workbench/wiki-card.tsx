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
    <PanelCard className="p-5">
      <div className="text-xs font-medium uppercase text-ink-muted">wiki node</div>
      <h2 className="mt-3 font-headline text-xl font-bold text-ink-text">
        <Link className="rounded-sm outline-none hover:text-ink-primary focus-visible:ring-2 focus-visible:ring-ink-primary" href={`/app/wiki/${topic.id}`}>
          {topic.title}
        </Link>
      </h2>
      <p className="mt-3 text-sm leading-7 text-ink-muted">{topic.summary}</p>
      <div className="mt-5 flex flex-wrap items-center gap-2">
        {topic.unsupportedClaimCount > 0 ? <StatusPill tone="warm">{`${topic.unsupportedClaimCount} 条缺少直接证据`}</StatusPill> : null}
        {topic.staleClaimCount > 0 ? <StatusPill tone="soft">{`${topic.staleClaimCount} 条需要重审`}</StatusPill> : null}
        {topic.conflictingClaimCount > 0 ? <StatusPill tone="neutral">{`${topic.conflictingClaimCount} 条存在冲突`}</StatusPill> : null}
        {highRiskClaimCount === 0 ? <StatusPill tone="primary">claim 风险已清空</StatusPill> : null}
      </div>
      <dl className="mt-5 grid grid-cols-2 gap-3 border-t border-ink-line pt-4 text-sm text-ink-muted">
        <div>
          <dt className="text-xs">raw 来源</dt>
          <dd className="mt-1 font-semibold tabular-nums text-ink-text">{topic.sourceCount}</dd>
        </div>
        <div>
          <dt className="text-xs">开放问题</dt>
          <dd className="mt-1 font-semibold tabular-nums text-ink-text">{topic.openQuestionCount}</dd>
        </div>
      </dl>
      {topic.vaultPath ? <p className="mt-3 break-words text-sm text-ink-primary">{topic.vaultPath}</p> : null}
    </PanelCard>
  );
}
