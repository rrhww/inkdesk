import type { ReactNode } from "react";

import { PanelCard } from "@/components/ui/panel-card";
import { StatusPill } from "@/components/ui/status-pill";
import type { ResearchProposalClaim, ResearchReviewItem } from "@/lib/types";

type ReviewCardProps = {
  actions: ReactNode;
  highlighted?: boolean;
  review: ResearchReviewItem;
};

function ReviewSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-[22px] bg-ink-low px-4 py-4">
      <h3 className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function EmptyLine({ children }: { children: string }) {
  return <p className="text-sm leading-7 text-ink-muted">{children}</p>;
}

function claimTone(status?: string) {
  if (status === "supported") {
    return "primary" as const;
  }
  if (status === "partial") {
    return "warm" as const;
  }
  return "neutral" as const;
}

function claimSummary(status?: string) {
  if (status === "supported") {
    return "有直接证据支撑";
  }
  if (status === "partial") {
    return "已有来源，但缺少直接证据链";
  }
  return "缺少直接证据";
}

function claimGovernanceSummary(claim: ResearchProposalClaim) {
  if (claim?.hasConflict) {
    return "这条 claim 当前和同主题里的另一条判断互相打架，建议先统一裁决再继续依赖。";
  }
  if (claim?.needsReview) {
    return "这条 claim 最近使用频繁，但验证已过期，建议先重审再继续依赖。";
  }
  if (claim?.provenanceStatus === "unsupported") {
    return "这条 claim 还缺直接证据，当前更适合先补证。";
  }
  if (claim?.provenanceStatus === "supported") {
    return "这条 claim 当前验证较新，可继续复用。";
  }
  return "这条 claim 已绑定来源，但证据链还不够直接。";
}

function formatClaimDate(prefix: string, value?: string | null) {
  if (!value) {
    return `${prefix} 暂无记录`;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return `${prefix} 暂无记录`;
  }
  return `${prefix} ${date.toISOString().slice(0, 10)}`;
}

function reviewIntentSummary(review: ResearchReviewItem) {
  if (review.title.includes("重审") || review.summary.includes("重审") || review.summary.includes("复核")) {
    return "这是一条知识重审提案：先补证，再决定是否更新既有 claim。";
  }
  return review.proposalPayload?.explanation ?? review.proposedUnderstanding ?? review.summary;
}

