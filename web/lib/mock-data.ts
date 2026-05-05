import {
  agentSuggestionsFixture,
  authorProfileFixture,
  notesFixture,
  plansFixture,
  publicKnowledgeBucketsFixture,
  publicProjectsFixture,
  publicUpdatesFixture
} from "@/lib/mock/fixtures";

export const authorProfile = authorProfileFixture;
export const publicProjects = publicProjectsFixture;
export const publicKnowledgeBuckets = publicKnowledgeBucketsFixture;
export const publicUpdates = publicUpdatesFixture;
export const agentSuggestions = agentSuggestionsFixture;
export const plans = plansFixture;
export const notes = notesFixture;

function updatedAtValue(updatedAt: string) {
  return Date.parse(updatedAt.replace(" ", "T"));
}

function sortByUpdatedAt<T extends { updatedAt: string }>(records: T[]) {
  return [...records].sort((left, right) => updatedAtValue(right.updatedAt) - updatedAtValue(left.updatedAt));
}

export const workbenchSummary = {
  activePlans: plans.filter((plan) => plan.status === "active").length,
  privateNotes: notes.filter((note) => !note.published).length,
  publishedNotes: notes.filter((note) => note.published).length
};

export const knowledgeHubSummary = {
  totalNotes: notes.length,
  privateNotes: notes.filter((note) => note.visibility === "private").length,
  publicNotes: notes.filter((note) => note.visibility === "public").length,
  linkedNotes: notes.filter((note) => note.relatedPlanIds.length > 0).length
};

export const planWorkbenchSummary = {
  todayPlans: plans.filter((plan) => plan.horizon === "today" && plan.status !== "done").length,
  activePlans: plans.filter((plan) => plan.status === "active").length,
  queuedPlans: plans.filter((plan) => plan.status === "queued").length,
  linkedNotes: new Set(plans.flatMap((plan) => plan.relatedNoteIds)).size
};

export function filterKnowledgeNotes(filter: "all" | "private" | "published" | "recent" = "all") {
  const sorted = sortByUpdatedAt(notes);

  switch (filter) {
    case "private":
      return sorted.filter((note) => note.visibility === "private");
    case "published":
      return sorted.filter((note) => note.visibility === "public");
    case "recent":
      return sorted.slice(0, 2);
    default:
      return sorted;
  }
}

export function searchKnowledgeNotes(query: string) {
  const normalized = query.trim().toLowerCase();

  if (!normalized) {
    return [];
  }

  return sortByUpdatedAt(notes)
    .map((note) => {
      const hitLabels: string[] = [];
      let score = 0;

      if (note.title.toLowerCase().includes(normalized)) {
        score += 6;
        hitLabels.push("标题");
      }

      if (note.tags.some((tag) => tag.toLowerCase().includes(normalized))) {
        score += 5;
        hitLabels.push("标签");
      }

      if (note.excerpt.toLowerCase().includes(normalized)) {
        score += 4;
        hitLabels.push("摘要");
      }

      return {
        note,
        score,
        hitLabels: Array.from(new Set(hitLabels))
      };
    })
    .filter((entry) => entry.score > 0)
    .sort((left, right) => right.score - left.score || updatedAtValue(right.note.updatedAt) - updatedAtValue(left.note.updatedAt));
}

export function getPlanWorkflowLanes() {
  return [
    {
      key: "today" as const,
      title: "今天推进",
      description: "先把今天必须收口的事项处理掉，让主系统继续向前。",
      plans: sortByUpdatedAt(plans.filter((plan) => plan.horizon === "today" && plan.status !== "done"))
    },
    {
      key: "active" as const,
      title: "持续推进",
      description: "这些计划还需要连续几轮迭代，不抢第一屏，但不能掉出视野。",
      plans: sortByUpdatedAt(plans.filter((plan) => plan.status === "active" && plan.horizon !== "today"))
    },
    {
      key: "queued" as const,
      title: "等待下一轮",
      description: "方向已经明确，先暂存为下一轮的行动入口。",
      plans: sortByUpdatedAt(plans.filter((plan) => plan.status === "queued"))
    }
  ];
}

export function getNotesByIds(ids: string[]) {
  return ids.map((id) => notes.find((note) => note.id === id)).filter(Boolean);
}
