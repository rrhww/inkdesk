import Link from "next/link";
import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { PanelCard } from "@/components/ui/panel-card";
import { AskAnswerCard } from "@/components/workbench/ask-answer-card";
import { PageShell } from "@/components/workbench/page-shell";
import { OWNER_SESSION_COOKIE } from "@/lib/owner-session";
import { requireRequestOwnerSession } from "@/lib/request-owner-session";
import { askResearch, getAskBriefing, getResearchDashboard, getWikiPages, proposeAskWriteback } from "@/lib/research";
import type { ResearchAskBriefing, ResearchAskMode } from "@/lib/types";

async function createAskWritebackAction(formData: FormData) {
  "use server";

  const askTurnId = String(formData.get("askTurnId") ?? "").trim();
  if (!askTurnId) {
    return;
  }

  const cookieStore = await cookies();
  const review = await proposeAskWriteback(askTurnId, cookieStore.get(OWNER_SESSION_COOKIE)?.value);
  revalidatePath("/app");
  revalidatePath("/app/ask");
  revalidatePath("/app/ingest");
  redirect(`/app/ingest?created=${review.id}`);
}

type AskWorkspacePageProps = {
  searchParams: Promise<{
    q?: string;
    topicId?: string;
    mode?: string;
    continueFromAskTurnId?: string;
  }>;
  basePath?: "/app" | "/app/ask";
};

function buildAskHref(input: {
  basePath: "/app" | "/app/ask";
  question: string;
  mode: ResearchAskMode;
  topicId?: string;
  continueFromAskTurnId?: string;
}) {
  const params = new URLSearchParams();
  params.set("q", input.question);
  if (input.topicId) {
    params.set("topicId", input.topicId);
  }
  if (input.continueFromAskTurnId) {
    params.set("continueFromAskTurnId", input.continueFromAskTurnId);
  }
  params.set("mode", input.mode);
  return `${input.basePath}?${params.toString()}`;
}

function ActionBadge({ briefing }: { briefing: ResearchAskBriefing }) {
  const label = briefing.scope === "ask_turn" ? "问后判断" : briefing.scope === "topic" ? "主题判断" : "首屏判断";
  return <div className="slip">{label}</div>;
}

function signalLabel(type: string) {
  if (type === "UNSUPPORTED_CLAIM") {
    return "缺少直接证据";
  }
  if (type === "STALE_CLAIM") {
    return "需要重审";
  }
  return type;
}

function BriefingPanel({ briefing }: { briefing: ResearchAskBriefing }) {
  return (
    <PanelCard className="relative overflow-hidden p-6 lg:p-8">
      <div aria-hidden="true" className="absolute right-5 top-5 h-20 w-20 rounded-full border border-ink-primary/20" />
      <ActionBadge briefing={briefing} />
      <div className="mt-4 text-[11px] uppercase tracking-[0.2em] text-ink-muted">今日批注</div>
      <h2 className="mt-2 font-headline text-[2.2rem] font-bold leading-[1.05] tracking-[-0.03em] text-ink-text">判断面板</h2>
      <p className="mt-4 text-sm leading-8 text-ink-text">{briefing.summary}</p>
      <div className="mt-5 flex flex-wrap gap-3 text-sm text-ink-muted">
        <span className="stamp-soft">判断置信度 {Math.round(briefing.confidence * 100)}%</span>
        <span className="slip">{briefing.knowledgeGaps.length} 条知识缺口</span>
        <span className="slip">{briefing.nextActions.length} 个下一步动作</span>
      </div>

      <div className="mt-7 text-[11px] uppercase tracking-[0.2em] text-ink-muted">知识缺口</div>
      <div className="mt-4 space-y-3">
        {briefing.knowledgeGaps.map((gap) => (
          <Link key={`${gap.title}-${gap.href}`} className="note-block desk-lift block" href={gap.href}>
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-tertiary">批注</div>
            <div className="mt-2 font-headline text-xl font-bold tracking-[-0.03em] text-ink-text">{gap.title}</div>
            <p className="mt-2 text-sm leading-7 text-ink-text">{gap.detail}</p>
          </Link>
        ))}
      </div>

      <div className="mt-7 text-[11px] uppercase tracking-[0.2em] text-ink-muted">下一步动作</div>
      <div className="mt-4 space-y-3">
        {briefing.nextActions.map((action) => (
          <Link
            key={`${action.kind}-${action.href}`}
            className="desk-lift block rounded-[24px] border border-black/10 bg-white/70 px-4 py-4"
            href={action.href}
          >
            <div className="slip">{action.kind.replaceAll("_", " ")}</div>
            <div className="mt-3 font-headline text-xl font-bold tracking-[-0.03em] text-ink-text">{action.label}</div>
            <p className="mt-2 text-sm leading-7 text-ink-muted">{action.description}</p>
          </Link>
        ))}
      </div>

      {briefing.supportingSignals.length > 0 ? (
        <>
          <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">支撑线索</div>
          <div className="mt-4 space-y-3">
            {briefing.supportingSignals.map((signal) => (
              <Link
                key={`${signal.type}-${signal.href}`}
                className="desk-lift block rounded-[24px] border border-black/10 bg-white/70 px-4 py-4"
                href={signal.href}
              >
                <div className="slip">{signalLabel(signal.type)}</div>
                <div className="mt-3 font-medium text-ink-text">{signal.title}</div>
                <p className="mt-2 text-sm leading-7 text-ink-muted">{signal.summary}</p>
              </Link>
            ))}
          </div>
        </>
      ) : null}
    </PanelCard>
  );
}

