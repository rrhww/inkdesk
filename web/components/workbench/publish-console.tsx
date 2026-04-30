"use client";

import Link from "next/link";
import { type FormEvent, useTransition } from "react";

import { SectionHeading } from "@/components/ui/section-heading";
import { StatCard } from "@/components/ui/stat-card";
import { StatusPill } from "@/components/ui/status-pill";
import type { PublishDashboard } from "@/lib/types";

type PublishConsoleProps = {
  dashboard: PublishDashboard;
  publishAction?: (formData: FormData) => Promise<void>;
  unpublishAction?: (formData: FormData) => Promise<void>;
};

export function PublishConsole({ dashboard, publishAction, unpublishAction }: PublishConsoleProps) {
  const [isPending, startTransition] = useTransition();

  function submitAction(action?: (formData: FormData) => Promise<void>) {
    return (event: FormEvent<HTMLFormElement>) => {
      if (!action) {
        return;
      }

      event.preventDefault();
      const formData = new FormData(event.currentTarget);

      startTransition(async () => {
        await action(formData);
        window.location.reload();
      });
    };
  }

  return (
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      <section className="mb-8">
        <SectionHeading
          eyebrow="发布"
          title="把主系统里的内容发布到公开输出"
          description="发布模块仍然存在，但它已经不再主导产品。它的职责是把已经成熟的知识资产，从主系统整理成可对外阅读与分享的公开输出。"
        />
      </section>

      <section className="mb-8 grid gap-4 md:grid-cols-3">
        <StatCard detail="已经发布出去的知识资产" eyebrow="发布摘要" value={dashboard.summary.publishedNotes} />
        <StatCard detail="仍留在主系统里的私有资产" eyebrow="继续整理后发布" value={dashboard.summary.privateNotes} />
        <StatCard detail="正在进入计划与 Agent 工作流的资产" eyebrow="知识输出路径" value={dashboard.summary.workflowLinkedNotes} />
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="paper-card p-8">
          <SectionHeading eyebrow="已发布" title="已经稳定发布出去的知识资产" />
          <div className="mt-5 space-y-4">
            {dashboard.published.map((entry) => (
              <div key={entry.noteId} className="rounded-[24px] bg-ink-low px-5 py-5">
                <div className="flex flex-wrap items-center gap-3">
                  <StatusPill tone="soft">{entry.stateLabel}</StatusPill>
                  <span className="text-sm text-ink-muted">{entry.visibilityLabel}</span>
                </div>
                <h3 className="mt-4 font-headline text-2xl font-bold tracking-tight text-ink-text">{entry.title}</h3>
                <p className="mt-2 text-sm text-ink-muted">公开路径：{entry.publicPath ?? "待生成"}</p>
                <p className="mt-2 text-sm leading-7 text-ink-muted">{entry.excerpt}</p>
                <div className="mt-4 rounded-[20px] bg-white px-4 py-4 text-sm text-ink-muted">来源知识资产：{entry.noteId}</div>
                <div className="mt-5 flex flex-wrap gap-3">
                  {entry.publicPath ? (
                    <Link href={entry.publicPath} className="rounded-sm bg-ink-primary px-4 py-3 text-sm font-semibold text-white">
                      预览公共文章
                    </Link>
                  ) : null}
                  <Link href={`/app/notes/${entry.noteId}?state=published`} className="rounded-sm bg-white px-4 py-3 text-sm font-semibold text-ink-text">
                    回到知识资产
                  </Link>
                  {unpublishAction ? (
                    <form onSubmit={submitAction(unpublishAction)}>
                      <input name="noteId" type="hidden" value={entry.noteId} />
                      <button className="rounded-sm bg-white px-4 py-3 text-sm font-semibold text-ink-text" disabled={isPending} type="submit">
                        {isPending ? "处理中..." : "撤回到主系统"}
                      </button>
                    </form>
                  ) : (
                    <button className="rounded-sm bg-white px-4 py-3 text-sm font-semibold text-ink-text" type="button">
                      撤回到主系统
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="paper-card p-8">
          <SectionHeading eyebrow="仅主系统" title="仍需要继续整理的内容" />
          <div className="mt-5 space-y-4">
            {dashboard.drafts.map((entry) => (
              <div key={entry.noteId} className="rounded-[24px] bg-ink-low px-5 py-5">
                <div className="flex flex-wrap items-center gap-3">
                  <StatusPill tone="warm">{entry.stateLabel}</StatusPill>
                  <span className="text-sm text-ink-muted">{entry.updatedAt}</span>
                </div>
                <h3 className="mt-4 font-headline text-2xl font-bold tracking-tight text-ink-text">{entry.title}</h3>
                <p className="mt-3 text-sm leading-7 text-ink-muted">{entry.excerpt}</p>
                <div className="mt-4 rounded-[20px] bg-white px-4 py-4 text-sm text-ink-muted">来源知识资产：{entry.noteId}</div>
                <div className="mt-5 flex flex-wrap gap-3">
                  {publishAction ? (
                    <form onSubmit={submitAction(publishAction)}>
                      <input name="noteId" type="hidden" value={entry.noteId} />
                      <button className="rounded-sm bg-ink-primary px-4 py-3 text-sm font-semibold text-white" disabled={isPending} type="submit">
                        {isPending ? "处理中..." : "发布到公开输出"}
                      </button>
                    </form>
                  ) : null}
                  <Link href={`/app/notes/${entry.noteId}?state=draft`} className="rounded-sm bg-white px-4 py-3 text-sm font-semibold text-ink-text">
                    回到知识资产
                  </Link>
                  <Link href={`/app/search?q=${encodeURIComponent(entry.title)}`} className="rounded-sm bg-white px-4 py-3 text-sm font-semibold text-ink-text">
                    继续整理上下文
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
