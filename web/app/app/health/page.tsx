import { EmptyState } from "@/components/ui/empty-state";
import { PanelCard } from "@/components/ui/panel-card";
import { PageShell } from "@/components/workbench/page-shell";
import { getVaultHealth } from "@/lib/research";
import type { HealthFinding, HealthFindingType, HealthSeverity } from "@/lib/types";

const SEVERITY_LABELS: Record<HealthSeverity, string> = {
  error: "错误",
  warning: "警告",
  info: "提示",
};

const SEVERITY_COLORS: Record<HealthSeverity, string> = {
  error: "bg-[#fde8e8] text-[#c62828]",
  warning: "bg-[#fff4ec] text-ink-tertiary",
  info: "bg-ink-primarySoft text-ink-primary",
};

const TYPE_LABELS: Partial<Record<HealthFindingType, string>> = {
  BROKEN_LINK: "断链",
  ORPHAN_PAGE: "孤页",
  MISSING_FRONTMATTER: "缺 frontmatter",
  MISSING_SOURCE: "缺来源引用",
  INVALID_STATUS: "状态非法",
  SHORT_PAGE: "短页",
  DUPLICATE_TITLE: "重复标题",
  SIMILAR_TITLE: "相似标题",
  STALE_PAGE: "长期未更新",
  OUTDATED_REFERENCE: "来源失效",
  EXPLICIT_OUTDATED: "已过期",
  MISSING_SECTION: "缺模板段落",
};

const SEVERITY_ORDER: HealthSeverity[] = ["error", "warning", "info"];

function HealthSummaryGrid({
  score,
  gate,
  totalPages,
  errors,
  warnings,
  infos,
}: {
  score: number | null | undefined;
  gate: string | null | undefined;
  totalPages: number;
  errors: number;
  warnings: number;
  infos: number;
}) {
  const gateColor = gate === "PASSED" ? "text-green-600" : "text-red-600";
  const gateLabel = gate === "PASSED" ? "通过" : gate === "FAILED" ? "未通过" : "—";
  const scoreDisplay = score != null ? `${score}%` : "N/A";

  return (
    <div className="grid grid-cols-6 gap-4">
      <div className="text-center">
        <div className={`text-2xl font-headline font-extrabold ${score != null && score >= 80 ? "text-green-600" : score != null && score >= 60 ? "text-ink-tertiary" : "text-red-600"}`}>
          {scoreDisplay}
        </div>
        <div className="mt-1 text-xs text-ink-muted">健康分</div>
      </div>
      <div className="text-center">
        <div className={`text-2xl font-headline font-extrabold ${gateColor}`}>{gateLabel}</div>
        <div className="mt-1 text-xs text-ink-muted">Schema Gate</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-headline font-extrabold text-ink-text">{totalPages}</div>
        <div className="mt-1 text-xs text-ink-muted">总页面</div>
      </div>
      <div className="text-center">
        <div className={`text-2xl font-headline font-extrabold ${errors > 0 ? "text-red-600" : "text-ink-muted"}`}>{errors}</div>
        <div className="mt-1 text-xs text-ink-muted">错误</div>
      </div>
      <div className="text-center">
        <div className={`text-2xl font-headline font-extrabold ${warnings > 0 ? "text-ink-tertiary" : "text-ink-muted"}`}>{warnings}</div>
        <div className="mt-1 text-xs text-ink-muted">警告</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-headline font-extrabold text-ink-muted">{infos}</div>
        <div className="mt-1 text-xs text-ink-muted">提示</div>
      </div>
    </div>
  );
}

