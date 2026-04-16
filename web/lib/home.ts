import { mockInkdeskDataSource } from "@/lib/mock-data-source";
import { fetchInkdeskJson, hasApiBaseUrl, InkdeskApiError } from "@/lib/server-api";
import type { KnowledgeNoteSummary, PlanDetail, PublishEntry, WorkbenchSnapshot } from "@/lib/types";

type BackendHomePlan = {
  id: string;
  title: string;
  statusLabel: string;
  horizonLabel: string;
  priorityLabel: string;
  nextStep: string;
  nextActionLabel: string;
  nextActionHref: string;
  searchTerm?: string | null;
};

type BackendHomeNote = {
  id: string;
  title: string;
  excerpt: string;
  folder: string;
  updatedAt: string;
  published: boolean;
  visibility: "private" | "public";
  visibilityLabel: string;
};

type BackendHomePublishQueueItem = {
  noteId: string;
  title: string;
  excerpt: string;
  updatedAt: string;
  state: "draft" | "published";
  stateLabel: string;
};

type BackendHomeResponse = {
  summary: WorkbenchSnapshot["summary"];
  focusPlan: BackendHomePlan | null;
  focusNote: BackendHomeNote | null;
  suggestions: WorkbenchSnapshot["suggestions"];
  quickActions: WorkbenchSnapshot["quickActions"];
  recentKnowledge: BackendHomeNote[];
  publishQueue: BackendHomePublishQueueItem[];
};

function countWords(value: string) {
  return value
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;
}

function estimateReadingMinutes(value: string) {
  return Math.max(1, Math.ceil(countWords(value) / 220));
}

function visibilityLabelFor(visibility: "private" | "public") {
  return visibility === "public" ? "已发布" : "仅主系统";
}

function knowledgeStateLabelFor(published: boolean) {
  return published ? "已发布" : "仅主系统";
}

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

function statusFromLabel(label: string, fallback?: PlanDetail["status"]): PlanDetail["status"] {
  switch (label) {
    case "进行中":
      return "active";
    case "待推进":
      return "queued";
    case "已完成":
      return "done";
    default:
      return fallback ?? "queued";
  }
}

function horizonFromLabel(label: string, fallback?: PlanDetail["horizon"]): PlanDetail["horizon"] {
  switch (label) {
    case "今天":
      return "today";
    case "本周":
      return "this-week";
    case "下一步":
      return "next";
    default:
      return fallback ?? "next";
  }
}

function priorityFromLabel(label: string, fallback?: PlanDetail["priority"]): PlanDetail["priority"] {
  switch (label) {
    case "最高优先级":
      return "critical";
    case "当前主线":
      return "focus";
    case "下一轮整理":
      return "steady";
    default:
      return fallback ?? "steady";
  }
}

function placeholderFocusPlan(): PlanDetail {
  return {
    id: "plan-empty",
    title: "当前还没有需要推进的计划",
    summary: "先回到计划模块固定今天最重要的一步。",
    status: "queued",
    statusLabel: "待推进",
    horizon: "next",
    horizonLabel: "下一步",
    priority: "steady",
    priorityLabel: "下一轮整理",
    focusLabel: "等待建立焦点",
    nextStep: "当前还没有可推进的计划，先回到计划模块固定下一步动作。",
    nextActionLabel: "查看任务与计划",
    nextActionHref: "/app/plans",
    relatedNoteIds: [],
    relatedTagIds: [],
    relatedSearchTerms: ["Agent"],
    agentPrompt: "先建立今天最重要的一条计划。",
    updatedAt: "待更新",
    milestones: []
  };
}

function placeholderFocusNote(): KnowledgeNoteSummary {
  return {
    id: "new-note",
    title: "当前还没有可直接回看的知识资产",
    excerpt: "可以先新建一条知识资产，把当前判断记录下来。",
    tags: [],
    folder: "知识资产",
    updatedAt: "待记录",
    readingMinutes: 1,
    words: 0,
    published: false,
    visibility: "private",
    visibilityLabel: "仅主系统",
    relatedPlanIds: [],
    relatedTagIds: [],
    relatedSearchTerms: ["Agent"],
    knowledgeStateLabel: "等待记录"
  };
}

