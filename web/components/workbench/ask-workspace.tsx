import { InkSelect, type InkSelectOption } from "@/components/ui/ink-select";
import Link from "next/link";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { PanelCard } from "@/components/ui/panel-card";
import { AskAnswerCard } from "@/components/workbench/ask-answer-card";
import { PageShell } from "@/components/workbench/page-shell";
import { OWNER_SESSION_VALUE } from "@/lib/owner-session";
import { askResearch, getAskBriefing, getResearchDashboard, getWikiPages, proposeAskWriteback } from "@/lib/research";
import type { ResearchAskBriefing, ResearchAskMode } from "@/lib/types";

async function createAskWritebackAction(formData: FormData) {
  "use server";

  const askTurnId = String(formData.get("askTurnId") ?? "").trim();
  if (!askTurnId) {
    return;
  }

  const review = await proposeAskWriteback(askTurnId, OWNER_SESSION_VALUE);
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

function BriefingPanel({ briefing }: { briefing: ResearchAskBriefing }) {
  return (
    <PanelCard className="p-8">
      <h2 className="font-headline text-3xl font-extrabold tracking-tight text-ink-text">判断面板</h2>
      <p className="mt-4 text-sm leading-7 text-ink-text">{briefing.summary}</p>

      <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">知识缺口</div>
      <div className="mt-4 space-y-3">
        {briefing.knowledgeGaps.map((gap, i) => (
          <Link key={`${gap.title}-${gap.href}-${i}`} className="block rounded-[22px] bg-[#fff5e9] px-4 py-4" href={gap.href}>
            <div className="font-headline text-xl font-bold tracking-tight text-ink-text">{gap.title}</div>
            <p className="mt-2 text-sm leading-7 text-ink-text">{gap.detail}</p>
          </Link>
        ))}
      </div>

      <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">下一步动作</div>
      <div className="mt-4 space-y-3">
        {briefing.nextActions.map((action, i) => (
          <Link key={`${action.kind}-${action.href}-${i}`} className="block rounded-[22px] bg-ink-low px-4 py-4 hover:bg-white" href={action.href}>
            <div className="font-headline text-xl font-bold tracking-tight text-ink-text">{action.label}</div>
            <p className="mt-2 text-sm leading-7 text-ink-muted">{action.description}</p>
          </Link>
        ))}
      </div>
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
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">Context Ask</div>
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
  const dashboard = await getResearchDashboard(OWNER_SESSION_VALUE);
  const wikiPages = await getWikiPages(OWNER_SESSION_VALUE);
  const resolved = await searchParams;
  const question = resolved.q?.trim();
  const topicId = resolved.topicId?.trim() || undefined;
  const mode: ResearchAskMode = resolved.mode === "vault_plus_web" ? "vault_plus_web" : "vault";
  const continueFromAskTurnId = resolved.continueFromAskTurnId?.trim() || undefined;
  const answer = question ? await askResearch({ question, topicId, mode, continueFromAskTurnId }, OWNER_SESSION_VALUE) : null;
  const briefing = answer
    ? await getAskBriefing({ askTurnId: answer.id }, OWNER_SESSION_VALUE)
    : await getAskBriefing(topicId ? { topicId } : undefined, OWNER_SESSION_VALUE);

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
                <InkSelect
                  id="ask-topic"
                  name="topicId"
                  value={topicId ?? ""}
                  options={[{ value: "", label: "全局 Ask" }, ...wikiPages.map((topic) => ({ value: topic.id, label: topic.title }))]}
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-ink-text" htmlFor="ask-mode">
                  证据模式
                </label>
                <InkSelect
                  id="ask-mode"
                  name="mode"
                  value={mode}
                  options={[
                    { value: "vault", label: "仅基于 vault 回答" },
                    { value: "vault_plus_web", label: "显式联网补料" },
                  ]}
                />
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
