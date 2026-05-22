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
  return <div className="rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-muted">{children}</div>;
}

export function AskAnswerCard({ answer, mode, renderFollowUpHref, writebackAction }: AskAnswerCardProps) {
  if (!answer) {
    return (
      <>
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">回答</div>
        <h2 className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">先从一个问题开始</h2>
        <p className="mt-4 text-sm leading-7 text-ink-muted">
          例如：这个 wiki 当前最稳定的理解是什么？下一轮最值得补充哪条证据？哪些旧笔记还没有完成 raw 到 wiki 的迁移？
        </p>
      </>
    );
  }

  return (
    <>
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">回答</div>
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
        {answer.canWriteback ? (
          writebackAction
        ) : (
          <span className="rounded-full bg-ink-low px-5 py-3 text-sm font-semibold text-ink-muted">当前回答暂不可写回</span>
        )}
        <span className="text-sm text-ink-muted">
          {answer.canWriteback ? "只会生成一条 ingest 提案，不会直接改写 wiki。" : "可以继续追问或补 raw，等证据更稳定后再沉淀。"}
        </span>
      </div>

      {mode === "vault" ? (
        <div className="mt-5">
          <Link
            className="inline-flex rounded-full bg-ink-primarySoft px-5 py-3 text-sm font-semibold text-ink-primary"
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
            <div key={gap} className="rounded-[22px] bg-[#fff5e9] px-4 py-4 text-sm leading-7 text-ink-text">
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
          <div className="mt-4 rounded-[22px] bg-[#fff5e9] px-4 py-4 text-sm leading-7 text-ink-text">
            这些外部资料还没有进入你的 vault。只有你点击“沉淀到 wiki”时，系统才会先把它们保存到 raw。
          </div>
          <div className="mt-4 space-y-3">
            {answer.usedWebSources.map((source) => (
              <div key={source.url} className="rounded-[22px] bg-ink-low px-4 py-4">
                <div className="font-headline text-xl font-bold tracking-tight text-ink-text">{source.title}</div>
                <div className="mt-2 break-words text-sm text-ink-primary">{source.url}</div>
                <p className="mt-3 text-sm leading-7 text-ink-text">{source.excerpt}</p>
                <p className="mt-2 text-sm leading-7 text-ink-muted">{source.reasonUsed}</p>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="mt-4">
          <EmptyBlock>本次回答没有使用外部网页，完全基于当前 vault。</EmptyBlock>
        </div>
      )}

      <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">继续追问</div>
      <div className="mt-4 space-y-3">
        {answer.followUpQuestions.length > 0 ? (
          answer.followUpQuestions.map((followUp) => (
            <Link
              key={followUp}
              className="block rounded-[22px] bg-ink-low px-4 py-4 text-sm leading-7 text-ink-text hover:bg-white"
              href={renderFollowUpHref(followUp)}
            >
              {followUp}
            </Link>
          ))
        ) : (
          <EmptyBlock>暂无系统建议追问，可以直接在左侧输入新的问题。</EmptyBlock>
        )}
      </div>

      <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">引用来源</div>
      <div className="mt-4 space-y-3">
        {answer.citations.length > 0 ? (
          answer.citations.map((citation, index) => (
            <div
              key={citation.chunkId ?? citation.id ?? `${citation.sourceId ?? citation.title}-${citation.locator ?? index}`}
              className="rounded-[22px] bg-ink-low px-4 py-4"
            >
              <div className="font-headline text-xl font-bold tracking-tight text-ink-text">{citation.title}</div>
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
