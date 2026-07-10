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
  ContextPackSummary,
  CreateDevRunRequest,
  DepositRequest,
  DepositResponse,
  DevRun,
  DevRunSummary,
  EvalRunManifest,
  GoldenTasksResponse,
  HealthRunSummary,
  HealthResponse,
  HealthTrendResponse,
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
  SkillDetail,
  SkillRegistrySummary,
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

export async function submitStageOutput(
  runId: string,
  stage: string,
  payload: Record<string, unknown>,
): Promise<DevRun> {
  return postInkdeskJson<DevRun>(`/runs/${runId}/events`, {
    stage,
    eventType: "stage_output",
    payload,
  });
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

// ── Health History ──

export async function createHealthSnapshot(): Promise<HealthResponse> {
  return withResearchFallback(
    () => postInkdeskJson<HealthResponse>("/health/runs", {}),
    () => vaultHealthFixture
  );
}

export async function getHealthTrend(): Promise<HealthTrendResponse> {
  return withResearchFallback(
    () => fetchInkdeskJson<HealthTrendResponse>("/health/runs"),
    () => ({ current: null, recent: [], currentFindings: null })
  );
}

export async function getHealthRun(runId: string): Promise<HealthRunSummary> {
  return fetchInkdeskJson<HealthRunSummary>(`/health/runs/${runId}`);
}

// ── Golden Tasks ──

export async function getGoldenTasks(): Promise<GoldenTasksResponse> {
  return withResearchFallback(
    () => fetchInkdeskJson<GoldenTasksResponse>("/evals/golden"),
    () => ({ schemaVersion: "1.0.0", tasks: [] })
  );
}

export async function createEvalRun(taskIds: string[], rubricIds: string[]): Promise<EvalRunManifest> {
  return postInkdeskJson<EvalRunManifest>("/evals/runs", { taskIds, rubricIds });
}

export async function getEvalRun(evalRunId: string): Promise<EvalRunManifest> {
  return fetchInkdeskJson<EvalRunManifest>(`/evals/runs/${evalRunId}`);
}

// ── Stage Actions ──

export async function generateContextPack(runId: string): Promise<DevRun> {
  return postInkdeskJson<DevRun>(`/runs/${runId}/context-pack`, {});
}

export function extractContextPackSummary(run: DevRun): ContextPackSummary | null {
  const event = [...run.events]
    .reverse()
    .find((e) => e.eventType === "context_pack_generated" && e.stage === "context");
  if (!event) return null;
  const payload = event.payload as Record<string, unknown>;
  return {
    wikiPageCount: (payload.wikiPageCount as number) ?? 0,
    askHistoryCount: (payload.askHistoryCount as number) ?? 0,
    pendingReviewCount: (payload.pendingReviewCount as number) ?? 0,
    title: (payload.title as string) ?? "",
    goal: (payload.goal as string) ?? "",
    repoContext: (payload.repoContext as string | null) ?? null,
  };
}

export async function depositRun(runId: string): Promise<DevRun> {
  return postInkdeskJson<DevRun>(`/runs/${runId}/deposit`, {});
}

export function extractDepositInfo(run: DevRun): { reviewId: string; isNew: boolean } | null {
  const event = [...run.events]
    .reverse()
    .find((e) => e.eventType === "deposit_created" && e.stage === "deposit");
  if (!event) return null;
  const payload = event.payload as Record<string, unknown>;
  return {
    reviewId: (payload.reviewId as string) ?? "",
    isNew: (payload.isNew as boolean) ?? false,
  };
}

// ── Solution ──

export async function generateSolution(runId: string): Promise<DevRun> {
  return postInkdeskJson<DevRun>(`/runs/${runId}/solution`, {});
}

export type SolutionDraft = {
  draft: string;
  risks: string[];
};

export function extractSolutionDraft(run: DevRun): SolutionDraft | null {
  const event = [...run.events]
    .reverse()
    .find((e) => e.eventType === "solution_draft_generated" && e.stage === "solution");
  if (!event) return null;
  const payload = event.payload as Record<string, unknown>;
  return {
    draft: (payload.draft as string) ?? "",
    risks: (payload.risks as string[]) ?? [],
  };
}

// ── Review ──

export async function generateReviewChecklist(runId: string): Promise<DevRun> {
  return postInkdeskJson<DevRun>(`/runs/${runId}/review`, {});
}

export type ReviewChecklist = {
  checklist: string[];
  summary: string;
};

export function extractReviewChecklist(run: DevRun): ReviewChecklist | null {
  const event = [...run.events]
    .reverse()
    .find((e) => e.eventType === "review_checklist_generated" && e.stage === "review");
  if (!event) return null;
  const payload = event.payload as Record<string, unknown>;
  return {
    checklist: (payload.checklist as string[]) ?? [],
    summary: (payload.summary as string) ?? "",
  };
}

// ── Coding ──

export async function executeCoding(runId: string): Promise<DevRun> {
  return postInkdeskJson<DevRun>(`/runs/${runId}/coding/execute`, {});
}

export type CodingStatus = "idle" | "running" | "completed" | "failed";

export type CodingExecutionState = {
  status: CodingStatus;
  briefing: string | null;
  result: string | null;
  error: string | null;
  success: boolean | null;
};

export async function getCodingStatus(runId: string): Promise<CodingExecutionState> {
  return fetchInkdeskJson<CodingExecutionState>(`/runs/${runId}/coding/status`);
}

export function extractCodingBriefing(run: DevRun): string | null {
  const event = [...run.events]
    .reverse()
    .find((e) => e.eventType === "coding_briefing_prepared" && e.stage === "coding");
  if (!event) return null;
  return (event.payload as Record<string, unknown>).briefing as string ?? null;
}

export function extractCodingResult(run: DevRun): { result: string; success: boolean; error: string | null } | null {
  const event = [...run.events]
    .reverse()
    .find((e) => e.eventType === "coding_result_submitted" && e.stage === "coding");
  if (!event) return null;
  const payload = event.payload as Record<string, unknown>;
  return {
    result: (payload.result as string) ?? "",
    success: (payload.success as boolean) ?? false,
    error: (payload.error as string | null) ?? null,
  };
}

// ── Testing ──

export async function generateTestingChecklist(runId: string): Promise<DevRun> {
  return postInkdeskJson<DevRun>(`/runs/${runId}/testing`, {});
}

export type TestingChecklist = {
  checklist: string[];
  summary: string;
};

export function extractTestingChecklist(run: DevRun): TestingChecklist | null {
  const event = [...run.events]
    .reverse()
    .find((e) => e.eventType === "testing_checklist_generated" && e.stage === "testing");
  if (!event) return null;
  const payload = event.payload as Record<string, unknown>;
  return {
    checklist: (payload.checklist as string[]) ?? [],
    summary: (payload.summary as string) ?? "",
  };
}

// ── Skill Workbench ──

export async function getSkills(): Promise<SkillRegistrySummary> {
  return withResearchFallback(
    () => fetchInkdeskJson<SkillRegistrySummary>("/skills"),
    () => ({ total: 0, valid: 0, invalid: 0, byStatus: { draft: 0, active: 0, deprecated: 0 }, skills: [] })
  );
}

export async function getSkillDetail(skillName: string): Promise<SkillDetail> {
  return fetchInkdeskJson<SkillDetail>(`/skills/${skillName}`);
}
