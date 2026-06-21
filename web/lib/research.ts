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

export async function getResearchDashboard(): Promise<ResearchDashboard> {
  return withResearchFallback(
    () => fetchInkdeskJson<ResearchDashboard>("/admin/home"),
    () => researchDashboardFixture
  );
}

export async function getWikiPages(): Promise<ResearchTopicSummary[]> {
  return withResearchFallback(
    () => fetchInkdeskJson<ResearchTopicSummary[]>("/wiki"),
    () => researchTopicSummariesFixture
  );
}

export async function getWikiDetail(topicId: string): Promise<ResearchTopicDetail> {
  return withResearchFallback(
    () => fetchInkdeskJson<ResearchTopicDetail>(`/wiki/${topicId}`),
    () => {
      const topic = getResearchTopicDetailFixture(topicId);
      if (!topic) {
        throw new Error(`Unknown mock topic ${topicId}`);
      }
      return topic;
    }
  );
}

export async function getRawSources(): Promise<ResearchSourceRecord[]> {
  return withResearchFallback(
    () => fetchInkdeskJson<ResearchSourceRecord[]>("/raw"),
    () => researchSourcesFixture
  );
}

export async function getIngestItems(): Promise<ResearchReviewItem[]> {
  return withResearchFallback(
    () => fetchInkdeskJson<ResearchReviewItem[]>("/ingest"),
    () => researchReviewItemsFixture
  );
}

export async function askResearch(request: ResearchAskRequest): Promise<ResearchAskResponse> {
  return withResearchFallback(
    () => postInkdeskJson<ResearchAskResponse>("/ask", request),
    () => answerResearchQuestionFixture(request)
  );
}

export async function getAskBriefing(
  input?: { topicId?: string; askTurnId?: string }
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
      return fetchInkdeskJson<ResearchAskBriefing>(`/ask/briefing${suffix}`);
    },
    () => getAskBriefingFixture(input)
  );
}

export async function proposeAskWriteback(askTurnId: string): Promise<ResearchReviewItem> {
  return withResearchFallback(
    () => postInkdeskJson<ResearchReviewItem>(`/ask/${askTurnId}/writeback`, {}),
    () => createAskWritebackFixture(askTurnId)
  );
}

export async function acceptIngest(reviewId: string) {
  return postInkdeskJson<ResearchReviewDecision>(`/ingest/${reviewId}/accept`, {});
}

export async function rejectIngest(reviewId: string) {
  return postInkdeskJson<ResearchReviewDecision>(`/ingest/${reviewId}/reject`, {});
}

export async function importWebSource(request: ResearchWebImportRequest) {
  return postInkdeskJson<ResearchSourceRecord>("/raw/web", request);
}

export async function importTextSource(request: ResearchTextImportRequest) {
  return postInkdeskJson<ResearchSourceRecord>(
    "/raw",
    {
      kind: "TEXT",
      title: request.title,
      locator: request.locator,
      excerpt: request.excerpt,
      body: request.body
    }
  );
}

export async function importPdfSource(file: File, title?: string, locator?: string) {
  const formData = new FormData();
  formData.set("file", file);
  if (title?.trim()) {
    formData.set("title", title.trim());
  }
  if (locator?.trim()) {
    formData.set("locator", locator.trim());
  }
  return postInkdeskFormData<ResearchSourceRecord>("/raw/pdf", formData);
}

export const getTopics = getWikiPages;
export const getTopicDetail = getWikiDetail;
export const getSources = getRawSources;
export const getReviewItems = getIngestItems;
export const acceptReview = acceptIngest;
export const rejectReview = rejectIngest;

export async function getVaultStatus(): Promise<VaultStatus> {
  return fetchInkdeskJson<VaultStatus>("/vault/status");
}

export async function initializeVault(request: VaultInitializeRequest): Promise<VaultStatus> {
  return postInkdeskJson<VaultStatus>("/vault/initialize", request);
}

export async function getDevRuns(): Promise<DevRunSummary[]> {
  return withResearchFallback(
    () => fetchInkdeskJson<DevRunSummary[]>("/runs"),
    () => []
  );
}

export async function getDevRun(runId: string): Promise<DevRun> {
  return fetchInkdeskJson<DevRun>(`/runs/${runId}`);
}

export async function createDevRun(request: CreateDevRunRequest): Promise<DevRun> {
  return postInkdeskJson<DevRun>("/runs", request);
}

export async function depositResearch(request: DepositRequest): Promise<DepositResponse> {
  return postInkdeskJson<DepositResponse>("/deposits", request);
}

export async function getVaultHealth(): Promise<HealthResponse> {
  return withResearchFallback(
    () => fetchInkdeskJson<HealthResponse>("/health"),
    () => vaultHealthFixture
  );
}

export async function getCompileQueue(): Promise<CompileTaskSummary[]> {
  return withResearchFallback(
    () => fetchInkdeskJson<CompileTaskSummary[]>("/compile/queue"),
    () => compileQueueFixture
  );
}

export async function getCompileTask(taskId: string): Promise<CompileTaskResponse> {
  return withResearchFallback(
    () => fetchInkdeskJson<CompileTaskResponse>(`/compile/${taskId}`),
    () => {
      const task = getCompileTaskFixture(taskId);
      if (!task) throw new Error(`Unknown mock compile task ${taskId}`);
      return task;
    }
  );
}

export async function retryCompileTask(taskId: string): Promise<CompileTaskResponse> {
  return withResearchFallback(
    () => postInkdeskJson<CompileTaskResponse>(`/compile/${taskId}/retry`, {}),
    () => {
      const task = getCompileTaskFixture("compile-failed");
      if (!task) throw new Error(`Unknown mock compile task ${taskId}`);
      return { ...task, status: "PENDING", errorMessage: null };
    }
  );
}

export async function compileSource(sourceId: string): Promise<CompileTaskResponse> {
  return withResearchFallback(
    () => postInkdeskJson<CompileTaskResponse>(`/raw/${sourceId}/compile`, {}),
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
