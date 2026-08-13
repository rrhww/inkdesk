"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, CircleDot, FileQuestion, ListTodo, Plus, RefreshCw } from "lucide-react";

import { ServerAPI, type DevelopmentTask, type TaskContextStatus, type TaskOriginType, type TaskStatus } from "@/lib/server-api";

const statusLabel: Record<TaskStatus, string> = { backlog: "Backlog", ready: "Ready", doing: "Doing", review: "Review", blocked: "Blocked", done: "Done" };
const contextLabel: Record<TaskContextStatus, string> = { pending: "等待检索", searching: "正在装配", ready: "上下文就绪", gap: "知识缺口", failed: "装配失败" };
const originLabel: Record<TaskOriginType, string> = { realtime_requirement: "实时需求", knowledge_signal: "知识信号", execution_finding: "执行发现", manual: "人工输入" };

function TaskDetail({ task, onChange }: { task: DevelopmentTask; onChange: (task: DevelopmentTask) => void }) {
  const pack = task.contextPack as { topics?: Array<{ topicId?: string; id?: string; title?: string; path?: string }>; sourcePaths?: string[]; codePaths?: string[]; graphVersion?: string } | null | undefined;
  const gap = task.knowledgeGap as { reason?: string; query?: string; requestedTopicIds?: string[]; recordedAt?: string } | null | undefined;
  const next: Partial<Record<TaskStatus, TaskStatus[]>> = { backlog: ["ready", "blocked"], ready: ["doing", "backlog", "blocked"], doing: ["review", "blocked"], review: ["done", "doing", "blocked"], blocked: ["backlog", "ready", "doing"] };

  async function transition(status: TaskStatus) { onChange(await ServerAPI.transitionTask(task.id, status, task.version)); }
  async function assemble() { onChange(await ServerAPI.assembleTaskContext(task.id, true)); }

  return <section className="min-w-0 p-5 sm:p-7">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="font-mono text-[10px] uppercase tracking-widest text-emerald-700">{originLabel[task.originType]} / {statusLabel[task.status]}</p><h2 className="mt-2 text-xl font-semibold">{task.title}</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{task.goal}</p></div><span className="border border-slate-200 px-2 py-1 font-mono text-xs">v{task.version}</span></div>
    <dl className="mt-6 grid border-y border-slate-200 py-4 text-sm sm:grid-cols-3"><div className="py-2"><dt className="text-xs text-slate-500">上下文</dt><dd className="mt-1 font-medium">{contextLabel[task.contextStatus]}</dd></div><div className="py-2"><dt className="text-xs text-slate-500">优先级 / 风险</dt><dd className="mt-1 font-mono">{task.priority} / {task.risk}</dd></div><div className="py-2"><dt className="text-xs text-slate-500">来源引用</dt><dd className="mt-1 break-all font-mono text-xs">{task.originRef || "无外部引用"}</dd></div></dl>

    {pack ? <div className="mt-6"><h3 className="text-sm font-semibold">Context Pack</h3><p className="mt-1 font-mono text-[10px] text-slate-400">GRAPH {pack.graphVersion || "unknown"}</p><div className="mt-3 divide-y divide-slate-100 border-y border-slate-200">{(pack.topics || []).map((topic) => { const id = topic.topicId || topic.id || ""; return <Link key={`${id}-${topic.path}`} href={`/app/wiki/${id}`} className="flex min-h-12 items-center justify-between gap-3 py-3 text-sm hover:text-emerald-700"><span>{topic.title || topic.path}</span><ArrowRight className="h-4 w-4 shrink-0" /></Link>; })}</div>{(pack.codePaths || []).length ? <p className="mt-4 break-all font-mono text-xs text-slate-500">{pack.codePaths?.join(" · ")}</p> : null}</div> : null}
    {gap ? <div className="mt-6 border-l-2 border-amber-500 pl-4"><div className="flex items-center gap-2 text-sm font-semibold"><FileQuestion className="h-4 w-4" />Knowledge Gap</div><p className="mt-2 text-sm text-slate-600">{gap.reason || "没有找到足够的项目知识"}</p><p className="mt-1 text-xs text-slate-500">检索已经完成，可以继续执行，但应在结果中补回缺失知识。</p></div> : null}
    <div className="mt-7 flex flex-wrap gap-2"><button type="button" onClick={() => void assemble()} className="inline-flex h-10 items-center gap-2 border border-slate-300 px-3 text-sm"><RefreshCw className="h-4 w-4" />{task.contextStatus === "failed" ? "重试装配" : "重新装配"}</button>{(next[task.status] || []).map((status) => <button key={status} type="button" disabled={(status === "ready" || status === "doing") && !["ready", "gap"].includes(task.contextStatus)} onClick={() => void transition(status)} className="h-10 bg-slate-950 px-3 text-sm text-white disabled:cursor-not-allowed disabled:bg-slate-300">移至 {statusLabel[status]}</button>)}</div>
  </section>;
}