function adaptFocusPlan(record: BackendHomePlan | null): PlanDetail {
  if (!record) {
    return placeholderFocusPlan();
  }

  const supplement = mockInkdeskDataSource.getPlanById(record.id);

  return {
    id: record.id,
    title: record.title,
    summary: supplement?.summary ?? record.nextStep,
    status: statusFromLabel(record.statusLabel, supplement?.status),
    statusLabel: record.statusLabel,
    horizon: horizonFromLabel(record.horizonLabel, supplement?.horizon),
    horizonLabel: record.horizonLabel,
    priority: priorityFromLabel(record.priorityLabel, supplement?.priority),
    priorityLabel: record.priorityLabel,
    focusLabel: supplement?.focusLabel ?? "当前焦点",
    nextStep: record.nextStep,
    nextActionLabel: record.nextActionLabel,
    nextActionHref: record.nextActionHref,
    relatedNoteIds: supplement?.relatedNoteIds ?? [],
    relatedTagIds: supplement?.relatedTagIds ?? [],
    relatedSearchTerms:
      record.searchTerm && record.searchTerm.trim()
        ? [normalizeLegacyProductTerm(record.searchTerm)]
        : supplement?.relatedSearchTerms ?? [record.title],
    agentPrompt: supplement?.agentPrompt ?? `围绕「${record.title}」推进下一步。`,
    updatedAt: supplement?.updatedAt ?? "待更新",
    milestones: supplement?.milestones ?? []
  };
}

function adaptHomeNote(record: BackendHomeNote): KnowledgeNoteSummary {
  const supplement = mockInkdeskDataSource.getKnowledgeNoteById(record.id);
  const textForMetrics = record.excerpt || record.title;

  return {
    id: record.id,
    title: record.title,
    excerpt: record.excerpt,
    tags: supplement?.tags ?? [],
    folder: record.folder || supplement?.folder || "知识资产",
    updatedAt: supplement?.updatedAt ?? record.updatedAt,
    readingMinutes: supplement?.readingMinutes ?? estimateReadingMinutes(textForMetrics),
    words: supplement?.words ?? countWords(textForMetrics),
    published: record.published,
    visibility: record.visibility,
    visibilityLabel: visibilityLabelFor(record.visibility),
    relatedPlanIds: supplement?.relatedPlanIds ?? [],
    relatedTagIds: supplement?.relatedTagIds ?? [],
    relatedSearchTerms: supplement?.relatedSearchTerms ?? [],
    knowledgeStateLabel: knowledgeStateLabelFor(record.published),
    slug: supplement?.slug
  };
}

function adaptPublishQueueItem(record: BackendHomePublishQueueItem): PublishEntry {
  const supplement = mockInkdeskDataSource.getKnowledgeNoteById(record.noteId);

  return {
    noteId: record.noteId,
    title: record.title,
    excerpt: record.excerpt,
    slug: supplement?.slug,
    updatedAt: supplement?.updatedAt ?? record.updatedAt,
    state: record.state,
    stateLabel: record.stateLabel,
    visibilityLabel: supplement?.visibilityLabel ?? "仅主系统",
    publicPath: supplement?.slug ? `/articles/${supplement.slug}` : undefined,
    relatedPlanIds: supplement?.relatedPlanIds ?? []
  };
}

async function getBackendHomeSnapshot(ownerSession?: string) {
  return fetchInkdeskJson<BackendHomeResponse>("/admin/home", { ownerSession });
}

export async function getWorkbenchSnapshot(ownerSession?: string): Promise<WorkbenchSnapshot> {
  if (!hasApiBaseUrl()) {
    return mockInkdeskDataSource.getWorkbenchSnapshot();
  }

  try {
    const snapshot = await getBackendHomeSnapshot(ownerSession);

    return {
      summary: snapshot.summary,
      focusPlan: adaptFocusPlan(snapshot.focusPlan),
      focusNote: snapshot.focusNote ? adaptHomeNote(snapshot.focusNote) : placeholderFocusNote(),
      suggestions: snapshot.suggestions,
      quickActions: snapshot.quickActions,
      recentKnowledge: snapshot.recentKnowledge.map(adaptHomeNote),
      publishQueue: snapshot.publishQueue.map(adaptPublishQueueItem)
    };
  } catch (error) {
    if (error instanceof InkdeskApiError) {
      throw error;
    }

    return mockInkdeskDataSource.getWorkbenchSnapshot();
  }
}
