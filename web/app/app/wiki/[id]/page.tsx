import { notFound } from "next/navigation";

import { PanelCard } from "@/components/ui/panel-card";
import { StatusPill } from "@/components/ui/status-pill";
import { PageShell } from "@/components/workbench/page-shell";
import { requireRequestOwnerSession } from "@/lib/request-owner-session";
import { getWikiDetail } from "@/lib/research";
import type { ResearchClaimProvenanceStatus, ResearchTopicClaim } from "@/lib/types";

type WikiDetailPageProps = {
  params: Promise<{
    id: string;
  }>;
};

function claimTone(status?: ResearchClaimProvenanceStatus) {
  if (status === "supported") {
    return "primary" as const;
  }
  if (status === "partial") {
    return "warm" as const;
  }
  return "neutral" as const;
}

function claimDescription(status?: ResearchClaimProvenanceStatus) {
  if (status === "supported") {
    return "这条 claim 目前有直接证据链支撑。";
  }
  if (status === "partial") {
    return "这条 claim 已绑定来源，但证据链还不够直接。";
  }
  return "这条 claim 缺少直接证据，建议回到 raw 或 ingest 补证。";
}

function claimGovernanceTone(claim: ResearchTopicClaim) {
  if (claim.hasConflict) {
    return "neutral" as const;
  }
  if (claim.needsReview) {
    return "warm" as const;
  }
  if (claim.provenanceStatus === "unsupported") {
    return "neutral" as const;
  }
  return "primary" as const;
}

function claimGovernanceLabel(claim: ResearchTopicClaim) {
  if (claim.hasConflict) {
    return "存在冲突";
  }
  if (claim.needsReview) {
    return "需要重审";
  }
  if (claim.provenanceStatus === "unsupported") {
    return "缺少直接证据";
  }
  if (claim.provenanceStatus === "supported") {
    return "最近已验证";
  }
  return "证据链待补强";
}

function claimGovernanceSummary(claim: ResearchTopicClaim) {
  if (claim.hasConflict) {
    return "这条 claim 当前和同主题里的另一条判断互相打架，建议先回到 ingest 做统一裁决。";
  }
  if (claim.needsReview) {
    return "这条 claim 最近使用频繁，但验证时间已经过旧，建议先回到 ingest 复核。";
  }
  if (claim.provenanceStatus === "unsupported") {
    return "这条 claim 还没有直接证据，下一步更适合补 raw 或审 ingest。";
  }
  if (claim.provenanceStatus === "supported") {
    return "这条 claim 当前验证较新，可以继续作为稳定上下文使用。";
  }
  return "这条 claim 已绑定来源，但证据链还不够直接，后续仍值得继续补证。";
}

function formatVerifiedAt(value?: string | null) {
  if (!value) {
    return "最近验证 暂无记录";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "最近验证 暂无记录";
  }
  return `最近验证 ${date.toISOString().slice(0, 10)}`;
}

function formatUsedAt(value?: string | null) {
  if (!value) {
    return "最近使用 暂无记录";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "最近使用 暂无记录";
  }
  return `最近使用 ${date.toISOString().slice(0, 10)}`;
}