function BriefingHero({
  briefing,
  basePath,
  mode,
  topicId,
}: {
  briefing: ResearchAskBriefing;
  basePath: "/app" | "/app/ask";
  mode: ResearchAskMode;
  topicId?: string;
}) {
  const todayLabel = new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric"
  }).format(new Date(briefing.generatedAt));

  return (
    <PanelCard className="overflow-hidden p-6 lg:p-8">
      <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="stamp">今日研究桌</span>
            <span className="slip">本轮研究日期 {todayLabel}</span>
          </div>
          <h2 className="mt-5 max-w-3xl font-headline text-[clamp(2.4rem,4.8vw,4.4rem)] font-bold leading-[0.98] tracking-[-0.05em] text-ink-text">
            先看当前缺什么证据，再决定下一步
          </h2>
          <p className="mt-5 max-w-2xl text-sm leading-8 text-ink-text">{briefing.summary}</p>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <div className="desk-panel px-4 py-4">
              <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">当前焦点主题</div>
              <div className="mt-2 font-headline text-xl font-bold tracking-[-0.03em] text-ink-text">
                {briefing.topicTitle ?? "Inkvault repositioning"}
              </div>
            </div>
            <div className="desk-panel px-4 py-4">
              <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">知识缺口</div>
              <div className="mt-2 font-headline text-xl font-bold tracking-[-0.03em] text-ink-text">
                {briefing.knowledgeGaps[0]?.title ?? "待补一条证据"}
              </div>
            </div>
            <div className="desk-panel px-4 py-4">
              <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">建议切入点</div>
              <div className="mt-2 font-headline text-xl font-bold tracking-[-0.03em] text-ink-text">
                {briefing.nextActions[0]?.label ?? "继续追问"}
              </div>
            </div>
          </div>
        </div>

        <div className="desk-panel self-start px-5 py-5">
          <div className="slip">建议提问</div>
          <div className="mt-4 space-y-3">
            {briefing.suggestedQuestions.map((item, index) => (
              <Link
                key={item}
                className="desk-lift block rounded-[24px] border border-black/10 bg-white/70 px-4 py-4 text-sm leading-7 text-ink-text"
                href={buildAskHref({
                  basePath,
                  question: item,
                  mode,
                  topicId
                })}
              >
                <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">纸签 {index + 1}</div>
                <div className="mt-2 font-medium text-ink-text">{item}</div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </PanelCard>
  );
}

export async function AskWorkspacePage({ searchParams, basePath = "/app" }: AskWorkspacePageProps) {
  const ownerSession = await requireRequestOwnerSession();
  const dashboard = await getResearchDashboard(ownerSession);
  const wikiPages = await getWikiPages(ownerSession);
  const resolved = await searchParams;
  const question = resolved.q?.trim();
  const topicId = resolved.topicId?.trim() || undefined;
  const mode: ResearchAskMode = resolved.mode === "vault_plus_web" ? "vault_plus_web" : "vault";
  const continueFromAskTurnId = resolved.continueFromAskTurnId?.trim() || undefined;
  const answer = question ? await askResearch({ question, topicId, mode, continueFromAskTurnId }, ownerSession) : null;
  const briefing = answer
    ? await getAskBriefing({ askTurnId: answer.id }, ownerSession)
    : await getAskBriefing(topicId ? { topicId } : undefined, ownerSession);

  function askHref(
    nextQuestion: string,
    nextMode = mode,
    nextTopicId = topicId,
    nextContinueFromAskTurnId = answer?.id ?? continueFromAskTurnId
  ) {
    return buildAskHref({
      basePath,
      question: nextQuestion,
      mode: nextMode,
      topicId: nextTopicId,
      continueFromAskTurnId: nextContinueFromAskTurnId
    });
  }

  return (
    <PageShell
      eyebrow="Ask"
      title="研究问答"
      description="先看当前知识缺口，再决定继续追问、补 raw、打开 ingest，还是把稳定结论沉淀到知识库。"
    >
      {!answer ? <BriefingHero basePath={basePath} briefing={briefing} mode={mode} topicId={topicId ?? dashboard.focusTopic?.id ?? undefined} /> : null}

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
        <div className="space-y-6">
          <PanelCard className="p-6 lg:p-8">
            <div className="flex flex-wrap items-center gap-3">
              <div className="stamp">发起提问</div>
              <div className="slip">主提问区</div>
            </div>
            <form action={basePath} className="mt-5 space-y-3" method="GET">
              <div>
                <label className="mb-2 block text-sm font-medium text-ink-text" htmlFor="ask-question">
                  你的问题 <span className="text-ink-errorText">*</span>
                </label>
                <textarea
                  className="desk-field min-h-36"
                  defaultValue={question}
                  id="ask-question"
                  name="q"
                  placeholder="输入你要在现有 wiki / raw 上追问的问题"
                  required
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-ink-text" htmlFor="ask-topic">
                  提问范围
                </label>
                <select
                  className="desk-field"
                  defaultValue={topicId ?? ""}
                  id="ask-topic"
                  name="topicId"
                >
                  <option value="">全局 Ask</option>
                  {wikiPages.map((topic) => (
                    <option key={topic.id} value={topic.id}>
                      {topic.title}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-ink-text" htmlFor="ask-mode">
                  证据模式
                </label>
                <select
                  className="desk-field"
                  defaultValue={mode}
                  id="ask-mode"
                  name="mode"
                >
                  <option value="vault">仅基于 vault 回答</option>
                  <option value="vault_plus_web">显式联网补料</option>
                </select>
              </div>
              {continueFromAskTurnId ? <input name="continueFromAskTurnId" type="hidden" value={continueFromAskTurnId} /> : null}
              <button className="rounded-full bg-ink-primary px-5 py-3 text-sm font-semibold text-white shadow-paper" type="submit">
                提问
              </button>
            </form>

            <div className="note-block mt-4">
              默认先读 wiki 与 raw。只有你明确切到“显式联网补料”，系统才会把外部资料当作补充研究输入。
            </div>
          </PanelCard>

          <PanelCard className="p-6 lg:p-8">
            <AskAnswerCard
              answer={answer}
              continueFromAskTurnId={continueFromAskTurnId}
              mode={mode}
              renderFollowUpHref={(nextQuestion: string, nextMode?: ResearchAskMode) => askHref(nextQuestion, nextMode ?? mode)}
              writebackAction={
                answer ? (
                  <form action={createAskWritebackAction}>
                    <input name="askTurnId" type="hidden" value={answer.id} />
                    <button className="rounded-full bg-ink-primary px-5 py-3 text-sm font-semibold text-white" type="submit">
                      {answer.usedWebSources.length > 0 ? "沉淀到 wiki（会先保存外部来源到 raw）" : "沉淀到 wiki"}
                    </button>
                  </form>
                ) : null
              }
            />
          </PanelCard>
        </div>

        <div className="space-y-6 xl:pt-2">
          <BriefingPanel briefing={briefing} />
        </div>
      </div>
    </PageShell>
  );
}
