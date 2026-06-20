import { EmptyState } from "@/components/ui/empty-state";
import { PanelCard } from "@/components/ui/panel-card";
import { StatusPill } from "@/components/ui/status-pill";
import { PageShell } from "@/components/workbench/page-shell";
import { WikiCard } from "@/components/workbench/wiki-card";
import { OWNER_SESSION_VALUE } from "@/lib/owner-session";
import { getResearchDashboard, getWikiPages } from "@/lib/research";

export default async function WikiPage() {
  const dashboard = await getResearchDashboard(OWNER_SESSION_VALUE);
  const topics = await getWikiPages(OWNER_SESSION_VALUE);
  const unsupportedClaimCount = dashboard.health.unsupportedClaimCount;
  const staleClaimCount = dashboard.health.staleClaimCount;
  const conflictingClaimCount = dashboard.health.conflictingClaimCount;
  const highRiskClaimCount = unsupportedClaimCount + staleClaimCount;

  return (
    <PageShell
        eyebrow="wiki"
        title="沉淀后的知识页面"
        description="wiki/ 是正式知识层。每个页面都来自已接受的 ingest 提案，并保留 current understanding、open questions、key claims 和 raw 来源链接。"
    >
      <PanelCard className="mt-8 p-6">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">claim 治理总览</div>
        <h2 className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">
          {highRiskClaimCount > 0 ? `${highRiskClaimCount} 条高风险 claim 仍需处理` : "当前 claim 风险已清空"}
        </h2>
        <p className="mt-3 text-sm leading-7 text-ink-muted">
          {highRiskClaimCount > 0
            ? "知识页里仍有 claim 需要补证或重审，建议先回到对应 wiki、raw 或 ingest 继续收口。"
            : "当前知识库里的 claim 已没有明显风险，可以继续把它当作稳定研究上下文。"}
        </p>
        <div className="mt-5 flex flex-wrap items-center gap-2">
          {unsupportedClaimCount > 0 ? <StatusPill tone="warm">{`${unsupportedClaimCount} 条缺少直接证据`}</StatusPill> : null}
          {staleClaimCount > 0 ? <StatusPill tone="soft">{`${staleClaimCount} 条需要重审`}</StatusPill> : null}
          {conflictingClaimCount > 0 ? <StatusPill tone="neutral">{`${conflictingClaimCount} 条 claim 存在冲突`}</StatusPill> : null}
          {highRiskClaimCount === 0 ? <StatusPill tone="primary">claim 风险已清空</StatusPill> : null}
          <StatusPill tone="neutral">{`${dashboard.summary.activeTopics} 个知识页`}</StatusPill>
        </div>
      </PanelCard>

      <div className="mt-8 grid gap-4 xl:grid-cols-2">
        {topics.length > 0 ? (
          topics.map((topic) => <WikiCard key={topic.id} topic={topic} />)
        ) : (
          <EmptyState
            eyebrow="wiki empty"
            title="还没有可沉淀的知识页"
            description="先从 raw 导入材料，再在 ingest 接受第一条提案。wiki 会在确认后形成长期理解。"
            actionLabel="前往 ingest"
            href="/app/ingest"
          />
        )}
      </div>
    </PageShell>
  );
}
