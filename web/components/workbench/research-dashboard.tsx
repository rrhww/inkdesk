import Link from "next/link";

import { PanelCard } from "@/components/ui/panel-card";
import { SectionHeading } from "@/components/ui/section-heading";
import { StatCard } from "@/components/ui/stat-card";
import type { ResearchDashboard } from "@/lib/types";

type ResearchDashboardProps = {
  snapshot: ResearchDashboard;
};

export function ResearchDashboardView({ snapshot }: ResearchDashboardProps) {
  return (
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      <section className="rounded-[32px] bg-[linear-gradient(135deg,#0f3d39_0%,#1e5b57_55%,#d7ede3_100%)] px-6 py-8 text-white shadow-paper lg:px-8">
        <SectionHeading
          eyebrow="Today Vault Panel"
          title="raw 进入 vault，ingest 编译提案，wiki 沉淀知识"
          description="Inkvault 现在是一个私有 LLM Wiki：raw 保存网页、PDF 和迁移材料，AI 只在 ingest 里提出补丁，最后由你确认哪些变化写入 wiki。"
        />
        <div className="mt-8 grid gap-4 md:grid-cols-4">
          <StatCard eyebrow="Wiki Pages" value={snapshot.summary.activeTopics} detail="已经写入 vault 的知识页" />
          <StatCard eyebrow="Ingest Queue" value={snapshot.summary.pendingReviews} detail="等待接受或忽略的 AI 提案" />
          <StatCard eyebrow="Raw Pending" value={snapshot.summary.inboxSources} detail="还没编译进 wiki 的原始材料" />
          <StatCard eyebrow="Raw Files" value={snapshot.summary.totalSources} detail="已经建立索引与溯源的材料" />
        </div>
      </section>

      <section className="mt-8 grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <PanelCard className="p-8">
          <div className="flex items-start justify-between gap-6">
            <div>
              <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">焦点 wiki</div>
              <h2 className="mt-3 font-headline text-4xl font-extrabold tracking-tight text-ink-text">
                {snapshot.focusTopic?.title ?? "等待确认第一个研究主题"}
              </h2>
              <p className="mt-4 max-w-3xl text-sm leading-7 text-ink-muted">
                {snapshot.focusTopic?.summary ?? "先从 raw 里确认第一批来源，再建立你的第一个 wiki 页面。"}
              </p>
            </div>
            <Link
              className="rounded-full bg-ink-primary px-5 py-3 text-sm font-semibold text-white"
              href={snapshot.focusTopic ? `/app/wiki/${snapshot.focusTopic.id}` : "/app/ingest"}
            >
              {snapshot.focusTopic ? "打开 wiki" : "前往 ingest"}
            </Link>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <div className="rounded-[24px] bg-ink-low px-5 py-5">
              <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">ingest 提案</div>
              <div className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">
                {snapshot.pendingReviews.length}
              </div>
              <p className="mt-2 text-sm text-ink-muted">每条 AI 变更都需要显式进入 ingest，而不是直接改写 wiki。</p>
            </div>
            <div className="rounded-[24px] bg-ink-low px-5 py-5">
              <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">建议提问</div>
              <div className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">
                {snapshot.suggestedQuestions.length}
              </div>
              <p className="mt-2 text-sm text-ink-muted">优先用 Ask 在已有 wiki 上提问，再决定是否要导入新 raw。</p>
            </div>
          </div>
        </PanelCard>

        <div className="space-y-6">
          <PanelCard className="p-6">
            <div className="flex items-center justify-between">
              <div className="font-headline text-lg font-bold tracking-tight">ingest 队列</div>
              <Link className="text-sm text-ink-primary" href="/app/ingest">
                查看全部
              </Link>
            </div>
            <div className="mt-5 space-y-3">
              {snapshot.pendingReviews.slice(0, 3).map((review) => (
                <div key={review.id} className="rounded-[22px] bg-ink-low px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{review.kind}</div>
                  <div className="mt-2 font-headline text-xl font-bold tracking-tight text-ink-text">{review.title}</div>
                  <p className="mt-2 text-sm leading-7 text-ink-muted">{review.summary}</p>
                </div>
              ))}
            </div>
          </PanelCard>

          <PanelCard className="p-6">
            <div className="flex items-center justify-between">
              <div className="font-headline text-lg font-bold tracking-tight">建议提问</div>
              <Link className="text-sm text-ink-primary" href="/app/ask">
                打开 Ask
              </Link>
            </div>
            <div className="mt-5 space-y-3">
              {snapshot.suggestedQuestions.map((question) => (
                <Link
                  key={question}
                  className="block rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-text hover:bg-white"
                  href={`/app/ask?q=${encodeURIComponent(question)}${snapshot.focusTopic ? `&topicId=${snapshot.focusTopic.id}` : ""}`}
                >
                  {question}
                </Link>
              ))}
            </div>
          </PanelCard>
        </div>
      </section>

      <section className="mt-8 grid gap-6 xl:grid-cols-2">
        <PanelCard className="p-8">
          <div className="flex items-center justify-between">
            <div className="font-headline text-lg font-bold tracking-tight">最新 raw</div>
            <Link className="text-sm text-ink-primary" href="/app/raw">
              查看 raw vault
            </Link>
          </div>
          <div className="mt-6 space-y-4">
            {snapshot.recentSources.map((source) => (
              <div key={source.id} className="rounded-[24px] bg-ink-low px-5 py-5">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="rounded-full bg-white px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-ink-muted">
                    {source.kind}
                  </span>
                  <span className="rounded-full bg-ink-primarySoft px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-ink-primary">
                    {source.status}
                  </span>
                </div>
                <h3 className="mt-3 font-headline text-2xl font-extrabold tracking-tight text-ink-text">{source.title}</h3>
                <p className="mt-3 text-sm leading-7 text-ink-muted">{source.excerpt}</p>
                {source.locator ? <p className="mt-3 text-sm text-ink-muted">{source.locator}</p> : null}
                {source.vaultPath ? <p className="mt-2 text-sm text-ink-primary">{source.vaultPath}</p> : null}
              </div>
            ))}
          </div>
        </PanelCard>

        <PanelCard className="p-8">
          <div className="flex items-center justify-between">
            <div className="font-headline text-lg font-bold tracking-tight">下一步路径</div>
            <Link className="text-sm text-ink-primary" href="/app/raw">
              回到 raw
            </Link>
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <Link className="rounded-[24px] bg-ink-low px-5 py-5 hover:bg-white" href="/app/raw">
              <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">1. raw</div>
              <h3 className="mt-3 font-headline text-2xl font-extrabold tracking-tight text-ink-text">先收新来源</h3>
              <p className="mt-3 text-sm leading-7 text-ink-muted">网页、PDF 和迁移材料都会先进入 raw 文件，再决定如何进入 wiki。</p>
            </Link>
            <Link className="rounded-[24px] bg-ink-low px-5 py-5 hover:bg-white" href="/app/ingest">
              <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">2. ingest</div>
              <h3 className="mt-3 font-headline text-2xl font-extrabold tracking-tight text-ink-text">再审 AI 提案</h3>
              <p className="mt-3 text-sm leading-7 text-ink-muted">页面创建、合并与补丁都必须显式通过 ingest，防止静默改写长期记忆。</p>
            </Link>
            <Link className="rounded-[24px] bg-ink-low px-5 py-5 hover:bg-white" href="/app/wiki">
              <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">3. wiki</div>
              <h3 className="mt-3 font-headline text-2xl font-extrabold tracking-tight text-ink-text">维护编译结果</h3>
              <p className="mt-3 text-sm leading-7 text-ink-muted">每个 wiki 页面都保留当前理解、开放问题、关键论断和来源链接。</p>
            </Link>
            <Link className="rounded-[24px] bg-ink-low px-5 py-5 hover:bg-white" href="/app/ask">
              <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">4. Ask</div>
              <h3 className="mt-3 font-headline text-2xl font-extrabold tracking-tight text-ink-text">在现有记忆上提问</h3>
              <p className="mt-3 text-sm leading-7 text-ink-muted">先问已有 wiki 和 raw 能回答什么，再决定是否需要新导入或继续编译。</p>
            </Link>
          </div>
        </PanelCard>
      </section>
    </main>
  );
}
