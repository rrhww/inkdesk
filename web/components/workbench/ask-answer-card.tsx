import Link from "next/link";
import type { ReactNode } from "react";

import type { ResearchAskResponse } from "@/lib/types";

type AskAnswerCardProps = {
  answer: ResearchAskResponse | null;
  continueFromAskTurnId?: string;
  mode: "vault" | "vault_plus_web";
  renderFollowUpHref: (question: string, mode?: "vault" | "vault_plus_web") => string;
  writebackAction: ReactNode;
};

function EmptyBlock({ children }: { children: string }) {
  return <div className="desk-panel px-4 py-4 text-sm leading-7 text-ink-muted">{children}</div>;
}

function CitationStatus({ hasVaultPath }: { hasVaultPath: boolean }) {
  return <span className={hasVaultPath ? "stamp-soft" : "slip"}>{hasVaultPath ? "已入 vault" : "未入 vault"}</span>;
}

export function AskAnswerCard({ answer, mode, renderFollowUpHref, writebackAction }: AskAnswerCardProps) {
  if (!answer) {
    return (
      <>
        <div className="slip">研究记录</div>
        <h2 className="mt-4 font-headline text-3xl font-bold tracking-[-0.03em] text-ink-text">先从一个问题开始</h2>
        <p className="mt-4 max-w-reading text-sm leading-8 text-ink-muted">
          例如：这个 wiki 当前最稳定的理解是什么？下一轮最值得补充哪条证据？哪些旧笔记还没有完成 raw 到 wiki 的迁移？
        </p>
      </>
    );
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <div className="stamp">研究记录</div>
        <div className="slip">回答</div>
      </div>
      <h2 className="mt-4 font-headline text-[clamp(2rem,3.6vw,3.2rem)] font-bold leading-[1.06] tracking-[-0.04em] text-ink-text">
        {answer.question}
      </h2>
      {answer.contextAskTurnIds.length > 0 ? (
        <div className="note-block mt-4">
          正在延续上一轮问答。新的追问会继续沿用这条 Ask 线索，而不是重新开始。
        </div>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-3 text-sm text-ink-muted">
        <span className="stamp-soft">置信度 {Math.round(answer.confidence * 100)}%</span>
        <span className="slip">{answer.usedWikiIds.length} 个 wiki 页面</span>
        <span className="slip">{answer.usedSourceIds.length} 条来源</span>
      </div>
      <div className="reading-prose mt-5 max-w-reading">
        <p>{answer.answer}</p>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        {answer.canWriteback ? (
          writebackAction
        ) : (
          <span className="rounded-full border border-black/10 bg-white/70 px-5 py-3 text-sm font-semibold text-ink-muted">
            当前回答暂不可写回
          </span>
        )}
        <span className="text-sm text-ink-muted">
          {answer.canWriteback ? "只会生成一条 ingest 提案，不会直接改写 wiki。" : "可以继续追问或补 raw，等证据更稳定后再沉淀。"}
        </span>
      </div>

      {mode === "vault" ? (
        <div className="mt-5">
          <Link
            className="inline-flex rounded-full border border-ink-primary/20 bg-ink-primarySoft px-5 py-3 text-sm font-semibold text-ink-primary"
            href={renderFollowUpHref(answer.question, "vault_plus_web")}
          >
            显式联网补料
          </Link>
        </div>
      ) : null}

      <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">知识缺口</div>
      <div className="mt-4 space-y-3">
        {answer.knowledgeGaps.length > 0 ? (
          answer.knowledgeGaps.map((gap) => (
            <div key={gap} className="note-block">
              {gap}
            </div>
          ))
        ) : (
          <EmptyBlock>当前回答没有明显证据空洞；如果你想扩大范围，可以显式联网补料。</EmptyBlock>
        )}
      </div>

      <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">外部补料</div>
      {answer.usedWebSources.length > 0 ? (
        <>
          <div className="note-block mt-4">
            这些外部资料还没有进入你的 vault。只有你点击“沉淀到 wiki”时，系统才会先把它们保存到 raw。
          </div>
          <div className="mt-4 space-y-3">
            {answer.usedWebSources.map((source) => (
              <div key={source.url} className="desk-panel px-4 py-4">
                <div className="flex flex-wrap items-center gap-3">
                  <CitationStatus hasVaultPath={false} />
                  <span className="slip">外部补料</span>
                </div>
                <div className="mt-3 font-headline text-xl font-bold tracking-[-0.03em] text-ink-text">{source.title}</div>
                <div className="mt-2 break-words text-sm text-ink-primary">{source.url}</div>
                <p className="mt-3 text-sm leading-7 text-ink-text">{source.excerpt}</p>
                <p className="mt-2 text-sm leading-7 text-ink-muted">{source.reasonUsed}</p>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="mt-4">
            <div className="desk-panel bg-white/70 px-4 py-4">
              <div className="flex flex-wrap items-center gap-3">
                <CitationStatus hasVaultPath={false} />
                <span className="slip">外部补料</span>
            </div>
            <p className="mt-3 text-sm leading-7 text-ink-muted">本次回答没有使用外部网页，完全基于当前 vault。</p>
          </div>
        </div>
      )}

      <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">继续追问</div>
      <div className="mt-4 space-y-3">
        {answer.followUpQuestions.length > 0 ? (
          answer.followUpQuestions.map((followUp) => (
            <Link
              key={followUp}
              className="desk-lift block rounded-[24px] border border-black/10 bg-white/70 px-4 py-4 text-sm leading-7 text-ink-text"
              href={renderFollowUpHref(followUp)}
            >
              <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">索引签</div>
              <div className="mt-2">{followUp}</div>
            </Link>
          ))
        ) : (
          <EmptyBlock>暂无系统建议追问，可以直接在左侧输入新的问题。</EmptyBlock>
        )}
      </div>

      <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">引用来源</div>
      <div className="mt-4 space-y-3">
        {answer.citations.length > 0 ? (
          answer.citations.map((citation) => (
            <div key={citation.sourceId} className="desk-panel px-4 py-4">
              <div className="flex flex-wrap items-center gap-3">
                <CitationStatus hasVaultPath={Boolean(citation.vaultPath)} />
                <span className="slip">{citation.kind ?? "来源"}</span>
              </div>
              <div className="mt-3 font-headline text-xl font-bold tracking-[-0.03em] text-ink-text">{citation.title}</div>
              <div className="mt-2 break-words text-sm text-ink-muted">{citation.locator || "未记录 locator"}</div>
              {citation.vaultPath ? <div className="mt-2 break-words text-sm text-ink-primary">{citation.vaultPath}</div> : null}
            </div>
          ))
        ) : (
          <EmptyBlock>暂无引用来源。建议补充 raw 或切换到显式联网补料。</EmptyBlock>
        )}
      </div>
    </>
  );
}
