import {
  answerResearchQuestionFixture,
  createAskWritebackFixture,
  getAskBriefingFixture,
  getResearchTopicDetailFixture,
  researchDashboardFixture,
  researchReviewItemsFixture,
  researchSourcesFixture,
  researchTopicSummariesFixture
} from "@/lib/mock/research-fixtures";
import { fetchInkvaultJson, hasApiBaseUrl, InkvaultApiError, postInkvaultJson } from "@/lib/server-api";
import type {
  ResearchAskRequest,
  ResearchAskBriefing,
  ResearchAskResponse,
  ResearchDashboard,
  ResearchReviewDecision,
  ResearchReviewItem,
  ResearchSourceRecord,
  ResearchTextImportRequest,
  ResearchTopicDetail,
  ResearchTopicSummary,
  ResearchWebImportRequest
} from "@/lib/types";
import { postInkvaultFormData } from "@/lib/server-api";

async function withResearchFallback<T>(run: () => Promise<T>, fallback: () => T): Promise<T> {
  if (!hasApiBaseUrl()) {
    return fallback();
  }

  try {
    return await run();
  } catch (error) {
    if (error instanceof InkvaultApiError) {
      throw error;
    }

    return fallback();
  }
}

export async function getResearchDashboard(ownerSession?: string): Promise<ResearchDashboard> {
  return withResearchFallback(
    () => fetchInkvaultJson<ResearchDashboard>("/admin/home", { ownerSession }),
    () => researchDashboardFixture
  );
}

export async function getWikiPages(ownerSession?: string): Promise<ResearchTopicSummary[]> {
  return withResearchFallback(
    () => fetchInkvaultJson<ResearchTopicSummary[]>("/wiki", { ownerSession }),
    () => researchTopicSummariesFixture
  );
}

export async function getWikiDetail(topicId: string, ownerSession?: string): Promise<ResearchTopicDetail> {
  return withResearchFallback(
    () => fetchInkvaultJson<ResearchTopicDetail>(`/wiki/${topicId}`, { ownerSession }),
    () => {
      const topic = getResearchTopicDetailFixture(topicId);
      if (!topic) {
        throw new Error(`Unknown mock topic ${topicId}`);
      }
      return topic;
    }
  );
}

export async function getRawSources(ownerSession?: string): Promise<ResearchSourceRecord[]> {
  return withResearchFallback(
    () => fetchInkvaultJson<ResearchSourceRecord[]>("/raw", { ownerSession }),
    () => researchSourcesFixture
  );
}

export async function getIngestItems(ownerSession?: string): Promise<ResearchReviewItem[]> {
  return withResearchFallback(
    () => fetchInkvaultJson<ResearchReviewItem[]>("/ingest", { ownerSession }),
    () => researchReviewItemsFixture
  );
}

export async function askResearch(request: ResearchAskRequest, ownerSession?: string): Promise<ResearchAskResponse> {
  return withResearchFallback(
    () => postInkvaultJson<ResearchAskResponse>("/ask", request, { ownerSession }),
    () => answerResearchQuestionFixture(request)
  );
}

export async function getAskBriefing(
  input?: { topicId?: string; askTurnId?: string },
  ownerSession?: string
): Promise<ResearchAskBriefing> {
  return withResearchFallback(
    () => {
      const params = new URLSearchParams();
      if (input?.topicId) {
        params.set("topicId", input.topicId);
      }
      if (input?.askTurnId) {
        params.set("askTurnId", input.askTurnId);
      }
      const suffix = params.toString() ? `?${params.toString()}` : "";
      return fetchInkvaultJson<ResearchAskBriefing>(`/ask/briefing${suffix}`, { ownerSession });
    },
    () => getAskBriefingFixture(input)
  );
}

export async function proposeAskWriteback(askTurnId: string, ownerSession?: string): Promise<ResearchReviewItem> {
  return withResearchFallback(
    () => postInkvaultJson<ResearchReviewItem>(`/ask/${askTurnId}/writeback`, {}, { ownerSession }),
    () => createAskWritebackFixture(askTurnId)
  );
}

export async function acceptIngest(reviewId: string, ownerSession?: string) {
  return postInkvaultJson<ResearchReviewDecision>(`/ingest/${reviewId}/accept`, {}, { ownerSession });
}

export async function rejectIngest(reviewId: string, ownerSession?: string) {
  return postInkvaultJson<ResearchReviewDecision>(`/ingest/${reviewId}/reject`, {}, { ownerSession });
}

export async function importWebSource(request: ResearchWebImportRequest, ownerSession?: string) {
  return postInkvaultJson<ResearchSourceRecord>("/raw/web", request, { ownerSession });
}

export async function importTextSource(request: ResearchTextImportRequest, ownerSession?: string) {
  return postInkvaultJson<ResearchSourceRecord>(
    "/raw",
    {
      kind: "TEXT",
      title: request.title,
      locator: request.locator,
      excerpt: request.excerpt,
      body: request.body
    },
    { ownerSession }
  );
}

export async function importPdfSource(file: File, title?: string, ownerSession?: string, locator?: string) {
  const formData = new FormData();
  formData.set("file", file);
  if (title?.trim()) {
    formData.set("title", title.trim());
  }
  if (locator?.trim()) {
    formData.set("locator", locator.trim());
  }
  return postInkvaultFormData<ResearchSourceRecord>("/raw/pdf", formData, { ownerSession });
}

export const getTopics = getWikiPages;
export const getTopicDetail = getWikiDetail;
export const getSources = getRawSources;
export const getReviewItems = getIngestItems;
export const acceptReview = acceptIngest;
export const rejectReview = rejectIngest;
