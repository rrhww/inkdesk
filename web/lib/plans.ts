import { getKnowledgeNotesByIds } from "@/lib/knowledge";
import { mockInkdeskDataSource } from "@/lib/mock-data-source";
import { fetchInkdeskJson, hasApiBaseUrl, patchInkdeskJson, postInkdeskJson } from "@/lib/server-api";

type BackendPlanListItem = {
  id: string;
  title: string;
  summary: string;
  status: "active" | "queued" | "done";
  statusLabel: string;
  horizon: "today" | "this-week" | "next";
  horizonLabel: string;
  priority: "critical" | "focus" | "steady";
  priorityLabel: string;
  focusLabel: string;
  nextStep: string;
  nextActionLabel: string;
  nextActionHref: string;
  searchTerm?: string | null;
  agentPrompt: string;
  updatedAt: string;
  relatedNoteIds: string[];
};

export type PlanUpsertInput = {
  title: string;
  summary: string;
  status: "active" | "queued" | "done";
  horizon: "today" | "this-week" | "next";
  priority: "critical" | "focus" | "steady";
  focusLabel: string;
  nextStep: string;
  nextActionLabel: string;
  nextActionHref: string;
  searchTerm: string;
  agentPrompt: string;
  relatedNoteIds: string[];
};

const laneMeta = {
  today: {
    title: "今天推进",
    description: "先把今天必须收口的事项处理掉，让主系统继续向前。"
  },
  active: {
    title: "持续推进",
    description: "这些计划还需要连续几轮迭代，不抢第一屏，但不能掉出视野。"
  },
  queued: {
    title: "等待下一轮",
    description: "方向已经明确，先暂存为下一轮的行动入口。"
  }
} as const;

function normalizeLegacyProductTerm(value: string) {
  switch (value.trim()) {
    case "\u516c\u5171\u9762":
    case "\u516c\u5171\u535a\u5ba2":
    case "\u4f5c\u8005\u95e8\u6237":
      return "公开输出";
    default:
      return value;
  }
}

function adaptPlan(item: BackendPlanListItem) {
  const supplement = mockInkdeskDataSource.getPlanById(item.id);

  return {
    id: item.id,
    title: item.title,
    summary: item.summary,
    status: item.status,
    statusLabel: item.statusLabel,
    horizon: item.horizon,
    horizonLabel: item.horizonLabel,
    priority: item.priority,
    priorityLabel: item.priorityLabel,
    focusLabel: item.focusLabel,
    nextStep: item.nextStep,
    nextActionLabel: item.nextActionLabel,
    nextActionHref: item.nextActionHref,
    relatedNoteIds: item.relatedNoteIds,
    relatedTagIds: supplement?.relatedTagIds ?? [],
    relatedSearchTerms: item.searchTerm ? [normalizeLegacyProductTerm(item.searchTerm)] : supplement?.relatedSearchTerms ?? [item.title],
    agentPrompt: item.agentPrompt,
    updatedAt: supplement?.updatedAt ?? item.updatedAt,
    milestones: supplement?.milestones ?? []
  };
}

function buildPlanWorkbench(plans: ReturnType<typeof adaptPlan>[]) {
  return {
    summary: {
      todayPlans: plans.filter((plan) => plan.horizon === "today" && plan.status !== "done").length,
      activePlans: plans.filter((plan) => plan.status === "active").length,
      queuedPlans: plans.filter((plan) => plan.status === "queued").length,
      linkedNotes: new Set(plans.flatMap((plan) => plan.relatedNoteIds)).size
    },
    lanes: [
      {
        key: "today" as const,
        title: laneMeta.today.title,
        description: laneMeta.today.description,
        plans: plans.filter((plan) => plan.horizon === "today" && plan.status !== "done")
      },
      {
        key: "active" as const,
        title: laneMeta.active.title,
        description: laneMeta.active.description,
        plans: plans.filter((plan) => plan.status === "active" && plan.horizon !== "today")
      },
      {
        key: "queued" as const,
        title: laneMeta.queued.title,
        description: laneMeta.queued.description,
        plans: plans.filter((plan) => plan.status === "queued")
      }
    ]
  };
}