export function ReviewCard({ actions, highlighted = false, review }: ReviewCardProps) {
  const topicDecision = review.proposalPayload?.topicDecision;
  const topicText =
    topicDecision?.decision === "PATCH"
      ? `建议补进现有 wiki「${topicDecision.targetTopicTitle ?? review.targetTopicTitle ?? "未命名主题"}」`
      : `建议新建 wiki「${topicDecision?.proposedTopicTitle ?? review.proposedTopicTitle ?? "未命名主题"}」`;

  return (
    <PanelCard className={`p-6 ${highlighted ? "ring-2 ring-ink-primary/25" : ""}`}>
      <div className="flex flex-wrap items-center gap-3">
        <StatusPill>{review.kind}</StatusPill>
        {review.targetTopicTitle ? <StatusPill tone="soft">{review.targetTopicTitle}</StatusPill> : null}
        {highlighted ? <StatusPill tone="warm">created</StatusPill> : null}
      </div>
      <h2 className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{review.title}</h2>
      <p className="mt-3 text-sm leading-7 text-ink-muted">{review.summary}</p>

      <div className="mt-5 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="space-y-4">
          <ReviewSection title="Topic 归属">
            <p className="text-sm leading-7 text-ink-text">{topicText}</p>
          </ReviewSection>
          <ReviewSection title="提案解释">
            <p className="text-sm leading-7 text-ink-text">
              {reviewIntentSummary(review)}
            </p>
          </ReviewSection>
          <ReviewSection title="写入内容">
            {review.proposalPayload?.summaryChanges?.length ? (
              <div className="space-y-2">
                {review.proposalPayload.summaryChanges.map((change) => (
                  <p key={change} className="text-sm leading-7 text-ink-text">
                    {change}
                  </p>
                ))}
              </div>
            ) : (
              <EmptyLine>这条提案没有结构化写入内容，将以摘要作为审阅依据。</EmptyLine>
            )}
          </ReviewSection>
        </div>

        <div className="space-y-4">
          <ReviewSection title="Claims">
            {review.proposalPayload?.claims?.length ? (
              <div className="space-y-3">
                {review.proposalPayload.claims.map((claim) => (
                  <div key={`${review.id}-${claim.statement}`} className="rounded-[18px] bg-white px-4 py-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusPill tone={claimTone(claim.provenanceStatus)}>{claim.provenanceStatus ?? "unsupported"}</StatusPill>
                      <StatusPill tone="soft">{`证据 ${claim.evidenceCount ?? 0} 条`}</StatusPill>
                      <StatusPill tone="soft">{`使用 ${claim.usageCount ?? 0} 次`}</StatusPill>
                      {claim.needsReview ? <StatusPill tone="warm">需要重审</StatusPill> : null}
                      {claim.hasConflict ? <StatusPill tone="neutral">存在冲突</StatusPill> : null}
                    </div>
                    <p className="text-sm leading-7 text-ink-text">{claim.statement}</p>
                    <p className="mt-2 text-sm text-ink-muted">{claim.citationLabel}</p>
                    <p className="mt-2 text-sm text-ink-muted">{claimSummary(claim.provenanceStatus)}</p>
                    <p className="mt-2 text-sm text-ink-muted">{claimGovernanceSummary(claim)}</p>
                    <p className="mt-2 text-sm text-ink-muted">{formatClaimDate("最近使用", claim.lastUsedAt)}</p>
                    <p className="mt-2 text-sm text-ink-muted">{formatClaimDate("最近验证", claim.lastVerifiedAt)}</p>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyLine>暂无可单独写入的 claim。</EmptyLine>
            )}
          </ReviewSection>
          <ReviewSection title="证据来源">
            {review.proposalPayload?.evidence?.length ? (
              <div className="space-y-3">
                {review.proposalPayload.evidence.map((evidence) => (
                  <div key={`${review.id}-${evidence.sourceId}`} className="rounded-[18px] bg-white px-4 py-4">
                    <div className="font-semibold text-ink-text">{evidence.sourceTitle}</div>
                    <p className="mt-2 text-sm leading-7 text-ink-text">{evidence.excerpt}</p>
                    {evidence.locator ? <p className="mt-2 break-words text-sm text-ink-muted">{evidence.locator}</p> : null}
                    {evidence.sourceVaultPath ? <p className="mt-2 break-words text-sm text-ink-primary">{evidence.sourceVaultPath}</p> : null}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyLine>暂无结构化证据，建议回到 raw 检查来源。</EmptyLine>
            )}
          </ReviewSection>
          <ReviewSection title="Open Questions">
            {review.proposalPayload?.openQuestions?.length ? (
              <div className="space-y-2">
                {review.proposalPayload.openQuestions.map((item) => (
                  <p key={item} className="text-sm leading-7 text-ink-text">
                    {item}
                  </p>
                ))}
              </div>
            ) : (
              <EmptyLine>这条提案暂时没有新增开放问题。</EmptyLine>
            )}
          </ReviewSection>
        </div>
      </div>

      <dl className="mt-4 grid gap-3 text-sm text-ink-muted md:grid-cols-2">
        <div>raw: {review.sourceVaultPath || "未绑定 raw 路径"}</div>
        <div>wiki: {review.proposedVaultPath || "等待确认写入位置"}</div>
      </dl>
      <div className="mt-5 flex flex-wrap gap-3">{actions}</div>
    </PanelCard>
  );
}
