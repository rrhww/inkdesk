import { EmptyState } from "@/components/ui/empty-state";
import { PanelCard } from "@/components/ui/panel-card";
import { PageShell } from "@/components/workbench/page-shell";
import { OWNER_SESSION_VALUE } from "@/lib/owner-session";
import { getVaultHealth } from "@/lib/research";
import type { HealthFinding, HealthSummary } from "@/lib/types";

const SEVERITY_LABELS: Record<string, string> = {
  warning: "警告",
  info: "提示",
};

const SEVERITY_COLORS: Record<string, string> = {
  warning: "bg-[#fff4ec] text-ink-tertiary",
  info: "bg-ink-primarySoft text-ink-primary",
};

const TYPE_LABELS: Record<string, string> = {
  BROKEN_LINK: "断链",
  ORPHAN_PAGE: "孤页",
  MISSING_FRONTMATTER: "缺 frontmatter",
  MISSING_SOURCE: "缺来源引用",
};

const TYPE_ICONS: Record<string, string> = {
  BROKEN_LINK: "link_off",
  ORPHAN_PAGE: "description",
  MISSING_FRONTMATTER: "info_i",
  MISSING_SOURCE: "source",
};

function HealthSummaryGrid({ summary }: { summary: HealthSummary }) {
  const items = [
    { label: "总页面数", value: summary.totalPages, icon: "description", color: "text-ink-text" },
    { label: "断链", value: summary.brokenLinkCount, icon: "link_off", color: summary.brokenLinkCount > 0 ? "text-ink-tertiary" : "text-ink-muted" },
    { label: "孤页", value: summary.orphanPageCount, icon: "description", color: summary.orphanPageCount > 0 ? "text-ink-tertiary" : "text-ink-muted" },
    { label: "缺 frontmatter", value: summary.missingFrontmatterCount, icon: "info_i", color: summary.missingFrontmatterCount > 0 ? "text-ink-tertiary" : "text-ink-muted" },
    { label: "缺来源引用", value: summary.missingSourceCount, icon: "source", color: summary.missingSourceCount > 0 ? "text-ink-tertiary" : "text-ink-muted" },
  ];

  return (
    <div className="grid grid-cols-5 gap-4">
      {items.map((item) => (
        <div key={item.label} className="text-center">
          <div className={`text-2xl font-headline font-extrabold ${item.color}`}>{item.value}</div>
          <div className="mt-1 flex items-center justify-center gap-1 text-xs text-ink-muted">
            <span className="material-symbols-outlined text-[14px]">{item.icon}</span>
            {item.label}
          </div>
        </div>
      ))}
    </div>
  );
}

function FindingCard({ finding }: { finding: HealthFinding }) {
  return (
    <div className="rounded-[22px] bg-ink-low px-5 py-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${SEVERITY_COLORS[finding.severity] ?? "bg-ink-low text-ink-muted"}`}>
              <span className="material-symbols-outlined text-[14px]">{TYPE_ICONS[finding.type] ?? "warning"}</span>
              {TYPE_LABELS[finding.type] ?? finding.type}
            </span>
            <span className="text-[11px] text-ink-muted">{SEVERITY_LABELS[finding.severity] ?? finding.severity}</span>
          </div>
          <p className="text-sm font-medium text-ink-text font-mono">{finding.page}</p>
          <p className="mt-1 text-sm leading-6 text-ink-muted">{finding.detail}</p>
        </div>
      </div>
    </div>
  );
}

export default async function HealthPage() {
  const health = await getVaultHealth(OWNER_SESSION_VALUE).catch(() => null);

  if (!health) {
    return (
      <PageShell eyebrow="health" title="知识库健康" description="知识库未初始化或扫描失败。">
        <div className="mt-8">
          <EmptyState
            eyebrow="health unavailable"
            title="无法获取健康数据"
            description="请确认知识库已完成初始化，且后端服务正常运行。"
            actionLabel="返回首页"
            href="/app"
          />
        </div>
      </PageShell>
    );
  }

  const warnings = health.findings.filter((f) => f.severity === "warning");
  const infos = health.findings.filter((f) => f.severity === "info");

  return (
    <PageShell
      eyebrow="health"
      title="知识库健康"
      description="基于确定性的文件扫描，不依赖 LLM。检测断链、孤页、缺失 frontmatter 与来源引用四类结构问题。深度语义问题将在后续阶段补充。"
    >
      <div className="mt-8 space-y-6">
        <PanelCard className="p-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">健康概览</div>
          <HealthSummaryGrid summary={health.summary} />
        </PanelCard>

        {health.findings.length === 0 ? (
          <PanelCard className="p-12 text-center">
            <div className="text-4xl mb-4">
              <span className="material-symbols-outlined text-[48px] text-ink-primary">verified</span>
            </div>
            <h3 className="font-headline text-2xl font-extrabold tracking-tight text-ink-text">知识库结构健康</h3>
            <p className="mt-2 text-sm text-ink-muted">未发现断链、孤页、缺 frontmatter 或缺来源引用的结构问题。</p>
          </PanelCard>
        ) : (
          <>
            {warnings.length > 0 && (
              <section>
                <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">
                  警告 ({warnings.length})
                </div>
                <div className="space-y-3">
                  {warnings.map((f, i) => (
                    <FindingCard finding={f} key={`${f.type}-${f.page}-${i}`} />
                  ))}
                </div>
              </section>
            )}

            {infos.length > 0 && (
              <section>
                <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">
                  提示 ({infos.length})
                </div>
                <div className="space-y-3">
                  {infos.map((f, i) => (
                    <FindingCard finding={f} key={`${f.type}-${f.page}-${i}`} />
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </PageShell>
  );
}
