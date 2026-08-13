"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, ArrowLeft, Check, Circle, ExternalLink, FileSearch, Loader2, OctagonX, ShieldCheck, Square } from "lucide-react";

import { MarkdownViewer } from "@/components/workbench/markdown-viewer";
import { type GraphStreamStatus, type HarnessPermission, type HarnessRun, type HarnessRunEvent, ServerAPI } from "@/lib/server-api";

const stages = [
  ["preflight", "Preflight"],
  ["collect-evidence", "Collect evidence"],
  ["specialist-structure", "Structure review"],
  ["specialist-testing", "Test review"],
  ["specialist-security", "Security review"],
  ["lead-reconcile", "Lead reconcile"],
  ["validate-findings", "Validate findings"],
  ["write-report", "Write report"],
  ["graph-refresh", "Graph refresh"]
] as const;

const dimensions = [
  "Task Understanding",
  "Controlled Execution",
  "Change Validation",
  "Reliable Delivery",
  "Learning Capture"
];

function StageIcon({ status }: { status: string }) {
  if (status === "succeeded") return <Check className="size-4" aria-hidden />;
  if (status === "running") return <Loader2 className="size-4 animate-spin" aria-hidden />;
  if (status === "failed") return <OctagonX className="size-4" aria-hidden />;
  if (status === "blocked" || status === "cancelled") return <Square className="size-4" aria-hidden />;
  return <Circle className="size-4" aria-hidden />;
}

