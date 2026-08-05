"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  FileText,
  Network,
  RefreshCw,
  Search,
  type LucideIcon,
} from "lucide-react";

import {
  ServerAPI,
  type KnowledgeSearchResult,
  type KnowledgeTopic,
  type KnowledgeTopicList,
} from "@/lib/server-api";

type LoadState = "loading" | "ready" | "empty" | "error";

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "更新时间未知";
  return new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "short", day: "numeric" }).format(date);
}

function signalLabel(topic: KnowledgeTopic) {
  if (topic.signals.some((signal) => signal.severity === "critical")) return "需要处理";
  if (topic.signals.length > 0) return "需要关注";
  return "内容稳定";
}

function TopicCard({ topic }: { topic: KnowledgeTopic }) {
  const attention = topic.signals.length > 0;

  return (
    <article className="group flex min-h-[17rem] flex-col border border-slate-200 bg-white p-5 transition-colors hover:border-slate-400">
      <div className="flex items-start justify-between gap-3">
        <span className="font-mono text-[10px] font-semibold uppercase tracking-widest text-emerald-700">
          {topic.kind} / {topic.source}
        </span>
        <span
          className={`inline-flex items-center gap-1.5 text-xs font-medium ${attention ? "text-amber-700" : "text-emerald-700"}`}
        >
          {attention ? <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" /> : null}
          {signalLabel(topic)}
        </span>
      </div>

      <h2 className="mt-5 text-lg font-semibold leading-7 text-slate-950">{topic.title}</h2>
      <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-600">
        {topic.summary || "该主题尚未形成摘要，打开简报查看原始资料并补充当前理解。"}
      </p>

      <dl className="mt-5 grid grid-cols-2 gap-3 border-y border-slate-100 py-4 text-xs">
        <div>
          <dt className="text-slate-500">关联来源</dt>
          <dd className="mt-1 font-mono font-semibold text-slate-900">{topic.sourceCount}</dd>
        </div>
        <div>
          <dt className="text-slate-500">未解问题</dt>
          <dd className="mt-1 font-mono font-semibold text-slate-900">{topic.openQuestionCount}</dd>
        </div>
      </dl>

      <div className="mt-auto flex items-end justify-between gap-4 pt-5">
        <div className="min-w-0">
          <p className="truncate font-mono text-[10px] text-slate-400">{topic.path}</p>
          <p className="mt-1 text-xs text-slate-500">{formatDate(topic.updatedAt)}</p>
        </div>
        <Link
          href={`/app/wiki/${topic.id}`}
          aria-label={`打开 ${topic.title} 主题简报`}
          className="grid h-10 w-10 shrink-0 place-items-center border border-slate-200 text-slate-500 transition-colors group-hover:border-emerald-600 group-hover:text-emerald-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600"
        >
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Link>
      </div>
    </article>
  );
}

export function KnowledgeBoard() {
  const [catalog, setCatalog] = useState<KnowledgeTopicList | null>(null);
  const [results, setResults] = useState<KnowledgeSearchResult | null>(null);
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [status, setStatus] = useState<LoadState>("loading");

  const loadTopics = useCallback(async () => {
    setStatus("loading");
    setResults(null);
    setSubmittedQuery("");
    try {
      const payload = await ServerAPI.fetchKnowledgeTopics();
      setCatalog(payload);
      setStatus(payload.topics.length > 0 ? "ready" : "empty");
    } catch {
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    let active = true;
    ServerAPI.fetchKnowledgeTopics()
      .then((payload) => {
        if (!active) return;
        setCatalog(payload);
        setStatus(payload.topics.length > 0 ? "ready" : "empty");
      })
      .catch(() => {
        if (active) setStatus("error");
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let timer: number | null = null;
    const unsubscribe = ServerAPI.subscribeToKnowledgeEvents?.(() => {
      if (timer !== null) window.clearTimeout(timer);
      timer = window.setTimeout(() => { void loadTopics(); }, 250);
    });
    return () => {
      if (timer !== null) window.clearTimeout(timer);
      unsubscribe?.();
    };
  }, [loadTopics]);

  const topics = results?.results ?? catalog?.topics ?? [];
  const stats = useMemo(
    () =>
      catalog?.stats ?? {
        topicCount: 0,
        sourceCount: 0,
        signalCount: 0,
      },
    [catalog],
  );
  const overviewStats: Array<{ label: string; value: number; icon: LucideIcon }> = [
    { label: "知识主题", value: stats.topicCount, icon: BookOpen },
    { label: "关联来源", value: stats.sourceCount, icon: FileText },
    { label: "需要关注", value: stats.signalCount, icon: AlertTriangle },
  ];

  async function submitSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = query.trim();
    if (!normalized) {
      await loadTopics();
      return;
    }
    setStatus("loading");
    setSubmittedQuery(normalized);
    try {
      const payload = await ServerAPI.searchKnowledge(normalized);
      setResults(payload);
      setStatus(payload.results.length > 0 ? "ready" : "empty");
    } catch {
      setStatus("error");
    }
  }

  return (
    <main className="h-dvh w-full overflow-y-auto bg-[#F8FAFC] text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-[90rem] flex-col gap-5 px-4 py-5 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center bg-slate-950 text-white">
              <BookOpen className="h-5 w-5" aria-hidden="true" strokeWidth={1.5} />
            </div>
            <div>
              <h1 className="text-lg font-semibold">Inkdesk 知识看板</h1>
              <p className="mt-0.5 text-xs text-slate-500">项目当前理解、关键决策与可信来源</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              title="刷新知识索引"
              aria-label="刷新知识索引"
              onClick={() => void loadTopics()}
              className="grid h-10 w-10 place-items-center border border-slate-200 bg-white text-slate-600 hover:border-slate-400 hover:text-slate-950 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
            </button>
            <Link
              href="/app/wiki/graph"
              className="inline-flex h-10 items-center gap-2 border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 hover:border-slate-400 hover:text-slate-950 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600"
            >
              <Network className="h-4 w-4" aria-hidden="true" />
              关系图
            </Link>
          </div>
        </div>
      </header>

      <div className="mx-auto w-full max-w-[90rem] px-4 py-7 sm:px-6 lg:px-8">
        <section aria-label="知识概览" className="grid border border-slate-200 bg-white sm:grid-cols-3">
          {overviewStats.map(({ label, value, icon: Icon }, index) => (
            <div key={String(label)} className={`flex items-center gap-4 p-5 ${index > 0 ? "border-t border-slate-200 sm:border-l sm:border-t-0" : ""}`}>
              <Icon className="h-5 w-5 text-slate-400" aria-hidden="true" strokeWidth={1.5} />
              <div>
                <div className="font-mono text-xl font-semibold tabular-nums">{String(value)}</div>
                <div className="mt-1 text-xs text-slate-500">{String(label)}</div>
              </div>
            </div>
          ))}
        </section>

        <form onSubmit={submitSearch} className="mt-6 flex w-full items-stretch border border-slate-300 bg-white focus-within:border-emerald-600">
          <Search className="ml-4 mt-3.5 h-5 w-5 shrink-0 text-slate-400" aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索模块、业务概念或历史决策"
            aria-label="搜索知识主题"
            className="h-12 min-w-0 flex-1 bg-transparent px-3 text-sm outline-none placeholder:text-slate-400"
          />
          <button type="submit" className="h-12 shrink-0 bg-slate-950 px-5 text-sm font-medium text-white hover:bg-emerald-700">
            生成主题简报
          </button>
        </form>

        <div className="mt-8 flex items-end justify-between gap-4">
          <div>
            <p className="font-mono text-[10px] font-semibold uppercase tracking-widest text-emerald-700">
              {submittedQuery ? "SEARCH RESULTS" : "KNOWLEDGE TOPICS"}
            </p>
            <h2 className="mt-2 text-xl font-semibold">
              {submittedQuery ? `与“${submittedQuery}”相关的主题` : "项目知识主题"}
            </h2>
          </div>
          {submittedQuery ? (
            <button type="button" onClick={() => void loadTopics()} className="text-sm font-medium text-emerald-700 hover:text-emerald-900">
              返回全部主题
            </button>
          ) : null}
        </div>

        {status === "ready" ? (
          <section aria-label="知识主题列表" className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {topics.map((topic) => <TopicCard key={topic.id} topic={topic} />)}
          </section>
        ) : null}

        {status === "loading" ? (
          <div role="status" className="mt-5 border border-slate-200 bg-white px-6 py-16 text-center font-mono text-xs tracking-widest text-slate-500">
            BUILDING KNOWLEDGE BRIEFING
          </div>
        ) : null}

        {status === "empty" ? (
          <div className="mt-5 border border-slate-200 bg-white px-6 py-16 text-center">
            <p className="text-sm font-semibold">没有找到可用主题</p>
            <p className="mt-2 text-sm text-slate-500">检查检索词，或在 Vault 与项目文档中补充相关 Markdown。</p>
          </div>
        ) : null}

        {status === "error" ? (
          <div className="mt-5 border border-rose-200 bg-white px-6 py-16 text-center">
            <p role="alert" className="text-sm font-semibold text-rose-700">知识服务暂不可用</p>
            <button type="button" onClick={() => void loadTopics()} className="mt-4 text-sm font-medium text-emerald-700">重新连接</button>
          </div>
        ) : null}
      </div>
    </main>
  );
}
