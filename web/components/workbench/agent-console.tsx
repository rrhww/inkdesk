import Link from "next/link";

import { PanelCard } from "@/components/ui/panel-card";
import { SectionHeading } from "@/components/ui/section-heading";
import { StatCard } from "@/components/ui/stat-card";
import { StatusPill } from "@/components/ui/status-pill";
import type { WorkbenchSnapshot } from "@/lib/types";

type AgentConsoleProps = {
  snapshot: WorkbenchSnapshot;
};

export function AgentConsole({ snapshot }: AgentConsoleProps) {
  const focusSearchTerm = snapshot.focusPlan.relatedSearchTerms[0] ?? "Agent";
  const isPlaceholderFocusNote = snapshot.focusNote.id === "new-note";
  const focusNoteHref = isPlaceholderFocusNote
    ? "/app/notes/new-note?state=blank"
    : `/app/notes/${snapshot.focusNote.id}${snapshot.focusNote.published ? "?state=published" : ""}`;

  return (
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      <section className="mb-8 overflow-hidden rounded-[32px] bg-ink-primary px-6 py-7 text-white shadow-paper lg:px-8">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-[0.24em] text-white/70">工作台摘要</div>
            <h2 className="mt-4 max-w-4xl font-headline text-4xl font-extrabold tracking-tight lg:text-5xl">先让 Agent 帮你把今天的上下文排好序</h2>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-white/80">
              这里把进行中的计划、待整理的知识和待发布内容放进同一视野，让主系统先组织判断，再组织行动。
            </p>
          </div>
          <Link href={`/app/search?q=${encodeURIComponent(focusSearchTerm)}`} className="rounded-full bg-white px-5 py-3 text-sm font-semibold text-ink-primary">
            返回当前焦点
          </Link>
        </div>

        <div className="mt-7 grid gap-3 md:grid-cols-4">
          <div className="rounded-[24px] bg-white/10 px-5 py-5 backdrop-blur">
            <div className="text-[11px] uppercase tracking-[0.2em] text-white/65">进行中计划</div>
            <div className="mt-3 font-headline text-3xl font-extrabold tracking-tight">{snapshot.summary.activePlans}</div>
            <div className="mt-2 text-sm text-white/75">需要继续推进的事项</div>
          </div>
          <div className="rounded-[24px] bg-white/10 px-5 py-5 backdrop-blur">
            <div className="text-[11px] uppercase tracking-[0.2em] text-white/65">待整理知识</div>
            <div className="mt-3 font-headline text-3xl font-extrabold tracking-tight">{snapshot.summary.privateNotes}</div>
            <div className="mt-2 text-sm text-white/75">仍留在主系统里的知识草稿</div>
          </div>
          <div className="rounded-[24px] bg-white/10 px-5 py-5 backdrop-blur">
            <div className="text-[11px] uppercase tracking-[0.2em] text-white/65">待发布内容</div>
            <div className="mt-3 font-headline text-3xl font-extrabold tracking-tight">{snapshot.publishQueue.length}</div>
            <div className="mt-2 text-sm text-white/75">还没正式发布出去的资产</div>
          </div>
          <div className="rounded-[24px] bg-white/10 px-5 py-5 backdrop-blur">
            <div className="text-[11px] uppercase tracking-[0.2em] text-white/65">工作流关联</div>
            <div className="mt-3 font-headline text-3xl font-extrabold tracking-tight">{snapshot.summary.linkedNotes}</div>
            <div className="mt-2 text-sm text-white/75">正在支撑计划与 Agent 的知识资产</div>
          </div>
        </div>
      </section>

      <section className="mb-8 grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <PanelCard className="p-8">
          <SectionHeading
            eyebrow="Agent 控制台"
            title="今天先推进最关键的上下文"
            description="Agent 先读取你最近的知识资产、当前计划和公开输出，再把它们压缩成一组可以直接行动的建议。"
          />

          <div className="mt-8 rounded-[28px] bg-ink-low px-6 py-6">
            <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{snapshot.suggestions[0]?.category}</div>
            <h3 className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{snapshot.suggestions[0]?.title}</h3>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-ink-muted">{snapshot.suggestions[0]?.summary}</p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href={snapshot.suggestions[0]?.href ?? "/app/search"} className="rounded-sm bg-ink-primary px-5 py-3 text-sm font-semibold text-white">
                {snapshot.suggestions[0]?.actionLabel}
              </Link>
              <Link href="/app/plans" className="rounded-sm bg-white px-5 py-3 text-sm font-semibold text-ink-text shadow-paper">
                打开任务与计划
              </Link>
              <Link href={focusNoteHref} className="rounded-sm bg-white px-5 py-3 text-sm font-semibold text-ink-text shadow-paper">
                {isPlaceholderFocusNote ? "新建知识资产" : "查看知识资产"}
              </Link>
            </div>
            <p className="mt-4 text-sm text-ink-muted">
              {isPlaceholderFocusNote ? snapshot.focusNote.title : `当前焦点知识：${snapshot.focusNote.title}`}
            </p>
          </div>
        </PanelCard>

        <div className="space-y-6">
          <StatCard detail="当前工作台里还在推进中的计划" eyebrow="当前推进" value={snapshot.focusPlan.statusLabel} />
          <PanelCard className="p-6">
            <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">焦点计划</div>
            <h3 className="mt-4 font-headline text-2xl font-extrabold tracking-tight text-ink-text">{snapshot.focusPlan.title}</h3>
            <p className="mt-3 text-sm leading-7 text-ink-muted">{snapshot.focusPlan.nextStep}</p>
            <div className="mt-5 flex flex-wrap gap-2">
              <StatusPill tone="soft">{snapshot.focusPlan.horizonLabel}</StatusPill>
              <StatusPill>{snapshot.focusPlan.priorityLabel}</StatusPill>
            </div>
          </PanelCard>
        </div>
      </section>

      <section className="mb-8 grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <PanelCard className="p-8">
          <div className="mb-6 flex items-center justify-between">
            <div className="font-headline text-lg font-bold tracking-tight">快速动作</div>
            <span className="text-sm text-ink-muted">用最短路径回到当前工作流</span>
          </div>
          <div className="space-y-4">
            {snapshot.quickActions.map((action) => (
              <Link key={action.id} href={action.href} className="block rounded-[24px] bg-ink-low/70 px-5 py-5 hover:bg-ink-low">
                <div className="flex items-center gap-3 text-sm text-ink-muted">
                  <span className="material-symbols-outlined text-base">{action.icon}</span>
                  <span>{action.label}</span>
                </div>
                <p className="mt-3 text-sm leading-7 text-ink-muted">{action.summary}</p>
              </Link>
            ))}
          </div>
        </PanelCard>

        <PanelCard className="p-8">
          <div className="mb-6 flex items-center justify-between">
            <div className="font-headline text-lg font-bold tracking-tight">Agent 建议</div>
            <span className="text-sm text-ink-muted">按当前工作台状态排序</span>
          </div>
          <div className="space-y-4">
            {snapshot.suggestions.map((suggestion) => (
              <Link key={suggestion.id} href={suggestion.href} className="block rounded-[24px] bg-ink-low/70 px-5 py-5 hover:bg-ink-low">
                <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{suggestion.category}</div>
                <h3 className="mt-2 font-headline text-2xl font-extrabold tracking-tight text-ink-text">{suggestion.title}</h3>
                <p className="mt-3 text-sm leading-7 text-ink-muted">{suggestion.summary}</p>
                <div className="mt-4 text-sm font-semibold text-ink-primary">{suggestion.actionLabel}</div>
              </Link>
            ))}
          </div>
        </PanelCard>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <PanelCard className="p-8">
          <div className="mb-6 flex items-center justify-between">
            <div className="font-headline text-lg font-bold tracking-tight">最近知识</div>
            <Link href="/app/library" className="text-sm text-ink-primary">
              查看全部
            </Link>
          </div>
          <div className="space-y-4">
            {snapshot.recentKnowledge.map((note) => (
              <Link key={note.id} href={`/app/notes/${note.id}${note.published ? "?state=published" : ""}`} className="block rounded-[24px] bg-ink-low/70 px-5 py-5 hover:bg-ink-low">
                <div className="flex flex-wrap items-center gap-3">
                  <StatusPill tone={note.visibility === "public" ? "soft" : "neutral"}>{note.visibilityLabel}</StatusPill>
                  <span className="text-sm text-ink-muted">{note.folder}</span>
                </div>
                <h3 className="mt-3 font-headline text-2xl font-extrabold tracking-tight text-ink-text">{note.title}</h3>
                <p className="mt-3 text-sm leading-7 text-ink-muted">{note.excerpt}</p>
              </Link>
            ))}
          </div>
        </PanelCard>

        <PanelCard className="p-8">
          <div className="mb-6 flex items-center justify-between">
            <div className="font-headline text-lg font-bold tracking-tight">待发布内容</div>
            <Link href="/app/publish" className="text-sm text-ink-primary">
              进入发布
            </Link>
          </div>
          <div className="space-y-4">
            {snapshot.publishQueue.map((entry) => (
              <div key={entry.noteId} className="rounded-[24px] bg-ink-low/70 px-5 py-5">
                <div className="flex items-center justify-between gap-4">
                  <StatusPill tone="warm">{entry.stateLabel}</StatusPill>
                  <span className="text-sm text-ink-muted">{entry.updatedAt}</span>
                </div>
                <h3 className="mt-3 font-headline text-2xl font-extrabold tracking-tight text-ink-text">{entry.title}</h3>
                <p className="mt-3 text-sm leading-7 text-ink-muted">{entry.excerpt}</p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <Link href={`/app/notes/${entry.noteId}`} className="rounded-sm bg-white px-4 py-3 text-sm font-semibold text-ink-text shadow-paper">
                    返回当前焦点
                  </Link>
                  <Link href="/app/publish" className="rounded-sm bg-white px-4 py-3 text-sm font-semibold text-ink-text shadow-paper">
                    打开发布控制台
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </PanelCard>
      </section>
    </main>
  );
}