export function RunInspector({ runId }: { runId: string }) {
  const [run, setRun] = useState<HarnessRun | null>(null);
  const [streamStatus, setStreamStatus] = useState<GraphStreamStatus>("connecting");
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<HarnessPermission[]>([]);
  const [toolEvents, setToolEvents] = useState<HarnessRunEvent[]>([]);
  const [now, setNow] = useState(() => Date.now());
  const refreshTimer = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [nextRun, nextPermissions] = await Promise.all([
        ServerAPI.fetchHarnessRun(runId),
        ServerAPI.fetchHarnessPermissions(runId)
      ]);
      setRun(nextRun);
      setPermissions(nextPermissions);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load this run.");
    }
  }, [runId]);

  useEffect(() => {
    const initialLoad = window.setTimeout(() => void refresh(), 0);
    const unsubscribe = ServerAPI.subscribeToRunEvents(
      runId,
      (event) => {
        if (event.type === "executor.delta") return;
        if (event.type.startsWith("executor.tool." ) || event.type === "executor.tool_denied") {
          setToolEvents((current) => [...current.slice(-19), event]);
        }
        if (refreshTimer.current !== null) window.clearTimeout(refreshTimer.current);
        refreshTimer.current = window.setTimeout(() => void refresh(), 80);
      },
      setStreamStatus
    );
    return () => {
      window.clearTimeout(initialLoad);
      if (refreshTimer.current !== null) window.clearTimeout(refreshTimer.current);
      unsubscribe();
    };
  }, [refresh, runId]);

  useEffect(() => {
    if (!permissions.length) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [permissions.length]);

  const scores = run?.findings?.dimensionScores ?? {};
  const findings = run?.findings?.findings ?? [];
  const evidence = useMemo(() => Object.entries(run?.evidence?.envelopes ?? {}), [run]);
  const terminal = run && ["succeeded", "failed", "cancelled", "stale", "interrupted"].includes(run.status);

  async function openReport() {
    try {
      setReport((await ServerAPI.fetchHarnessReport(runId)).content);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Report is not available.");
    }
  }

  async function decidePermission(permissionId: string, decision: "allow_once" | "deny") {
    try {
      await ServerAPI.decideHarnessPermission(runId, permissionId, decision);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to resolve this permission request.");
    }
  }

  if (error && !run) {
    return <main className="grid min-h-screen place-items-center p-6 text-sm text-ink-errorText">{error}</main>;
  }

  return (
    <main className="min-h-screen bg-[#f7f8f8] text-ink-text">
      <header className="border-b border-ink-line bg-white">
        <div className="mx-auto flex max-w-[1440px] items-center gap-4 px-5 py-4 lg:px-8">
          <Link href="/app/wiki" className="grid size-9 place-items-center border border-ink-line text-ink-muted hover:bg-ink-low" title="Back to graph">
            <ArrowLeft className="size-4" aria-hidden />
          </Link>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold uppercase text-ink-primary">Harness Audit</p>
            <h1 className="truncate font-headline text-xl font-bold">{runId}</h1>
          </div>
          <div className="text-right text-xs text-ink-muted">
            <div className="font-semibold uppercase text-ink-text">{run?.status ?? "loading"}</div>
            <div>{terminal ? "Event log complete" : streamStatus === "connected" ? "Live events" : streamStatus}</div>
          </div>
        </div>
      </header>

      <section className="border-b border-ink-line bg-white">
        <div className="mx-auto grid max-w-[1440px] grid-cols-2 gap-px bg-ink-line lg:grid-cols-5">
          {[
            ["Executor", run?.executor],
            ["Depth", run?.inputs.depth],
            ["Repository HEAD", run?.sourceHead?.slice(0, 12)],
            ["Session evidence", run?.evidence?.sessionEvidenceStatus ?? "pending"],
            ["Findings", findings.length.toString()]
          ].map(([label, value]) => (
            <div key={label} className="min-w-0 bg-white px-5 py-4 last:col-span-2 lg:last:col-span-1">
              <div className="text-[11px] font-semibold uppercase text-ink-muted">{label}</div>
              <div className="mt-1 truncate font-mono text-sm font-semibold">{value ?? "-"}</div>
            </div>
          ))}
        </div>
      </section>

      <div className="mx-auto grid max-w-[1440px] gap-0 lg:grid-cols-[300px_minmax(0,1fr)]">
        <aside className="border-b border-ink-line bg-white p-5 lg:min-h-[calc(100vh-154px)] lg:border-b-0 lg:border-r lg:p-7">
          <h2 className="font-headline text-sm font-bold uppercase">Stage timeline</h2>
          <ol className="mt-5 space-y-1">
            {stages.map(([id, label]) => {
              const status = run?.stageStates[id] ?? "pending";
              return (
                <li key={id} className="flex min-h-10 items-center gap-3 border-l-2 border-ink-high px-3 text-sm" data-status={status}>
                  <span className={status === "succeeded" ? "text-ink-primary" : status === "failed" ? "text-ink-errorText" : "text-ink-muted"}>
                    <StageIcon status={status} />
                  </span>
                  <span className="min-w-0 flex-1 truncate">{label}</span>
                  <span className="text-[10px] uppercase text-ink-muted">{status}</span>
                </li>
              );
            })}
          </ol>
          {!terminal && run ? (
            <button
              type="button"
              onClick={() => void ServerAPI.cancelHarnessRun(runId).then(refresh)}
              className="mt-6 flex h-9 w-full items-center justify-center gap-2 border border-ink-errorText text-xs font-bold uppercase text-ink-errorText hover:bg-ink-errorSoft"
            >
              <Square className="size-3" aria-hidden /> Cancel run
            </button>
          ) : null}
        </aside>

        <div className="min-w-0 px-5 py-7 lg:px-9">
          {run?.status === "stale" ? (
            <div className="mb-6 flex items-start gap-3 border border-amber-500 bg-amber-50 p-4 text-sm text-amber-950">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
              Repository HEAD changed during the audit. This report represents only the frozen source HEAD.
            </div>
          ) : null}
          {run?.error ? (
            <div className="mb-6 border border-ink-errorText bg-ink-errorSoft p-4 text-sm text-ink-errorText">
              <strong>{run.error.code}</strong>: {run.error.message}
            </div>
          ) : null}

          {permissions.length ? (
            <section className="mb-9 border border-amber-500 bg-amber-50">
              <div className="border-b border-amber-300 px-5 py-4">
                <h2 className="font-headline text-base font-bold text-amber-950">Read-only approvals</h2>
                <p className="mt-1 text-xs text-amber-900">Approval applies once and cannot enable writes, network access, project scripts, or repository-external paths.</p>
              </div>
              <div className="divide-y divide-amber-200">
                {permissions.map((permission) => {
                  const seconds = Math.max(0, Math.ceil((new Date(permission.expiresAt).getTime() - now) / 1000));
                  return (
                    <div key={permission.id} className="grid gap-4 bg-white p-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2 text-xs font-bold uppercase text-amber-900">
                          <span>{permission.stageId}</span><span>{permission.tool}</span><span>{seconds}s</span>
                        </div>
                        <pre className="mt-3 max-h-32 overflow-auto border border-ink-line bg-ink-low p-3 text-xs text-ink-text">{JSON.stringify(permission.inputPreview, null, 2)}</pre>
                      </div>
                      <div className="flex gap-2">
                        <button type="button" onClick={() => void decidePermission(permission.id, "allow_once")} className="h-9 border border-ink-primary px-3 text-xs font-bold text-ink-primary hover:bg-ink-primarySoft">Allow once</button>
                        <button type="button" onClick={() => void decidePermission(permission.id, "deny")} className="h-9 border border-ink-errorText px-3 text-xs font-bold text-ink-errorText hover:bg-ink-errorSoft">Deny</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          ) : null}

          <section>
            <div className="flex items-center justify-between gap-4">
              <h2 className="font-headline text-base font-bold">Five-dimension score</h2>
              {run?.reportPath ? (
                <button type="button" onClick={() => void openReport()} className="flex h-9 items-center gap-2 border border-ink-primary px-3 text-xs font-bold text-ink-primary hover:bg-ink-primarySoft">
                  <ExternalLink className="size-4" aria-hidden /> Open report
                </button>
              ) : null}
            </div>
            <div className="mt-4 grid gap-px bg-ink-line sm:grid-cols-5">
              {dimensions.map((dimension) => (
                <div key={dimension} className="min-h-28 bg-white p-4">
                  <div className="text-xs font-semibold text-ink-muted">{dimension}</div>
                  <div className="mt-5 font-headline text-3xl font-bold">{scores[dimension] ?? "-"}<span className="text-sm text-ink-muted"> / 4</span></div>
                </div>
              ))}
            </div>
          </section>

          <section className="mt-9">
            <h2 className="font-headline text-base font-bold">Evidence status</h2>
            <div className="mt-4 overflow-x-auto border border-ink-line bg-white">
              <table className="w-full min-w-[620px] text-left text-sm">
                <thead className="bg-ink-low text-[11px] uppercase text-ink-muted"><tr><th className="px-4 py-3">Envelope</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Evidence</th><th className="px-4 py-3">Summary</th></tr></thead>
                <tbody>
                  {evidence.map(([name, envelope]) => (
                    <tr key={name} className="border-t border-ink-high"><td className="px-4 py-3 font-semibold">{name}</td><td className="px-4 py-3">{envelope.status}</td><td className="px-4 py-3">{envelope.evidence.length}</td><td className="px-4 py-3 text-ink-muted">{envelope.summaryFacts.join(" ")}</td></tr>
                  ))}
                  {!evidence.length ? <tr><td colSpan={4} className="px-4 py-6 text-center text-ink-muted">Evidence collection has not completed.</td></tr> : null}
                </tbody>
              </table>
            </div>
          </section>

          {toolEvents.length ? (
            <section className="mt-9">
              <h2 className="font-headline text-base font-bold">Agent tool activity</h2>
              <div className="mt-4 overflow-hidden border border-ink-line bg-white">
                {toolEvents.map((event) => (
                  <div key={event.sequence} className="grid gap-2 border-t border-ink-high px-4 py-3 text-xs first:border-t-0 sm:grid-cols-[170px_180px_minmax(0,1fr)]">
                    <span className="font-mono font-semibold">{event.type}</span>
                    <span>{String(event.data.stageId ?? "-")}</span>
                    <span className="truncate text-ink-muted">{String(event.data.tool ?? event.data.reason ?? event.data.evidenceId ?? "")}</span>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          <section className="mt-9">
            <div className="flex items-center gap-2"><ShieldCheck className="size-4 text-ink-primary" aria-hidden /><h2 className="font-headline text-base font-bold">Frozen findings</h2></div>
            <div className="mt-4 space-y-3">
              {findings.map((finding) => (
                <article key={finding.id} className="border border-ink-line bg-white p-5">
                  <div className="flex flex-wrap items-center gap-2 text-[11px] font-bold uppercase">
                    <span className="text-ink-primary">{finding.id}</span><span className="border border-ink-line px-2 py-1">{finding.dimension}</span><span className={finding.severity === "critical" || finding.severity === "high" ? "text-ink-errorText" : "text-ink-muted"}>{finding.severity}</span>
                  </div>
                  <h3 className="mt-3 font-headline text-base font-bold">{finding.title}</h3>
                  <p className="mt-2 text-sm text-ink-muted">{finding.consequence}</p>
                  <dl className="mt-4 grid gap-3 text-xs sm:grid-cols-3"><div><dt className="font-bold uppercase text-ink-muted">Owner</dt><dd className="mt-1">{finding.owner}</dd></div><div><dt className="font-bold uppercase text-ink-muted">Expected artifact</dt><dd className="mt-1">{finding.expectedArtifact}</dd></div><div><dt className="font-bold uppercase text-ink-muted">Verifiers</dt><dd className="mt-1">{finding.verifiers.join(", ")}</dd></div></dl>
                </article>
              ))}
              {run?.findings && !findings.length ? <div className="border border-ink-line bg-white p-7 text-center text-sm text-ink-muted"><FileSearch className="mx-auto mb-2 size-5" aria-hidden />No evidence-supported findings were retained.</div> : null}
            </div>
          </section>

          {report ? <section className="mt-9 border-t border-ink-line pt-8"><h2 className="mb-5 font-headline text-base font-bold">Audit report</h2><div className="bg-white p-5 sm:p-8"><MarkdownViewer content={report} isLoading={false} /></div></section> : null}
        </div>
      </div>
    </main>
  );
}
