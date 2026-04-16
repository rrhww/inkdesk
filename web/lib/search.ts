import { getKnowledgeHubData } from "@/lib/knowledge";
import { getRecentKnowledgeSummaries, getRecommendedSearchTerms, mockInkdeskDataSource } from "@/lib/mock-data-source";
import { fetchInkdeskJson, hasApiBaseUrl } from "@/lib/server-api";
import type { SearchQuery } from "@/lib/types";

type BackendSearchResult = {
  note: {
    id: string;
    title: string;
    excerpt: string | null;
    tags: string[];
    folder: string;
    updatedAt: string;
    visibility: "private" | "public";
    published: boolean;
    slug: string | null;
  };
  score: number;
  hitLabels: string[];
  matchedTerms: string[];
};

function toVisibilityLabel(visibility: "private" | "public") {
  return visibility === "public" ? "已发布" : "仅主系统";
}

function toKnowledgeStateLabel(published: boolean) {
  return published ? "已发布" : "仅主系统";
}

function buildSearchParams(query: SearchQuery) {
  const params = new URLSearchParams({
    q: query.q
  });

  if (query.visibility) {
    params.set("visibility", query.visibility);
  }

  if (query.tag) {
    params.set("tag", query.tag);
  }

  if (query.folder) {
    params.set("folder", query.folder);
  }

  return params.toString();
}

export async function searchKnowledge(query: SearchQuery, ownerSession?: string) {
  if (!hasApiBaseUrl()) {
    return mockInkdeskDataSource.searchKnowledge(query);
  }

  const results = await fetchInkdeskJson<BackendSearchResult[]>(`/admin/search?${buildSearchParams(query)}`, { ownerSession });

  return results.map((result) => {
    const supplement = mockInkdeskDataSource.getKnowledgeNoteById(result.note.id);

    return {
      note: {
        id: result.note.id,
        title: result.note.title,
        excerpt: result.note.excerpt ?? supplement?.excerpt ?? "",
        tags: result.note.tags.length > 0 ? result.note.tags : supplement?.tags ?? [],
        folder: result.note.folder || supplement?.folder || "知识资产",
        updatedAt: supplement?.updatedAt ?? result.note.updatedAt,
        readingMinutes: supplement?.readingMinutes ?? 1,
        words: supplement?.words ?? 0,
        published: result.note.published,
        visibility: result.note.visibility,
        visibilityLabel: toVisibilityLabel(result.note.visibility),
        relatedPlanIds: supplement?.relatedPlanIds ?? [],
        relatedTagIds: supplement?.relatedTagIds ?? [],
        relatedSearchTerms: supplement?.relatedSearchTerms ?? [],
        knowledgeStateLabel: supplement?.knowledgeStateLabel ?? toKnowledgeStateLabel(result.note.published),
        slug: result.note.slug ?? undefined
      },
      score: result.score,
      hitLabels: result.hitLabels,
      matchedTerms: result.matchedTerms
    };
  });
}

export async function getSearchSuggestions(ownerSession?: string) {
  if (hasApiBaseUrl()) {
    const hub = await getKnowledgeHubData(undefined, ownerSession);

    return {
      recommendedTerms: getRecommendedSearchTerms(),
      recentKnowledge: hub.notes.slice(0, 3),
      folders: Array.from(new Set(hub.notes.map((note) => note.folder))),
      tags: Array.from(new Set(hub.notes.flatMap((note) => note.tags)))
    };
  }

  return {
    recommendedTerms: getRecommendedSearchTerms(),
    recentKnowledge: getRecentKnowledgeSummaries(),
    folders: Array.from(new Set(getRecentKnowledgeSummaries().map((note) => note.folder).concat(mockInkdeskDataSource.getKnowledgeHubData().notes.map((note) => note.folder)))),
    tags: Array.from(new Set(mockInkdeskDataSource.getKnowledgeHubData().notes.flatMap((note) => note.tags)))
  };
}