function FindingCard({ finding }: { finding: HealthFinding }) {
  const sev = finding.severity as HealthSeverity;
  return (
    <div className="rounded-[22px] bg-ink-low px-5 py-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${SEVERITY_COLORS[sev] ?? "bg-ink-low text-ink-muted"}`}>
              {sev === "error" && (
                <span className="material-symbols-outlined text-[14px]">error</span>
              )}
              {sev === "warning" && (
                <span className="material-symbols-outlined text-[14px]">warning</span>
              )}
              {sev === "info" && (
                <span className="material-symbols-outlined text-[14px]">info_i</span>
              )}
              {TYPE_LABELS[finding.type as HealthFindingType] ?? finding.type}
            </span>
            <span className="text-[11px] text-ink-muted">{SEVERITY_LABELS[sev] ?? sev}</span>
            {finding.ruleId && (
              <span className="text-[10px] text-ink-muted font-mono">{finding.ruleId}</span>
            )}
          </div>
          <p className="text-sm font-medium text-ink-text font-mono">{finding.page}</p>
          <p className="mt-1 text-sm leading-6 text-ink-muted">{finding.detail}</p>
        </div>
      </div>
    </div>
  );
}

function GateBanner({ gate }: { gate: string | null | undefined }) {
  if (gate === "PASSED") {
    return (
      <div className="rounded-[22px] bg-green-50 border border-green-200 px-6 py-4 text-sm text-green-800">
        <span className="font-bold">Schema Gate 通过</span> — 无 error 级别问题，可以创建 Evaluation Run。
      </div>
    );
  }
  if (gate === "FAILED") {
    return (
      <div className="rounded-[22px] bg-red-50 border border-red-200 px-6 py-4 text-sm text-red-800">
        <span className="font-bold">Schema Gate 未通过</span> — 存在 error 级别问题，在修复前无法创建 Evaluation Run。
      </div>
    );
  }
  return null;
}

export default async function HealthPage() {
  const health = await getVaultHealth().catch(() => null);

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

  const cat = health.categoryCounts ?? { error: 0, warning: 0, info: 0 };
  const findingsBySeverity: Record<HealthSeverity, HealthFinding[]> = {
    error: health.findings.filter((f) => f.severity === "error"),
    warning: health.findings.filter((f) => f.severity === "warning"),
    info: health.findings.filter((f) => f.severity === "info"),
  };

  return (
    <PageShell
      eyebrow="health"
      title="知识库健康"
      description={
        health.ruleVersion
          ? `基于确定性规则扫描（规则版本 ${health.ruleVersion}），不依赖 LLM。检测 ${health.findings[0] ? Object.keys(TYPE_LABELS).length : 4} 类结构问题。`
          : "基于确定性的文件扫描，不依赖 LLM。检测断链、孤页、缺失 frontmatter 与来源引用四类结构问题。深度语义问题将在后续阶段补充。"
      }
    >
      <div className="mt-8 space-y-6">
        <GateBanner gate={health.gateStatus} />

        <PanelCard className="p-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">健康概览</div>
          <HealthSummaryGrid
            score={health.healthScore}
            gate={health.gateStatus}
            totalPages={health.summary.totalPages}
            errors={cat.error}
            warnings={cat.warning}
            infos={cat.info}
          />
        </PanelCard>

        {health.findings.length === 0 ? (
          <PanelCard className="p-12 text-center">
            <div className="text-4xl mb-4">
              <span className="material-symbols-outlined text-[48px] text-ink-primary">verified</span>
            </div>
            <h3 className="font-headline text-2xl font-extrabold tracking-tight text-ink-text">
              知识库结构健康
            </h3>
            <p className="mt-2 text-sm text-ink-muted">
              未发现任何结构问题。健康分 {health.healthScore != null ? `${health.healthScore}%` : "N/A"}。
            </p>
          </PanelCard>
        ) : (
          <>
            {SEVERITY_ORDER.map((sev) => {
              const items = findingsBySeverity[sev];
              if (items.length === 0) return null;
              return (
                <section key={sev}>
                  <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">
                    {SEVERITY_LABELS[sev]} ({items.length})
                  </div>
                  <div className="space-y-3">
                    {items.map((f, i) => (
                      <FindingCard finding={f} key={`${f.fingerprint ?? `${f.type}-${f.page}-${i}`}`} />
                    ))}
                  </div>
                </section>
              );
            })}
          </>
        )}
      </div>
    </PageShell>
  );
}