export default async function WikiDetailPage({ params }: WikiDetailPageProps) {
  const { id } = await params;
  const ownerSession = await requireRequestOwnerSession();
  const topic = await getWikiDetail(id, ownerSession).catch(() => null);

  if (!topic) {
    notFound();
  }

  return (
    <PageShell eyebrow="wiki detail" title={topic.title} description={topic.summary}>
      {topic.vaultPath ? <p className="mt-4 px-1 text-sm text-ink-primary">{topic.vaultPath}</p> : null}

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <PanelCard className="p-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">Current Understanding</div>
          <div className="mt-5 space-y-3">
            {topic.currentUnderstanding.length > 0 ? (
              topic.currentUnderstanding.map((item) => (
                <div key={item} className="rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-text">
                  {item}
                </div>
              ))
            ) : (
              <div className="rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-muted">
                这个 wiki 还没有稳定理解。可以回到 ingest 接受第一条 summary change。
              </div>
            )}
          </div>

          <div className="mt-8 text-[11px] uppercase tracking-[0.2em] text-ink-muted">Open Questions</div>
          <div className="mt-5 space-y-3">
            {topic.openQuestions.length > 0 ? (
              topic.openQuestions.map((item) => (
                <div key={item} className="rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-text">
                  {item}
                </div>
              ))
            ) : (
              <div className="rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-muted">
                当前没有开放问题。下一轮 Ask 可以尝试挑战这页理解是否足够稳定。
              </div>
            )}
          </div>
        </PanelCard>

        <PanelCard className="p-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">Sources</div>
          <div className="mt-5 space-y-3">
            {topic.sources.length > 0 ? (
              topic.sources.map((source) => (
                <div key={source.sourceId} className="rounded-[22px] bg-ink-low px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{source.kind}</div>
                  <div className="mt-2 font-headline text-xl font-bold tracking-tight text-ink-text">{source.title}</div>
                  {source.locator ? <p className="mt-2 break-words text-sm text-ink-muted">{source.locator}</p> : null}
                  {source.vaultPath ? <p className="mt-2 break-words text-sm text-ink-primary">{source.vaultPath}</p> : null}
                </div>
              ))
            ) : (
              <div className="rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-muted">
                还没有 raw 来源链接。这个页面需要补证据后才算健康。
              </div>
            )}
          </div>
        </PanelCard>
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <PanelCard className="p-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">Key Claims</div>
          <div className="mt-5 space-y-3">
            {topic.keyClaims.length > 0 ? (
              topic.keyClaims.map((claim) => (
                <div key={claim.id} className="rounded-[22px] bg-ink-low px-4 py-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusPill tone={claimTone(claim.provenanceStatus)}>{claim.provenanceStatus ?? "unsupported"}</StatusPill>
                    <StatusPill tone="soft">{`证据 ${claim.evidenceCount ?? 0} 条`}</StatusPill>
                    <StatusPill tone="soft">{`使用 ${claim.usageCount ?? 0} 次`}</StatusPill>
                    <StatusPill tone={claimGovernanceTone(claim)}>{claimGovernanceLabel(claim)}</StatusPill>
                  </div>
                  <div className="text-sm leading-7 text-ink-text">{claim.statement}</div>
                  <div className="mt-2 text-sm text-ink-muted">{claim.citationLabel}</div>
                  <div className="mt-2 text-sm text-ink-muted">{formatVerifiedAt(claim.lastVerifiedAt)}</div>
                  <div className="mt-2 text-sm text-ink-muted">{formatUsedAt(claim.lastUsedAt)}</div>
                  <div className="mt-2 text-sm text-ink-muted">{claimDescription(claim.provenanceStatus)}</div>
                  <div className="mt-2 text-sm text-ink-muted">{claimGovernanceSummary(claim)}</div>
                </div>
              ))
            ) : (
              <div className="rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-muted">
                暂无可引用 claim。建议从 ingest 中补入有证据支撑的判断。
              </div>
            )}
          </div>
        </PanelCard>

        <PanelCard className="p-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">Research Thread</div>
          <div className="mt-5 space-y-3">
            {topic.thread.length > 0 ? (
              topic.thread.map((entry) => (
                <div key={entry.id} className="rounded-[22px] bg-ink-low px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{entry.role}</div>
                  <div className="mt-2 text-sm leading-7 text-ink-text">{entry.content}</div>
                </div>
              ))
            ) : (
              <div className="rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-muted">
                研究线程还没有记录。后续 Ask 和 ingest 会在这里留下演化脉络。
              </div>
            )}
          </div>
        </PanelCard>
      </div>
    </PageShell>
  );
}
