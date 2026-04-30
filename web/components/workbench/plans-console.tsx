"use client";

import Link from "next/link";
import { type FormEvent, useTransition } from "react";

import type { KnowledgeNoteSummary, PlanDetail, PlanWorkbenchData } from "@/lib/types";

type PlansConsoleProps = {
  workbench: PlanWorkbenchData;
  linkedKnowledge: KnowledgeNoteSummary[];
  allKnowledge: KnowledgeNoteSummary[];
  createAction?: (formData: FormData) => Promise<void>;
  updateAction?: (formData: FormData) => Promise<void>;
};

type PlanAction = (formData: FormData) => Promise<void>;
type SubmitAction = (action?: PlanAction) => (event: FormEvent<HTMLFormElement>) => void;

type EditablePlanShape = Pick<
  PlanDetail,
  | "title"
  | "summary"
  | "status"
  | "horizon"
  | "priority"
  | "focusLabel"
  | "nextStep"
  | "nextActionLabel"
  | "nextActionHref"
  | "agentPrompt"
  | "relatedNoteIds"
  | "relatedSearchTerms"
>;

const createDefaults: EditablePlanShape = {
  title: "",
  summary: "",
  status: "active",
  horizon: "today",
  priority: "focus",
  focusLabel: "",
  nextStep: "",
  nextActionLabel: "打开计划页",
  nextActionHref: "/app/plans",
  agentPrompt: "",
  relatedNoteIds: [],
  relatedSearchTerms: [""]
};

