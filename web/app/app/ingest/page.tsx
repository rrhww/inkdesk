import { revalidatePath } from "next/cache";

import { EmptyState } from "@/components/ui/empty-state";
import { PanelCard } from "@/components/ui/panel-card";
import { PageShell } from "@/components/workbench/page-shell";
import { ReviewCard } from "@/components/workbench/review-card";
import { OWNER_SESSION_VALUE } from "@/lib/owner-session";
import { acceptIngest, getIngestItems, rejectIngest } from "@/lib/research";
import { buildIngestRevalidationPaths } from "./revalidation-paths";

async function acceptIngestAction(formData: FormData) {
  "use server";

  const reviewId = String(formData.get("reviewId") ?? "");

  const decision = await acceptIngest(reviewId, OWNER_SESSION_VALUE);
  for (const path of buildIngestRevalidationPaths(decision.topicId)) {
    revalidatePath(path);
  }
}

async function rejectIngestAction(formData: FormData) {
  "use server";

  const reviewId = String(formData.get("reviewId") ?? "");

  await rejectIngest(reviewId, OWNER_SESSION_VALUE);
  for (const path of buildIngestRevalidationPaths()) {
    revalidatePath(path);
  }
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
  const reviews = await getIngestItems(OWNER_SESSION_VALUE);
  const resolved = searchParams ? await searchParams : undefined;
  const createdId = resolved?.created?.trim();

  return (
    <PageShell
      eyebrow="ingest"
      title="AI 编译提案队列"
      description="ingest 是 raw 到 wiki 的人工确认闸门。AI 可以提出页面创建、合并与补丁，但只有你接受后才会写入 wiki。"
    >
      {createdId ? (
        <PanelCard className="mt-6 p-5">
          <div className="text-sm leading-7 text-ink-text">
            已从 Ask 当前回答生成一条新的 ingest 提案。接下来只需要审阅这条提案，再决定是否写入 wiki。
          </div>
        </PanelCard>
      ) : null}

      <div className="mt-8 space-y-4">
        {reviews.length > 0 ? (
          reviews.map((review) => (
            <ReviewCard
              actions={
                <>
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
                </>
              }
              highlighted={createdId === review.id}
              key={review.id}
              review={review}
            />
          ))
        ) : (
          <EmptyState
            eyebrow="ingest empty"
            title="当前没有待审阅提案"
            description="这通常意味着 raw 已经处理完，或者 Ask 还没有生成可写回内容。可以回到 raw 补充材料，或用 Ask 发现新缺口。"
            actionLabel="补充 raw"
            href="/app/raw"
          />
        )}
      </div>
    </PageShell>
  );
}
