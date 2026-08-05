"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertTriangle, ArrowLeft, BookOpen, Code2, ExternalLink, FileText, Network, RefreshCw } from "lucide-react";

import { ServerAPI, type KnowledgeBriefing } from "@/lib/server-api";

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "更新时间未知";
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "long" }).format(date);
}

function Section({ eyebrow, title, children }: { eyebrow: string; title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-slate-200 py-7">
      <p className="font-mono text-[10px] font-semibold uppercase tracking-widest text-emerald-700">{eyebrow}</p>
      <h2 className="mt-2 text-lg font-semibold text-slate-950">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export default function KnowledgeBriefingPage() {
  const params = useParams<{ id: string }>();
  const [briefing, setBriefing] = useState<KnowledgeBriefing | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let active = true;
    ServerAPI.fetchKnowledgeBriefing(String(params.id))
      .then((payload) => {
        if (!active) return;
        setBriefing(payload);
        setStatus("ready");
      })
      .catch(() => {
        if (active) setStatus("error");
      });
    return () => {
      active = false;
    };
  }, [params.id]);

  if (status === "loading") {
    return <main className="grid h-dvh place-items-center bg-[#F8FAFC] font-mono text-xs tracking-widest text-slate-500">ASSEMBLING TOPIC BRIEFING</main>;
  }

  if (status === "error" || !briefing) {
    return (
      <main className="grid h-dvh place-items-center bg-[#F8FAFC] px-6 text-center">
        <div>
          <p role="alert" className="text-sm font-semibold text-rose-700">主题简报暂不可用</p>
          <Link href="/app/wiki" className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-emerald-700">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />返回知识看板
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="h-dvh w-full overflow-y-auto bg-[#F8FAFC] text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <Link href="/app/wiki" className="inline-flex h-10 items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-950">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />知识看板
          </Link>
          <Link href="/app/wiki/graph" className="inline-flex h-10 items-center gap-2 border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 hover:border-slate-400">
            <Network className="h-4 w-4" aria-hidden="true" />关系图
          </Link>
        </div>
      </header>

      <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_18rem]">
          <div className="min-w-0">
            <p className="font-mono text-[10px] font-semibold uppercase tracking-widest text-emerald-700">
              TOPIC BRIEFING / {briefing.confidence >= 0.75 ? "supported" : briefing.confidence >= 0.5 ? "partial" : "unknown"}
            </p>
            <h1 className="mt-3 text-3xl font-semibold leading-tight">{briefing.title}</h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">{briefing.summary || "该主题尚未形成稳定摘要。"}</p>
            <div className="mt-5 flex flex-wrap gap-3 text-sm"><a href={`/api/knowledge/topics/${encodeURIComponent(briefing.id)}/document`} target="_blank" rel="noreferrer" className="inline-flex h-10 items-center gap-2 border border-slate-300 bg-white px-3 hover:border-emerald-600"><ExternalLink className="h-4 w-4" />打开原文</a><span className="inline-flex h-10 items-center border border-slate-200 px-3 text-xs text-slate-500">来源覆盖：{briefing.provenanceStatus ?? "unknown"}</span></div>

            <Section eyebrow="CURRENT UNDERSTANDING" title="当前理解">
              {briefing.currentUnderstanding.length > 0 ? (
                <ul className="space-y-3">
                  {briefing.currentUnderstanding.map((item) => <li key={item} className="border-l-2 border-emerald-600 pl-4 text-sm leading-7 text-slate-700">{item}</li>)}
                </ul>
              ) : <p className="text-sm text-slate-500">尚未提炼出稳定理解。</p>}
            </Section>

            <Section eyebrow="KEY DECISIONS" title="关键决策">
              {briefing.keyDecisions.length > 0 ? (
                <ol className="space-y-3">
                  {briefing.keyDecisions.map((item, index) => <li key={item} className="flex gap-3 text-sm leading-7 text-slate-700"><span className="font-mono text-emerald-700">{String(index + 1).padStart(2, "0")}</span><span>{item}</span></li>)}
                </ol>
              ) : <p className="text-sm text-slate-500">原文没有标记明确决策。</p>}
            </Section>

            <Section eyebrow="OPEN QUESTIONS" title="未解问题">
              {briefing.openQuestions.length > 0 ? (
                <ul className="space-y-3">
                  {briefing.openQuestions.map((item) => <li key={item} className="flex gap-3 text-sm leading-7 text-slate-700"><AlertTriangle className="mt-1.5 h-4 w-4 shrink-0 text-amber-600" aria-hidden="true" /><span>{item}</span></li>)}
                </ul>
              ) : <p className="text-sm text-slate-500">当前没有从文档中识别出未解问题。</p>}
            </Section>

            <Section eyebrow="SOURCES" title="来源与相关资料">
              {briefing.sources.length > 0 ? (
                <div className="divide-y divide-slate-200 border-y border-slate-200">
                  {briefing.sources.map((source) => (
                    <a href={source.href ?? `/api/knowledge/documents/${encodeURIComponent(source.documentId)}`} target="_blank" rel="noreferrer" key={source.id} className="flex gap-4 py-4 hover:bg-slate-50">
                      <FileText className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-slate-900">{source.title}</p>
                        <p className="mt-1 break-all font-mono text-[10px] text-slate-500">{source.path}</p>
                        {source.summary ? <p className="mt-2 text-sm leading-6 text-slate-600">{source.summary}</p> : null}
                      </div>
                    </a>
                  ))}
                </div>
              ) : <p className="text-sm text-slate-500">该主题尚未关联其他来源。</p>}
            </Section>

            <Section eyebrow="RELATED TOPICS" title="关联主题">
              {briefing.relatedTopics.length > 0 ? <div className="flex flex-wrap gap-2">{briefing.relatedTopics.map((topic) => <Link key={topic.id} href={`/app/wiki/${topic.id}`} className="border border-slate-200 px-3 py-2 text-sm hover:border-emerald-600 hover:text-emerald-700">{topic.title}</Link>)}</div> : <p className="text-sm text-slate-500">当前没有可导航的关联主题。</p>}
            </Section>
          </div>

          <aside className="space-y-5 lg:sticky lg:top-6 lg:self-start">
            <div className="border border-slate-200 bg-white p-5">
              <div className="flex items-center gap-2 text-sm font-semibold"><BookOpen className="h-4 w-4 text-emerald-700" aria-hidden="true" />主题状态</div>
              <dl className="mt-4 space-y-3 text-xs">
                <div className="flex justify-between gap-3"><dt className="text-slate-500">可信度</dt><dd className="font-mono font-semibold">{Math.round(briefing.confidence * 100)}%</dd></div>
                <div className="flex justify-between gap-3"><dt className="text-slate-500">来源</dt><dd className="font-mono font-semibold">{briefing.sourceCount}</dd></div>
                <div className="flex justify-between gap-3"><dt className="text-slate-500">更新时间</dt><dd className="text-right font-medium">{formatDate(briefing.updatedAt)}</dd></div>
              </dl>
              <p className="mt-4 break-all border-t border-slate-100 pt-4 font-mono text-[10px] leading-5 text-slate-500">{briefing.path}</p>
            </div>

            {briefing.signals.length > 0 ? (
              <div className="border border-amber-200 bg-amber-50 p-5">
                <div className="flex items-center gap-2 text-sm font-semibold text-amber-900"><AlertTriangle className="h-4 w-4" aria-hidden="true" />知识信号</div>
                <ul className="mt-4 space-y-3">
                  {briefing.signals.map((signal) => <li key={`${signal.type}-${signal.title}`} className="text-xs leading-5 text-amber-900"><span className="font-semibold">{signal.title}</span><br />{signal.detail}</li>)}
                </ul>
              </div>
            ) : null}

            {briefing.codePaths.length > 0 ? (
              <div className="border border-slate-200 bg-white p-5">
                <div className="flex items-center gap-2 text-sm font-semibold"><Code2 className="h-4 w-4 text-emerald-700" aria-hidden="true" />相关代码路径</div>
                <ul className="mt-4 space-y-2">
                  {briefing.codePaths.map((path) => <li key={path} className="break-all font-mono text-[10px] leading-5 text-slate-600">{path}</li>)}
                </ul>
              </div>
            ) : null}

            <button type="button" onClick={() => window.location.reload()} className="inline-flex h-10 w-full items-center justify-center gap-2 border border-slate-300 bg-white text-sm font-medium text-slate-700 hover:border-slate-500">
              <RefreshCw className="h-4 w-4" aria-hidden="true" />刷新简报
            </button>
          </aside>
        </div>
      </div>
    </main>
  );
}
