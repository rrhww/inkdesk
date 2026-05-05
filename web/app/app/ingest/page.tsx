import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { PanelCard } from "@/components/ui/panel-card";
import { SectionHeading } from "@/components/ui/section-heading";
import { OWNER_SESSION_COOKIE } from "@/lib/owner-session";
import { getRequestOwnerSession } from "@/lib/request-owner-session";
import { acceptIngest, getIngestItems, rejectIngest } from "@/lib/research";

async function acceptIngestAction(formData: FormData) {
  "use server";

  const reviewId = String(formData.get("reviewId") ?? "");
  const cookieStore = await cookies();

  await acceptIngest(reviewId, cookieStore.get(OWNER_SESSION_COOKIE)?.value);
  revalidatePath("/app");
  revalidatePath("/app/ingest");
  revalidatePath("/app/wiki");
  revalidatePath("/app/raw");
}

async function rejectIngestAction(formData: FormData) {
  "use server";

  const reviewId = String(formData.get("reviewId") ?? "");
  const cookieStore = await cookies();

  await rejectIngest(reviewId, cookieStore.get(OWNER_SESSION_COOKIE)?.value);
  revalidatePath("/app");
  revalidatePath("/app/ingest");
  revalidatePath("/app/raw");
}

type IngestPageProps = {
  searchParams?: Promise<{
    created?: string;
  }>;
};

export default async function IngestPage(props: IngestPageProps) {
  return IngestPageContent({ searchParams: props.searchParams });
}

async function IngestPageContent({ searchParams }: IngestPageProps = {}) {
  const reviews = await getIngestItems(await getRequestOwnerSession());
  const resolved = searchParams ? await searchParams : undefined;
  const createdId = resolved?.created?.trim();

  return (
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      <SectionHeading
        eyebrow="ingest"
        title="AI 编译提案队列"
        description="ingest 是 raw 到 wiki 的人工确认闸门。AI 可以提出页面创建、合并与补丁，但只有你接受后才会写入 wiki。"
      />

      {createdId ? (
        <PanelCard className="mt-6 p-5">
          <div className="text-sm leading-7 text-ink-text">
            已从 Ask 当前回答生成一条新的 ingest 提案。接下来只需要审阅这条提案，再决定是否写入 wiki。
          </div>
        </PanelCard>
      ) : null}

      <div className="mt-8 space-y-4">
        {reviews.map((review) => (
          <PanelCard
            key={review.id}
            className={`p-6 ${createdId === review.id ? "ring-2 ring-ink-primary/20" : ""}`}
          >
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-full bg-ink-low px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-ink-muted">
                {review.kind}
              </span>
              {review.targetTopicTitle ? (
                <span className="rounded-full bg-ink-primarySoft px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-ink-primary">
                  {review.targetTopicTitle}
                </span>
              ) : null}
            </div>
            <h2 className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{review.title}</h2>
            <p className="mt-3 text-sm leading-7 text-ink-muted">{review.summary}</p>

            <div className="mt-5 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
              <div className="space-y-4">
                <div className="rounded-[22px] bg-ink-low px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">Topic 归属</div>
                  <p className="mt-3 text-sm leading-7 text-ink-text">
                    {review.proposalPayload?.topicDecision.decision === "PATCH"
                      ? `建议补进现有 wiki「${review.proposalPayload.topicDecision.targetTopicTitle ?? review.targetTopicTitle ?? "未命名主题"}」`
                      : `建议新建 wiki「${review.proposalPayload?.topicDecision.proposedTopicTitle ?? review.proposedTopicTitle ?? "未命名主题"}」`}
                  </p>
                </div>

                <div className="rounded-[22px] bg-ink-low px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">提案解释</div>
                  <p className="mt-3 text-sm leading-7 text-ink-text">
                    {review.proposalPayload?.explanation ?? review.proposedUnderstanding ?? review.summary}
                  </p>
                </div>

                {review.proposalPayload?.summaryChanges?.length ? (
                  <div className="rounded-[22px] bg-white px-4 py-4">
                    <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">建议写入</div>
                    <div className="mt-3 space-y-2">
                      {review.proposalPayload.summaryChanges.map((change) => (
                        <p key={change} className="text-sm leading-7 text-ink-text">
                          {change}
                        </p>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>

              <div className="space-y-4">
                {review.proposalPayload?.claims?.length ? (
                  <div className="rounded-[22px] bg-white px-4 py-4">
                    <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">Key Claims</div>
                    <div className="mt-3 space-y-3">
                      {review.proposalPayload.claims.map((claim) => (
                        <div key={`${review.id}-${claim.statement}`} className="rounded-[18px] bg-ink-low px-4 py-4">
                          <p className="text-sm leading-7 text-ink-text">{claim.statement}</p>
                          <p className="mt-2 text-sm text-ink-muted">{claim.citationLabel}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                {review.proposalPayload?.evidence?.length ? (
                  <div className="rounded-[22px] bg-white px-4 py-4">
                    <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">证据来源</div>
                    <div className="mt-3 space-y-3">
                      {review.proposalPayload.evidence.map((evidence) => (
                        <div key={`${review.id}-${evidence.sourceId}`} className="rounded-[18px] bg-ink-low px-4 py-4">
                          <div className="font-semibold text-ink-text">{evidence.sourceTitle}</div>
                          <p className="mt-2 text-sm leading-7 text-ink-text">{evidence.excerpt}</p>
                          {evidence.locator ? <p className="mt-2 text-sm text-ink-muted">{evidence.locator}</p> : null}
                          {evidence.sourceVaultPath ? <p className="mt-2 text-sm text-ink-primary">{evidence.sourceVaultPath}</p> : null}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                {review.proposalPayload?.openQuestions?.length ? (
                  <div className="rounded-[22px] bg-white px-4 py-4">
                    <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">Open Questions</div>
                    <div className="mt-3 space-y-2">
                      {review.proposalPayload.openQuestions.map((item) => (
                        <p key={item} className="text-sm leading-7 text-ink-text">
                          {item}
                        </p>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="mt-4 grid gap-3 text-sm text-ink-muted md:grid-cols-2">
              {review.sourceVaultPath ? <div>raw: {review.sourceVaultPath}</div> : null}
              {review.proposedVaultPath ? <div>wiki: {review.proposedVaultPath}</div> : null}
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              <form action={acceptIngestAction}>
                <input name="reviewId" type="hidden" value={review.id} />
                <button className="rounded-full bg-ink-primary px-5 py-3 text-sm font-semibold text-white" type="submit">
                  接受写入 wiki
                </button>
              </form>
              <form action={rejectIngestAction}>
                <input name="reviewId" type="hidden" value={review.id} />
                <button className="rounded-full bg-ink-low px-5 py-3 text-sm font-semibold text-ink-text" type="submit">
                  忽略提案
                </button>
              </form>
            </div>
          </PanelCard>
        ))}
      </div>
    </main>
  );
}
