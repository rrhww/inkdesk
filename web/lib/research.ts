import {
  answerResearchQuestionFixture,
  compileQueueFixture,
  createAskWritebackFixture,
  getAskBriefingFixture,
  getCompileTaskFixture,
  getResearchTopicDetailFixture,
  researchDashboardFixture,
  researchReviewItemsFixture,
  researchSourcesFixture,
  researchTopicSummariesFixture,
  vaultHealthFixture
} from "@/lib/mock/research-fixtures";
import { fetchInkdeskJson, hasApiBaseUrl, InkdeskApiError, postInkdeskJson } from "@/lib/server-api";
import type {
  CompileTaskResponse,
  CompileTaskSummary,
  CreateDevRunRequest,
  DepositRequest,
  DepositResponse,
  DevRun,
  DevRunSummary,
  HealthResponse,
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
  ResearchWebImportRequest,
  VaultInitializeRequest,
  VaultStatus,
} from "@/lib/types";
import { postInkdeskFormData } from "@/lib/server-api";

async function withResearchFallback<T>(run: () => Promise<T>, fallback: () => T): Promise<T> {
  if (!hasApiBaseUrl()) {
    return fallback();
  }

  try {
    return await run();
  } catch (error) {
    if (error instanceof InkdeskApiError) {
      throw error;
    }

    return fallback();
  }
}

export async function getResearchDashboard(ownerSession?: string): Promise<ResearchDashboard> {
  return withResearchFallback(
    () => fetchInkdeskJson<ResearchDashboard>("/admin/home", { ownerSession }),
    () => researchDashboardFixture
  );
}

export async function getWikiPages(ownerSession?: string): Promise<ResearchTopicSummary[]> {
  return withResearchFallback(
    () => fetchInkdeskJson<ResearchTopicSummary[]>("/wiki", { ownerSession }),
    () => researchTopicSummariesFixture
  );
}

export async function getWikiDetail(topicId: string, ownerSession?: string): Promise<ResearchTopicDetail> {
  return withResearchFallback(
    () => fetchInkdeskJson<ResearchTopicDetail>(`/wiki/${topicId}`, { ownerSession }),
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
    () => fetchInkdeskJson<ResearchSourceRecord[]>("/raw", { ownerSession }),
    () => researchSourcesFixture
  );
}

export async function getIngestItems(ownerSession?: string): Promise<ResearchReviewItem[]> {
  return withResearchFallback(
    () => fetchInkdeskJson<ResearchReviewItem[]>("/ingest", { ownerSession }),
    () => researchReviewItemsFixture
  );
}

export async function askResearch(request: ResearchAskRequest, ownerSession?: string): Promise<ResearchAskResponse> {
  return withResearchFallback(
    () => postInkdeskJson<ResearchAskResponse>("/ask", request, { ownerSession }),
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
      return fetchInkdeskJson<ResearchAskBriefing>(`/ask/briefing${suffix}`, { ownerSession });
    },
    () => getAskBriefingFixture(input)
  );
}

export async function proposeAskWriteback(askTurnId: string, ownerSession?: string): Promise<ResearchReviewItem> {
  return withResearchFallback(
    () => postInkdeskJson<ResearchReviewItem>(`/ask/${askTurnId}/writeback`, {}, { ownerSession }),
    () => createAskWritebackFixture(askTurnId)
  );
}

export async function acceptIngest(reviewId: string, ownerSession?: string) {
  return postInkdeskJson<ResearchReviewDecision>(`/ingest/${reviewId}/accept`, {}, { ownerSession });
}

export async function rejectIngest(reviewId: string, ownerSession?: string) {
  return postInkdeskJson<ResearchReviewDecision>(`/ingest/${reviewId}/reject`, {}, { ownerSession });
}

export async function importWebSource(request: ResearchWebImportRequest, ownerSession?: string) {
  return postInkdeskJson<ResearchSourceRecord>("/raw/web", request, { ownerSession });
}

export async function importTextSource(request: ResearchTextImportRequest, ownerSession?: string) {
  return postInkdeskJson<ResearchSourceRecord>(
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
  return postInkdeskFormData<ResearchSourceRecord>("/raw/pdf", formData, { ownerSession });
}

export const getTopics = getWikiPages;
export const getTopicDetail = getWikiDetail;
export const getSources = getRawSources;
export const getReviewItems = getIngestItems;
export const acceptReview = acceptIngest;
export const rejectReview = rejectIngest;

export async function getVaultStatus(ownerSession?: string): Promise<VaultStatus> {
  return fetchInkdeskJson<VaultStatus>("/vault/status", { ownerSession });
}

export async function initializeVault(request: VaultInitializeRequest, ownerSession?: string): Promise<VaultStatus> {
  return postInkdeskJson<VaultStatus>("/vault/initialize", request, { ownerSession });
}

export async function getDevRuns(ownerSession?: string): Promise<DevRunSummary[]> {
  return withResearchFallback(
    () => fetchInkdeskJson<DevRunSummary[]>("/runs", { ownerSession }),
    () => []
  );
}

export async function getDevRun(runId: string, ownerSession?: string): Promise<DevRun> {
  return fetchInkdeskJson<DevRun>(`/runs/${runId}`, { ownerSession });
}

export async function createDevRun(request: CreateDevRunRequest, ownerSession?: string): Promise<DevRun> {
  return postInkdeskJson<DevRun>("/runs", request, { ownerSession });
}

export async function depositResearch(request: DepositRequest, ownerSession?: string): Promise<DepositResponse> {
  return postInkdeskJson<DepositResponse>("/deposits", request, { ownerSession });
}

export async function getVaultHealth(ownerSession?: string): Promise<HealthResponse> {
  return withResearchFallback(
    () => fetchInkdeskJson<HealthResponse>("/health", { ownerSession }),
    () => vaultHealthFixture
  );
}

export async function getCompileQueue(ownerSession?: string): Promise<CompileTaskSummary[]> {
  return withResearchFallback(
    () => fetchInkdeskJson<CompileTaskSummary[]>("/compile/queue", { ownerSession }),
    () => compileQueueFixture
  );
}

export async function getCompileTask(taskId: string, ownerSession?: string): Promise<CompileTaskResponse> {
  return withResearchFallback(
    () => fetchInkdeskJson<CompileTaskResponse>(`/compile/${taskId}`, { ownerSession }),
    () => {
      const task = getCompileTaskFixture(taskId);
      if (!task) throw new Error(`Unknown mock compile task ${taskId}`);
      return task;
    }
  );
}

export async function retryCompileTask(taskId: string, ownerSession?: string): Promise<CompileTaskResponse> {
  return withResearchFallback(
    () => postInkdeskJson<CompileTaskResponse>(`/compile/${taskId}/retry`, {}, { ownerSession }),
    () => {
      const task = getCompileTaskFixture("compile-failed");
      if (!task) throw new Error(`Unknown mock compile task ${taskId}`);
      return { ...task, status: "PENDING", errorMessage: null };
    }
  );
}

export async function compileSource(sourceId: string, ownerSession?: string): Promise<CompileTaskResponse> {
  return withResearchFallback(
    () => postInkdeskJson<CompileTaskResponse>(`/raw/${sourceId}/compile`, {}, { ownerSession }),
    () => ({
      id: `compile-new-${sourceId}`,
      sourceId,
      status: "PENDING",
      errorMessage: null,
      createdAt: new Date().toISOString(),
      startedAt: null,
      completedAt: null,
      steps: [],
      isNew: true,
    })
  );
}