export function PlansConsole({ workbench, linkedKnowledge, allKnowledge, createAction, updateAction }: PlansConsoleProps) {
  const [isPending, startTransition] = useTransition();
  const todayPlan = workbench.lanes.find((lane) => lane.key === "today")?.plans[0] ?? workbench.lanes[0]?.plans[0];
  const plans = workbench.lanes.flatMap((lane) => lane.plans);
  const agentReadyPlans = plans.filter((plan) => plan.status !== "done");

  function submitAction(action?: PlanAction) {
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
      <section className="mb-8 overflow-hidden rounded-[32px] bg-ink-text px-6 py-7 text-white shadow-paper lg:px-8">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-[0.24em] text-white/60">任务与计划</div>
            <h2 className="mt-4 max-w-4xl font-headline text-4xl font-extrabold tracking-tight lg:text-5xl">让主系统把下一步动作真正组织起来</h2>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-white/75">
              这里不只是堆任务，而是把今天要推进的计划、关联知识和 Agent 协同入口压在同一个执行视图里，让主系统能持续推进，而不是只负责记录。
            </p>
          </div>

          <div className="rounded-[28px] bg-white/10 px-5 py-5 backdrop-blur xl:max-w-sm">
            <div className="text-[11px] uppercase tracking-[0.2em] text-white/60">今日主线</div>
            {todayPlan ? (
              <>
                <h3 className="mt-3 font-headline text-2xl font-extrabold tracking-tight">{todayPlan.title}</h3>
                <p className="mt-3 text-sm leading-7 text-white/75">{todayPlan.nextStep}</p>
                <div className="mt-5 flex flex-wrap gap-3">
                  <Link href={todayPlan.nextActionHref} className="rounded-sm bg-white px-4 py-3 text-sm font-semibold text-ink-text">
                    {todayPlan.nextActionLabel}
                  </Link>
                  <Link
                    href={`/app/search?q=${encodeURIComponent(todayPlan.relatedSearchTerms[0] ?? todayPlan.title)}`}
                    className="rounded-sm border border-white/15 px-4 py-3 text-sm font-semibold text-white"
                  >
                    继续检索
                  </Link>
                </div>
              </>
            ) : (
              <p className="mt-3 text-sm leading-7 text-white/75">当前还没有进入执行视图的计划，先创建一条新计划把下一步动作固定下来。</p>
            )}
          </div>
        </div>
      </section>

      <section className="mb-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="paper-card p-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">执行摘要</div>
          <div className="mt-4 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{workbench.summary.todayPlans}</div>
          <div className="mt-2 text-sm text-ink-muted">今天推进</div>
        </div>
        <div className="paper-card p-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">持续推进</div>
          <div className="mt-4 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{workbench.summary.activePlans}</div>
          <div className="mt-2 text-sm text-ink-muted">仍在主系统里持续迭代的计划</div>
        </div>
        <div className="paper-card p-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">等待下一轮</div>
          <div className="mt-4 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{workbench.summary.queuedPlans}</div>
          <div className="mt-2 text-sm text-ink-muted">已经明确但不抢当前注意力的事项</div>
        </div>
        <div className="paper-card p-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">关联知识</div>
          <div className="mt-4 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{workbench.summary.linkedNotes}</div>
          <div className="mt-2 text-sm text-ink-muted">正在支撑当前执行流的知识资产</div>
        </div>
      </section>

      <section className="mb-8 paper-card p-8">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-ink-primary">创建计划</div>
            <h3 className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">把下一步动作先固定进主系统</h3>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-ink-muted">这里会真实调用后端计划写接口，并把状态、下一步动作和关联知识一起持久化。</p>
          </div>
        </div>

        {createAction ? (
          <form className="mt-6" onSubmit={submitAction(createAction)}>
            <PlanEditorFields allKnowledge={allKnowledge} isPending={isPending} submitLabel="创建计划" values={createDefaults} />
          </form>
        ) : null}
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-6">
          {plans.length === 0 ? (
            <section className="paper-card p-8">
              <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">任务与计划</div>
              <h2 className="mt-4 font-headline text-4xl font-extrabold tracking-tight text-ink-text">当前还没有计划进入执行视图</h2>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-ink-muted">上面的创建表单已经接入真实写接口，保存后这里会立即回显。</p>
            </section>
          ) : null}

          {workbench.lanes.map((lane) => (
            <section key={lane.key} className="paper-card p-8">
              <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.2em] text-ink-primary">{lane.title}</div>
                  <h3 className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{lane.description}</h3>
                </div>
                <div className="text-sm text-ink-muted">当前 {lane.plans.length} 项</div>
              </div>

              <div className="mt-6 space-y-4">
                {lane.plans.map((plan) => {
                  const planNotes = linkedKnowledge.filter((note) => plan.relatedNoteIds.includes(note.id));
                  const searchTerm = plan.relatedSearchTerms[0] ?? plan.title;

                  return (
                    <PlanCard
                      allKnowledge={allKnowledge}
                      key={plan.id}
                      plan={plan}
                      planNotes={planNotes}
                      searchTerm={searchTerm}
                      submitAction={submitAction}
                      isPending={isPending}
                      updateAction={updateAction}
                    />
                  );
                })}
              </div>
            </section>
          ))}
        </div>

        <aside className="space-y-6">
          <section className="paper-card p-6">
            <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">Agent 协同</div>
            <h3 className="mt-4 font-headline text-2xl font-extrabold tracking-tight text-ink-text">把当前计划压缩成能直接行动的提示</h3>
            <div className="mt-5 space-y-4">
              {agentReadyPlans.map((plan) => (
                <div key={plan.id} className="rounded-[22px] bg-ink-low px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{plan.focusLabel}</div>
                  <div className="mt-2 font-headline text-xl font-bold tracking-tight text-ink-text">{plan.title}</div>
                  <p className="mt-3 text-sm leading-7 text-ink-muted">{plan.agentPrompt}</p>
                  <Link
                    href={`/app/search?q=${encodeURIComponent(plan.relatedSearchTerms[0] ?? plan.title)}`}
                    className="mt-4 inline-flex text-sm font-semibold text-ink-primary"
                  >
                    用相关知识继续检索
                  </Link>
                </div>
              ))}
            </div>
          </section>

          <section className="paper-card p-6">
            <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">知识回流</div>
            <h3 className="mt-4 font-headline text-2xl font-extrabold tracking-tight text-ink-text">最近正在支撑执行流的知识资产</h3>
            <div className="mt-5 space-y-4">
              {linkedKnowledge.map((note) => (
                <Link
                  key={note.id}
                  href={`/app/notes/${note.id}${note.published ? "?state=published" : ""}`}
                  className="block rounded-[22px] bg-ink-low px-4 py-4"
                >
                  <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{note.visibilityLabel}</div>
                  <div className="mt-2 font-headline text-xl font-bold tracking-tight text-ink-text">{note.title}</div>
                  <p className="mt-3 text-sm leading-7 text-ink-muted">{note.excerpt}</p>
                  <div className="mt-4 text-sm font-semibold text-ink-primary">回到知识资产</div>
                </Link>
              ))}
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}

