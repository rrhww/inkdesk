import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";

import { PanelCard } from "@/components/ui/panel-card";
import { SectionHeading } from "@/components/ui/section-heading";
import { OWNER_SESSION_COOKIE } from "@/lib/owner-session";
import { getRequestOwnerSession } from "@/lib/request-owner-session";
import { askResearch, getResearchDashboard, getWikiPages, proposeAskWriteback } from "@/lib/research";

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

type AskPageProps = {
  searchParams: Promise<{
    q?: string;
    topicId?: string;
    mode?: string;
    continueFromAskTurnId?: string;
  }>;
};

export default async function AskPage({ searchParams }: AskPageProps) {
  const ownerSession = await getRequestOwnerSession();
  const dashboard = await getResearchDashboard(ownerSession);
  const wikiPages = await getWikiPages(ownerSession);
  const resolved = await searchParams;
  const question = resolved.q?.trim();
  const topicId = resolved.topicId?.trim() || undefined;
  const mode = resolved.mode === "vault_plus_web" ? "vault_plus_web" : "vault";
  const continueFromAskTurnId = resolved.continueFromAskTurnId?.trim() || undefined;
  const answer = question ? await askResearch({ question, topicId, mode, continueFromAskTurnId }, ownerSession) : null;

  function askHref(
    nextQuestion: string,
    nextMode = mode,
    nextTopicId = topicId,
    nextContinueFromAskTurnId = answer?.id ?? continueFromAskTurnId
  ) {
    const params = new URLSearchParams();
    params.set("q", nextQuestion);
    if (nextTopicId) {
      params.set("topicId", nextTopicId);
    }
    if (nextContinueFromAskTurnId) {
      params.set("continueFromAskTurnId", nextContinueFromAskTurnId);
    }
    params.set("mode", nextMode);
    return `/app/ask?${params.toString()}`;
  }

  return (
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      <SectionHeading
        eyebrow="Ask"
        title="研究问答"
        description="先围绕已有 wiki 和 raw 提问，再决定是否需要继续导入新材料。Ask 的回答优先基于 wiki，并保留 raw 引用来源。"
      />

      <div className="mt-8 grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <PanelCard className="p-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">发起提问</div>
          <form action="/app/ask" className="mt-5 space-y-3" method="GET">
            <textarea
              className="min-h-32 w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm leading-7 text-ink-text outline-none"
              defaultValue={question}
              name="q"
              placeholder="输入你要在现有 wiki / raw 上追问的问题"
            />
            <select
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none"
              defaultValue={topicId ?? ""}
              name="topicId"
            >
              <option value="">全局 Ask</option>
              {wikiPages.map((topic) => (
                <option key={topic.id} value={topic.id}>
                  {topic.title}
                </option>
              ))}
            </select>
            <select
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none"
              defaultValue={mode}
              name="mode"
            >
              <option value="vault">仅基于 vault 回答</option>
              <option value="vault_plus_web">显式联网补料</option>
            </select>
            {continueFromAskTurnId ? <input name="continueFromAskTurnId" type="hidden" value={continueFromAskTurnId} /> : null}
            <button className="rounded-full bg-ink-primary px-5 py-3 text-sm font-semibold text-white" type="submit">
              提问
            </button>
          </form>

          <div className="mt-4 rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-muted">
            默认先读 wiki 与 raw。只有你明确切到“显式联网补料”，系统才会把外部资料当作补充研究输入。
          </div>

          <div className="mt-8 text-[11px] uppercase tracking-[0.2em] text-ink-muted">建议提问</div>
          <div className="mt-5 space-y-3">
            {dashboard.suggestedQuestions.map((item) => (
              <Link
                key={item}
                className="block rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-text hover:bg-white"
                href={askHref(item, mode, dashboard.focusTopic?.id ?? topicId)}
              >
                {item}
              </Link>
            ))}
          </div>
        </PanelCard>

        <PanelCard className="p-8">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">回答</div>
          {answer ? (
            <>
              <h2 className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{answer.question}</h2>
              {answer.contextAskTurnIds.length > 0 ? (
                <div className="mt-4 rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-muted">
                  正在延续上一轮问答。新的追问会继续沿用这条 Ask 线索，而不是重新开始。
                </div>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-3 text-sm text-ink-muted">
                <span className="rounded-full bg-ink-low px-3 py-2">置信度 {Math.round(answer.confidence * 100)}%</span>
                <span className="rounded-full bg-ink-low px-3 py-2">{answer.usedWikiIds.length} 个 wiki 页面</span>
                <span className="rounded-full bg-ink-low px-3 py-2">{answer.usedSourceIds.length} 条来源</span>
              </div>
              <p className="mt-4 text-sm leading-7 text-ink-text">{answer.answer}</p>

              <div className="mt-5 flex flex-wrap items-center gap-3">
                <form action={createAskWritebackAction}>
                  <input name="askTurnId" type="hidden" value={answer.id} />
                  <button className="rounded-full bg-ink-primary px-5 py-3 text-sm font-semibold text-white" type="submit">
                    {answer.usedWebSources.length > 0 ? "沉淀到 wiki（会先保存外部来源到 raw）" : "沉淀到 wiki"}
                  </button>
                </form>
                <span className="text-sm text-ink-muted">只会生成一条 ingest 提案，不会直接改写 wiki。</span>
              </div>

              {mode === "vault" ? (
                <div className="mt-5">
                  <Link
                    className="inline-flex rounded-full bg-ink-primarySoft px-5 py-3 text-sm font-semibold text-ink-primary"
                    href={askHref(answer.question, "vault_plus_web")}
                  >
                    显式联网补料
                  </Link>
                </div>
              ) : null}

              <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">知识缺口</div>
              <div className="mt-4 space-y-3">
                {answer.knowledgeGaps.length > 0 ? (
                  answer.knowledgeGaps.map((gap) => (
                    <div key={gap} className="rounded-[22px] bg-[#fff5e9] px-4 py-4 text-sm leading-7 text-ink-text">
                      {gap}
                    </div>
                  ))
                ) : (
                  <div className="rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-muted">
                    当前回答主要缺的是更深入追问，而不是明显证据空洞；如果你想继续扩展范围，可以显式联网补料。
                  </div>
                )}
              </div>

              {answer.usedWebSources.length > 0 ? (
                <>
                  <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">外部补料</div>
                  <div className="mt-4 rounded-[22px] bg-[#fff5e9] px-4 py-4 text-sm leading-7 text-ink-text">
                    这些外部资料还没有进入你的 vault。只有你点击“沉淀到 wiki”时，系统才会先把它们保存到 raw。
                  </div>
                  <div className="mt-4 space-y-3">
                    {answer.usedWebSources.map((source) => (
                      <div key={source.url} className="rounded-[22px] bg-ink-low px-4 py-4">
                        <div className="font-headline text-xl font-bold tracking-tight text-ink-text">{source.title}</div>
                        <div className="mt-2 text-sm text-ink-primary">{source.url}</div>
                        <p className="mt-3 text-sm leading-7 text-ink-text">{source.excerpt}</p>
                        <p className="mt-2 text-sm leading-7 text-ink-muted">{source.reasonUsed}</p>
                      </div>
                    ))}
                  </div>
                </>
              ) : null}

              <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">继续追问</div>
              <div className="mt-4 space-y-3">
                {answer.followUpQuestions.map((followUp) => (
                  <Link
                    key={followUp}
                    className="block rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-text hover:bg-white"
                    href={askHref(followUp)}
                  >
                    {followUp}
                  </Link>
                ))}
              </div>

              <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">引用来源</div>
              <div className="mt-4 space-y-3">
                {answer.citations.map((citation) => (
                  <div key={citation.sourceId} className="rounded-[22px] bg-ink-low px-4 py-4">
                    <div className="font-headline text-xl font-bold tracking-tight text-ink-text">{citation.title}</div>
                    <div className="mt-2 text-sm text-ink-muted">{citation.locator}</div>
                    {citation.vaultPath ? <div className="mt-2 text-sm text-ink-primary">{citation.vaultPath}</div> : null}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <>
              <h2 className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">先从一个问题开始</h2>
              <p className="mt-4 text-sm leading-7 text-ink-muted">
                例如：这个 wiki 当前最稳定的理解是什么？下一轮最值得补充哪条证据？哪些旧笔记还没有完成 raw 到 wiki 的迁移？
              </p>
            </>
          )}
        </PanelCard>
      </div>
    </main>
  );
}
