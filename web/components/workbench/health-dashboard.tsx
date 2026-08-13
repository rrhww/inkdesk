"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Check, CircleAlert, RotateCcw, ShieldCheck } from "lucide-react";

import { ServerAPI, type KnowledgeSignalRecord } from "@/lib/server-api";

const labels: Record<string, string> = {
  stale: "可能过期",
  unsupported: "缺少证据",
  conflicting: "判断冲突",
  open_question: "未解问题",
  missing_link: "链接缺失",
};

export function HealthDashboard() {
  const [signals, setSignals] = useState<KnowledgeSignalRecord[]>([]);
  const [statusFilter, setStatusFilter] = useState("active");
  const [typeFilter, setTypeFilter] = useState("all");
  const [selected, setSelected] = useState<KnowledgeSignalRecord | null>(null);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await ServerAPI.fetchKnowledgeSignals({
        status: statusFilter === "active" ? undefined : statusFilter,
        type: typeFilter === "all" ? undefined : typeFilter,
      });
      const next = statusFilter === "active"
        ? response.signals.filter((signal) => signal.status === "open" || signal.status === "acknowledged")
        : response.signals;
      setSignals(next);
      setSelected((current) => next.find((item) => item.id === current?.id) ?? next[0] ?? null);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, typeFilter]);

  useEffect(() => { void load(); }, [load]);

  const totals = useMemo(() => ({
    critical: signals.filter((item) => item.severity === "critical").length,
    warning: signals.filter((item) => item.severity === "warning").length,
  }), [signals]);

  async function act(action: "acknowledge" | "resolve" | "dismiss" | "reopen") {
    if (!selected) return;
    await ServerAPI.reviewKnowledgeSignal(selected.id, { action, ifVersion: selected.version, note: note.trim() || undefined });
    setNote("");
    await load();
  }

  return (
    <main className="min-h-dvh bg-slate-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[96rem] flex-wrap items-center justify-between gap-4 px-4 py-5 sm:px-6 lg:px-8">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase text-emerald-700"><ShieldCheck className="h-4 w-4" />Knowledge health</div>
            <h1 className="mt-1 text-xl font-semibold">知识复核队列</h1>
          </div>
          <nav className="flex gap-4 text-sm"><Link href="/app/wiki" className="text-slate-600 hover:text-slate-950">知识看板</Link><Link href="/app/tasks" className="text-slate-600 hover:text-slate-950">任务收件箱</Link></nav>
        </div>
      </header>

      <div className="mx-auto max-w-[96rem] px-4 py-6 sm:px-6 lg:px-8">
        <section className="grid border border-slate-200 bg-white sm:grid-cols-3">
          <div className="p-4"><p className="text-xs text-slate-500">当前信号</p><p className="mt-1 font-mono text-2xl">{signals.length}</p></div>
          <div className="border-t border-slate-200 p-4 sm:border-l sm:border-t-0"><p className="text-xs text-slate-500">高风险冲突</p><p className="mt-1 font-mono text-2xl text-rose-700">{totals.critical}</p></div>
          <div className="border-t border-slate-200 p-4 sm:border-l sm:border-t-0"><p className="text-xs text-slate-500">需要补证</p><p className="mt-1 font-mono text-2xl text-amber-700">{totals.warning}</p></div>
        </section>

        <div className="mt-5 flex flex-wrap gap-3 border-y border-slate-200 py-3">
          <select aria-label="按状态筛选" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="h-10 border border-slate-300 bg-white px-3 text-sm">
            <option value="active">待处理</option><option value="open">未查看</option><option value="acknowledged">已确认</option><option value="resolved">已解决</option><option value="dismissed">已忽略</option>
          </select>
          <select aria-label="按类型筛选" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} className="h-10 border border-slate-300 bg-white px-3 text-sm">
            <option value="all">全部类型</option>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>

        {error ? <p role="alert" className="mt-6 border border-rose-200 bg-white p-6 text-sm text-rose-700">知识健康服务暂不可用。</p> : null}
        {loading ? <p role="status" className="mt-6 p-8 text-center font-mono text-xs text-slate-500">LOADING HEALTH SIGNALS</p> : null}

        {!loading && !error ? (
          <div className="mt-5 grid min-h-[34rem] border border-slate-200 bg-white lg:grid-cols-[minmax(18rem,0.8fr)_minmax(24rem,1.2fr)]">
            <div className="border-b border-slate-200 lg:border-b-0 lg:border-r">
              {signals.length === 0 ? <p className="p-8 text-center text-sm text-slate-500">当前筛选下没有知识信号。</p> : signals.map((signal) => (
                <button key={signal.id} type="button" onClick={() => setSelected(signal)} className={`block w-full border-b border-slate-100 p-4 text-left hover:bg-slate-50 ${selected?.id === signal.id ? "bg-emerald-50" : ""}`}>
                  <div className="flex items-center justify-between gap-3"><span className="text-xs font-semibold text-slate-600">{labels[signal.type] ?? signal.type}</span><span className="font-mono text-[10px] uppercase text-slate-400">{signal.status}</span></div>
                  <p className="mt-2 text-sm font-medium">{signal.title}</p><p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">{signal.detail}</p>
                </button>
              ))}
            </div>

            <section className="p-5 sm:p-7">
              {selected ? <>
                <div className="flex items-start gap-3"><CircleAlert className={`mt-0.5 h-5 w-5 ${selected.severity === "critical" ? "text-rose-600" : "text-amber-600"}`} /><div><p className="font-mono text-[10px] uppercase tracking-widest text-slate-500">{selected.type} / {selected.status}</p><h2 className="mt-1 text-lg font-semibold">{selected.title}</h2></div></div>
                <p className="mt-5 text-sm leading-6 text-slate-700">{selected.detail}</p>
                <dl className="mt-6 grid gap-4 border-y border-slate-200 py-5 text-sm sm:grid-cols-2"><div><dt className="text-xs text-slate-500">主题</dt><dd className="mt-1"><Link className="font-mono text-emerald-700 hover:underline" href={`/app/wiki/${selected.topicId}`}>{selected.topicId}</Link></dd></div><div><dt className="text-xs text-slate-500">版本</dt><dd className="mt-1 font-mono">{selected.version}</dd></div></dl>
                <label className="mt-6 block text-xs font-medium text-slate-600">处理说明</label><textarea value={note} onChange={(event) => setNote(event.target.value)} className="mt-2 min-h-24 w-full border border-slate-300 p-3 text-sm outline-none focus:border-emerald-600" placeholder="解决或忽略时必须说明原因" />
                <div className="mt-4 flex flex-wrap gap-2">
                  {selected.status === "open" ? <button onClick={() => void act("acknowledge")} className="inline-flex h-10 items-center gap-2 border border-slate-300 px-3 text-sm"><Check className="h-4 w-4" />确认已查看</button> : null}
                  {selected.status !== "resolved" ? <button onClick={() => void act("resolve")} className="inline-flex h-10 items-center gap-2 bg-emerald-700 px-3 text-sm text-white"><ShieldCheck className="h-4 w-4" />标记解决</button> : null}
                  {selected.status !== "dismissed" ? <button onClick={() => void act("dismiss")} className="inline-flex h-10 items-center gap-2 border border-slate-300 px-3 text-sm"><AlertTriangle className="h-4 w-4" />接受风险</button> : null}
                  {selected.status === "resolved" || selected.status === "dismissed" ? <button onClick={() => void act("reopen")} className="inline-flex h-10 items-center gap-2 border border-slate-300 px-3 text-sm"><RotateCcw className="h-4 w-4" />重新打开</button> : null}
                </div>
              </> : <p className="grid h-full place-items-center text-sm text-slate-500">选择一个信号查看证据和处理动作。</p>}
            </section>
          </div>
        ) : null}
      </div>
    </main>
  );
}