function PlanCard({
  plan,
  planNotes,
  searchTerm,
  allKnowledge,
  isPending,
  submitAction,
  updateAction
}: {
  plan: PlanDetail;
  planNotes: KnowledgeNoteSummary[];
  searchTerm: string;
  allKnowledge: KnowledgeNoteSummary[];
  isPending: boolean;
  submitAction: SubmitAction;
  updateAction?: (formData: FormData) => Promise<void>;
}) {
  return (
    <div className="rounded-[28px] bg-ink-low/70 px-5 py-5">
      <div className="flex flex-wrap items-center gap-3 text-[11px] uppercase tracking-[0.2em] text-ink-muted">
        <span className="rounded-full bg-white px-3 py-1">{plan.priorityLabel}</span>
        <span>{plan.statusLabel}</span>
        <span>{plan.focusLabel}</span>
      </div>

      <div className="mt-4 flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <h4 className="font-headline text-3xl font-extrabold tracking-tight text-ink-text">{plan.title}</h4>
          <p className="mt-3 text-sm leading-7 text-ink-muted">{plan.summary}</p>
        </div>
        <div className="text-sm text-ink-muted">{plan.updatedAt}</div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <div className="rounded-[20px] bg-white px-4 py-4">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">当前焦点</div>
          <div className="mt-2 text-sm text-ink-text">{plan.focusLabel}</div>
        </div>
        <div className="rounded-[20px] bg-white px-4 py-4">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">时间范围</div>
          <div className="mt-2 text-sm text-ink-text">{plan.horizonLabel}</div>
        </div>
        <div className="rounded-[20px] bg-white px-4 py-4">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">下一步动作</div>
          <div className="mt-2 text-sm text-ink-text">{plan.nextStep}</div>
        </div>
      </div>

      <div className="mt-5 rounded-[20px] bg-white px-4 py-4">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">关联知识</div>
        <div className="mt-4 flex flex-wrap gap-3">
          {planNotes.map((note) => (
            <Link
              key={note.id}
              href={`/app/notes/${note.id}${note.published ? "?state=published" : ""}`}
              className="rounded-full bg-ink-low px-4 py-2 text-sm text-ink-muted"
            >
              {note.title}
            </Link>
          ))}
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        <Link href={plan.nextActionHref} className="rounded-sm bg-ink-primary px-4 py-3 text-sm font-semibold text-white">
          {plan.nextActionLabel}
        </Link>
        <Link href={`/app/search?q=${encodeURIComponent(searchTerm)}`} className="rounded-sm bg-white px-4 py-3 text-sm font-semibold text-ink-text">
          继续检索
        </Link>
        {planNotes[0] ? (
          <Link
            href={`/app/notes/${planNotes[0].id}${planNotes[0].published ? "?state=published" : ""}`}
            className="rounded-sm bg-white px-4 py-3 text-sm font-semibold text-ink-text"
          >
            打开知识资产
          </Link>
        ) : null}
      </div>

      {updateAction ? (
        <details className="mt-5 rounded-[24px] bg-white px-5 py-5">
          <summary className="cursor-pointer text-sm font-semibold text-ink-text">编辑计划</summary>
          <form className="mt-5" onSubmit={submitAction(updateAction)}>
            <input name="planId" type="hidden" value={plan.id} />
            <PlanEditorFields allKnowledge={allKnowledge} isPending={isPending} submitLabel="保存计划变更" values={plan} />
          </form>
        </details>
      ) : null}
    </div>
  );
}

