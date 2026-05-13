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
  return <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{label}</div>;
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
    <PanelCard className="p-8">
      <ActionBadge briefing={briefing} />
      <h2 className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">判断面板</h2>
      <p className="mt-4 text-sm leading-7 text-ink-text">{briefing.summary}</p>
      <div className="mt-4 flex flex-wrap gap-3 text-sm text-ink-muted">
        <span className="rounded-full bg-ink-low px-3 py-2">判断置信度 {Math.round(briefing.confidence * 100)}%</span>
        <span className="rounded-full bg-ink-low px-3 py-2">{briefing.knowledgeGaps.length} 条知识缺口</span>
        <span className="rounded-full bg-ink-low px-3 py-2">{briefing.nextActions.length} 个下一步动作</span>
      </div>

      <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">知识缺口</div>
      <div className="mt-4 space-y-3">
        {briefing.knowledgeGaps.map((gap) => (
          <Link key={`${gap.title}-${gap.href}`} className="block rounded-[22px] bg-[#fff5e9] px-4 py-4" href={gap.href}>
            <div className="font-headline text-xl font-bold tracking-tight text-ink-text">{gap.title}</div>
            <p className="mt-2 text-sm leading-7 text-ink-text">{gap.detail}</p>
          </Link>
        ))}
      </div>

      <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">下一步动作</div>
      <div className="mt-4 space-y-3">
        {briefing.nextActions.map((action) => (
          <Link key={`${action.kind}-${action.href}`} className="block rounded-[22px] bg-ink-low px-4 py-4 hover:bg-white" href={action.href}>
            <div className="font-headline text-xl font-bold tracking-tight text-ink-text">{action.label}</div>
            <p className="mt-2 text-sm leading-7 text-ink-muted">{action.description}</p>
          </Link>
        ))}
      </div>

      {briefing.supportingSignals.length > 0 ? (
        <>
          <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">支撑线索</div>
          <div className="mt-4 space-y-3">
            {briefing.supportingSignals.map((signal) => (
              <Link key={`${signal.type}-${signal.href}`} className="block rounded-[22px] border border-black/5 px-4 py-4" href={signal.href}>
                <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{signalLabel(signal.type)}</div>
                <div className="mt-2 font-medium text-ink-text">{signal.title}</div>
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
  return (
    <PanelCard className="p-8">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">Ask-first</div>
      <h2 className="mt-3 font-headline text-4xl font-extrabold tracking-tight text-ink-text">先看当前缺什么证据，再决定下一步</h2>
      <p className="mt-4 max-w-3xl text-sm leading-7 text-ink-text">{briefing.summary}</p>
      <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">建议提问</div>
      <div className="mt-6 grid gap-3 md:grid-cols-3">
        {briefing.suggestedQuestions.map((item) => (
          <Link
            key={item}
            className="rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-text hover:bg-white"
            href={buildAskHref({
              basePath,
              question: item,
              mode,
              topicId
            })}
          >
            {item}
          </Link>
        ))}
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

      <div className="mt-8 grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
        <div className="space-y-6">
          <PanelCard className="p-8">
            <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">发起提问</div>
            <form action={basePath} className="mt-5 space-y-3" method="GET">
              <div>
                <label className="mb-2 block text-sm font-medium text-ink-text" htmlFor="ask-question">
                  你的问题 <span className="text-ink-errorText">*</span>
                </label>
                <textarea
                  className="min-h-32 w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm leading-7 text-ink-text outline-none focus:ring-2 focus:ring-ink-primary/20"
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
                  className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none focus:ring-2 focus:ring-ink-primary/20"
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
                  className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none focus:ring-2 focus:ring-ink-primary/20"
                  defaultValue={mode}
                  id="ask-mode"
                  name="mode"
                >
                  <option value="vault">仅基于 vault 回答</option>
                  <option value="vault_plus_web">显式联网补料</option>
                </select>
              </div>
              {continueFromAskTurnId ? <input name="continueFromAskTurnId" type="hidden" value={continueFromAskTurnId} /> : null}
              <button className="rounded-full bg-ink-primary px-5 py-3 text-sm font-semibold text-white" type="submit">
                提问
              </button>
            </form>

            <div className="mt-4 rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-muted">
              默认先读 wiki 与 raw。只有你明确切到“显式联网补料”，系统才会把外部资料当作补充研究输入。
            </div>
          </PanelCard>

          <PanelCard className="p-8">
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

        <div className="space-y-6">
          <BriefingPanel briefing={briefing} />
        </div>
      </div>
    </PageShell>
  );
}