export function TaskInbox() {
  const [tasks, setTasks] = useState<DevelopmentTask[]>([]);
  const [selected, setSelected] = useState<DevelopmentTask | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [statusFilter, setStatusFilter] = useState<TaskStatus | "all">("all");
  const [contextFilter, setContextFilter] = useState<TaskContextStatus | "all">("all");
  const [originFilter, setOriginFilter] = useState<TaskOriginType | "all">("all");
  const [title, setTitle] = useState(""); const [goal, setGoal] = useState(""); const [origin, setOrigin] = useState<TaskOriginType>("realtime_requirement");
  const selectedIdRef = useRef<string | null>(null);
  useEffect(() => { selectedIdRef.current = selected?.id ?? null; }, [selected]);

  const load = useCallback(async () => { setStatus("loading"); try { const result = await ServerAPI.fetchTasks({ status: statusFilter === "all" ? undefined : statusFilter, originType: originFilter === "all" ? undefined : originFilter, contextStatus: contextFilter === "all" ? undefined : contextFilter }); setTasks(result.tasks); const currentId = selectedIdRef.current; setSelected(currentId ? (result.tasks.find((item) => item.id === currentId) ?? result.tasks[0] ?? null) : result.tasks[0] ?? null); setStatus("ready"); } catch { setStatus("error"); } }, [contextFilter, originFilter, statusFilter]);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);
  useEffect(() => ServerAPI.subscribeToTaskEvents(() => void load()), [load]);

  const summary = useMemo(() => ({ active: tasks.filter((task) => !["done", "backlog"].includes(task.status)).length, needsContext: tasks.filter((task) => ["pending", "searching", "failed"].includes(task.contextStatus)).length }), [tasks]);

  async function create(event: React.FormEvent) { event.preventDefault(); if (!title.trim() || !goal.trim()) return; const task = await ServerAPI.createTask({ title: title.trim(), goal: goal.trim(), originType: origin }); setTitle(""); setGoal(""); setSelected(task); await load(); }
  function updateTask(task: DevelopmentTask) { setSelected(task); setTasks((current) => current.map((item) => item.id === task.id ? task : item)); }

  return <main className="min-h-dvh bg-slate-50 text-slate-950"><header className="border-b border-slate-200 bg-white"><div className="mx-auto flex max-w-[96rem] flex-wrap items-center justify-between gap-4 px-4 py-5 sm:px-6 lg:px-8"><div><div className="flex items-center gap-2 text-xs font-semibold uppercase text-emerald-700"><ListTodo className="h-4 w-4" />Development inbox</div><h1 className="mt-1 text-xl font-semibold">研发任务收件箱</h1></div><nav className="flex gap-4 text-sm"><Link href="/app/wiki" className="text-slate-600 hover:text-slate-950">知识看板</Link><Link href="/app/health" className="text-slate-600 hover:text-slate-950">知识健康</Link></nav></div></header>
    <div className="mx-auto max-w-[96rem] px-4 py-6 sm:px-6 lg:px-8"><section className="grid border border-slate-200 bg-white sm:grid-cols-3"><div className="p-4"><p className="text-xs text-slate-500">当前列表</p><p className="mt-1 font-mono text-2xl">{tasks.length}</p></div><div className="border-t border-slate-200 p-4 sm:border-l sm:border-t-0"><p className="text-xs text-slate-500">执行中</p><p className="mt-1 font-mono text-2xl">{summary.active}</p></div><div className="border-t border-slate-200 p-4 sm:border-l sm:border-t-0"><p className="text-xs text-slate-500">待装配上下文</p><p className="mt-1 font-mono text-2xl text-amber-700">{summary.needsContext}</p></div></section>
      <form onSubmit={create} className="mt-5 grid gap-3 border-y border-slate-200 py-4 lg:grid-cols-[minmax(12rem,0.8fr)_minmax(18rem,1.4fr)_12rem_auto]"><input aria-label="任务标题" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="任务标题" className="h-10 border border-slate-300 bg-white px-3 text-sm" /><input aria-label="任务目标" value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="预期结果和约束" className="h-10 border border-slate-300 bg-white px-3 text-sm" /><select aria-label="任务来源" value={origin} onChange={(e) => setOrigin(e.target.value as TaskOriginType)} className="h-10 border border-slate-300 bg-white px-3 text-sm"><option value="realtime_requirement">实时需求</option><option value="manual">人工输入</option><option value="execution_finding">执行发现</option></select><button type="submit" className="inline-flex h-10 items-center justify-center gap-2 bg-emerald-700 px-4 text-sm text-white"><Plus className="h-4 w-4" />创建任务</button></form>
      <div className="mt-3 flex flex-wrap gap-2"><select aria-label="状态筛选" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as TaskStatus | "all")} className="h-9 border border-slate-300 bg-white px-2 text-xs"><option value="all">全部状态</option>{Object.entries(statusLabel).map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select><select aria-label="来源筛选" value={originFilter} onChange={(e) => setOriginFilter(e.target.value as TaskOriginType | "all")} className="h-9 border border-slate-300 bg-white px-2 text-xs"><option value="all">全部来源</option>{Object.entries(originLabel).map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select><select aria-label="上下文筛选" value={contextFilter} onChange={(e) => setContextFilter(e.target.value as TaskContextStatus | "all")} className="h-9 border border-slate-300 bg-white px-2 text-xs"><option value="all">全部上下文</option>{Object.entries(contextLabel).map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></div>
      {status === "error" ? <p role="alert" className="mt-5 border border-rose-200 bg-white p-6 text-rose-700">任务服务暂不可用。</p> : null}{status === "loading" ? <p role="status" className="mt-5 p-8 text-center font-mono text-xs text-slate-500">LOADING DEVELOPMENT TASKS</p> : null}
      {status === "ready" ? <div className="mt-5 grid min-h-[38rem] border border-slate-200 bg-white lg:grid-cols-[minmax(18rem,0.8fr)_minmax(26rem,1.6fr)]"><div className="border-b border-slate-200 lg:border-b-0 lg:border-r">{tasks.length === 0 ? <p className="p-8 text-center text-sm text-slate-500">暂无任务，先记录一个实时需求。</p> : tasks.map((task) => <button key={task.id} onClick={() => setSelected(task)} className={`block w-full border-b border-slate-100 p-4 text-left hover:bg-slate-50 ${selected?.id === task.id ? "bg-emerald-50" : ""}`}><div className="flex items-center justify-between gap-3"><span className="text-xs text-slate-500">{originLabel[task.originType]}</span><span className="font-mono text-[10px] uppercase text-slate-400">{statusLabel[task.status]}</span></div><p className="mt-2 text-sm font-medium">{task.title}</p><p className="mt-2 flex items-center gap-1.5 text-xs text-slate-500"><CircleDot className="h-3 w-3" />{contextLabel[task.contextStatus]}</p></button>)}</div>{selected ? <TaskDetail task={selected} onChange={updateTask} /> : <p className="grid h-full place-items-center p-8 text-sm text-slate-500">选择一个任务查看上下文。</p>}</div> : null}
    </div></main>;
}