async function getBackendPlans(ownerSession?: string) {
  const plans = await fetchInkdeskJson<BackendPlanListItem[]>("/admin/plans", { ownerSession });
  return plans.map(adaptPlan);
}

export async function getPlanWorkbenchData(ownerSession?: string) {
  if (!hasApiBaseUrl()) {
    return mockInkdeskDataSource.getPlanWorkbenchData();
  }

  return buildPlanWorkbench(await getBackendPlans(ownerSession));
}

export async function getPlanById(id: string, ownerSession?: string) {
  if (!hasApiBaseUrl()) {
    return mockInkdeskDataSource.getPlanById(id);
  }

  const plans = await getBackendPlans(ownerSession);
  return plans.find((plan) => plan.id === id);
}

export async function getPlanKnowledgeLinks(ids: string[], ownerSession?: string) {
  return getKnowledgeNotesByIds(ids, ownerSession);
}

export async function createPlanRecord(input: PlanUpsertInput, ownerSession?: string) {
  if (!hasApiBaseUrl()) {
    return adaptPlan({
      id: `mock-plan-${Date.now()}`,
      title: input.title,
      summary: input.summary,
      status: input.status,
      statusLabel: input.status === "done" ? "已完成" : input.status === "queued" ? "待推进" : "进行中",
      horizon: input.horizon,
      horizonLabel: input.horizon === "today" ? "今天" : input.horizon === "this-week" ? "本周" : "下一步",
      priority: input.priority,
      priorityLabel: input.priority === "critical" ? "最高优先级" : input.priority === "focus" ? "当前主线" : "下一轮整理",
      focusLabel: input.focusLabel,
      nextStep: input.nextStep,
      nextActionLabel: input.nextActionLabel,
      nextActionHref: input.nextActionHref,
      searchTerm: input.searchTerm,
      agentPrompt: input.agentPrompt,
      updatedAt: "刚刚保存",
      relatedNoteIds: input.relatedNoteIds
    });
  }

  return adaptPlan(await postInkdeskJson<BackendPlanListItem>("/admin/plans", input, { ownerSession }));
}

export async function updatePlanRecord(planId: string, input: PlanUpsertInput, ownerSession?: string) {
  if (!hasApiBaseUrl()) {
    return {
      ...(mockInkdeskDataSource.getPlanById(planId) ?? mockInkdeskDataSource.getPlanWorkbenchData().lanes[0]?.plans[0]),
      ...input,
      id: planId,
      statusLabel: input.status === "done" ? "已完成" : input.status === "queued" ? "待推进" : "进行中",
      horizonLabel: input.horizon === "today" ? "今天" : input.horizon === "this-week" ? "本周" : "下一步",
      priorityLabel: input.priority === "critical" ? "最高优先级" : input.priority === "focus" ? "当前主线" : "下一轮整理",
      relatedSearchTerms: input.searchTerm ? [input.searchTerm] : [input.title],
      milestones: []
    };
  }

  return adaptPlan(await patchInkdeskJson<BackendPlanListItem>(`/admin/plans/${planId}`, input, { ownerSession }));
}

export function planPayloadFromFormData(formData: FormData): PlanUpsertInput {
  return {
    title: String(formData.get("title") ?? ""),
    summary: String(formData.get("summary") ?? ""),
    status: String(formData.get("status") ?? "active") as PlanUpsertInput["status"],
    horizon: String(formData.get("horizon") ?? "today") as PlanUpsertInput["horizon"],
    priority: String(formData.get("priority") ?? "focus") as PlanUpsertInput["priority"],
    focusLabel: String(formData.get("focusLabel") ?? ""),
    nextStep: String(formData.get("nextStep") ?? ""),
    nextActionLabel: String(formData.get("nextActionLabel") ?? ""),
    nextActionHref: String(formData.get("nextActionHref") ?? ""),
    searchTerm: String(formData.get("searchTerm") ?? ""),
    agentPrompt: String(formData.get("agentPrompt") ?? ""),
    relatedNoteIds: formData
      .getAll("relatedNoteIds")
      .map((value) => String(value))
      .filter(Boolean)
  };
}