function PlanEditorFields({
  values,
  allKnowledge,
  isPending,
  submitLabel
}: {
  values: EditablePlanShape;
  allKnowledge: KnowledgeNoteSummary[];
  isPending: boolean;
  submitLabel: string;
}) {
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2 text-sm text-ink-muted">
          <span>标题</span>
          <input className="w-full rounded-sm bg-ink-low px-4 py-3 text-ink-text" defaultValue={values.title} name="title" />
        </label>
        <label className="space-y-2 text-sm text-ink-muted">
          <span>焦点标签</span>
          <input className="w-full rounded-sm bg-ink-low px-4 py-3 text-ink-text" defaultValue={values.focusLabel} name="focusLabel" />
        </label>
      </div>

      <label className="block space-y-2 text-sm text-ink-muted">
        <span>摘要</span>
        <textarea className="min-h-24 w-full rounded-[20px] bg-ink-low px-4 py-4 text-ink-text" defaultValue={values.summary} name="summary" />
      </label>

      <div className="grid gap-4 md:grid-cols-3">
        <SelectField defaultValue={values.status} label="状态" name="status" options={[["active", "进行中"], ["queued", "待推进"], ["done", "已完成"]]} />
        <SelectField defaultValue={values.horizon} label="时间范围" name="horizon" options={[["today", "今天"], ["this-week", "本周"], ["next", "下一步"]]} />
        <SelectField
          defaultValue={values.priority}
          label="优先级"
          name="priority"
          options={[["critical", "最高优先级"], ["focus", "当前主线"], ["steady", "下一轮整理"]]}
        />
      </div>

      <label className="block space-y-2 text-sm text-ink-muted">
        <span>下一步动作</span>
        <textarea className="min-h-24 w-full rounded-[20px] bg-ink-low px-4 py-4 text-ink-text" defaultValue={values.nextStep} name="nextStep" />
      </label>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2 text-sm text-ink-muted">
          <span>动作按钮文案</span>
          <input className="w-full rounded-sm bg-ink-low px-4 py-3 text-ink-text" defaultValue={values.nextActionLabel} name="nextActionLabel" />
        </label>
        <label className="space-y-2 text-sm text-ink-muted">
          <span>动作链接</span>
          <input className="w-full rounded-sm bg-ink-low px-4 py-3 text-ink-text" defaultValue={values.nextActionHref} name="nextActionHref" />
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2 text-sm text-ink-muted">
          <span>检索词</span>
          <input className="w-full rounded-sm bg-ink-low px-4 py-3 text-ink-text" defaultValue={values.relatedSearchTerms[0] ?? ""} name="searchTerm" />
        </label>
      </div>

      <label className="block space-y-2 text-sm text-ink-muted">
        <span>Agent 提示词</span>
        <textarea className="min-h-24 w-full rounded-[20px] bg-ink-low px-4 py-4 text-ink-text" defaultValue={values.agentPrompt} name="agentPrompt" />
      </label>

      <div className="rounded-[24px] bg-ink-low px-5 py-5">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">关联知识资产</div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {allKnowledge.map((note) => (
            <label key={note.id} className="flex items-start gap-3 rounded-[20px] bg-white px-4 py-4 text-sm text-ink-muted">
              <input defaultChecked={values.relatedNoteIds.includes(note.id)} name="relatedNoteIds" type="checkbox" value={note.id} />
              <span>
                <span className="block font-semibold text-ink-text">{note.title}</span>
                <span className="mt-1 block text-xs">{note.visibilityLabel}</span>
              </span>
            </label>
          ))}
        </div>
      </div>

      <button className="rounded-sm bg-ink-primary px-4 py-3 text-sm font-semibold text-white" disabled={isPending} type="submit">
        {isPending ? "处理中..." : submitLabel}
      </button>
    </div>
  );
}

function SelectField({
  label,
  name,
  defaultValue,
  options
}: {
  label: string;
  name: string;
  defaultValue: string;
  options: Array<[string, string]>;
}) {
  return (
    <label className="space-y-2 text-sm text-ink-muted">
      <span>{label}</span>
      <select className="w-full rounded-sm bg-ink-low px-4 py-3 text-ink-text" defaultValue={defaultValue} name={name}>
        {options.map(([value, text]) => (
          <option key={value} value={value}>
            {text}
          </option>
        ))}
      </select>
    </label>
  );
}
