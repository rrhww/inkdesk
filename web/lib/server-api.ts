export class InkdeskApiError extends Error {
  status: number;
  code?: string;

  constructor(status: number, message: string, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function normalizeApiBaseUrl(baseUrl: string) {
  const normalized = baseUrl.trim().replace(/\/+$/, "");

  if (!normalized) {
    return null;
  }

  return normalized.endsWith("/api") ? normalized : `${normalized}/api`;
}

export function resolveApiBaseUrl() {
  if (typeof window !== "undefined") {
    return "/api";
  }

  return normalizeApiBaseUrl(process.env.INKDESK_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "");
}

export function hasApiBaseUrl() {
  return Boolean(resolveApiBaseUrl());
}

type RequestInkdeskOptions = {
  method?: "GET" | "POST" | "PATCH";
  body?: unknown | FormData;
};

function buildHeaders(options?: RequestInkdeskOptions) {
  if (options?.body !== undefined && !(options.body instanceof FormData)) {
    return { "Content-Type": "application/json" };
  }
  return undefined;
}

async function requestInkdesk(path: string, options?: RequestInkdeskOptions) {
  const apiBaseUrl = resolveApiBaseUrl();

  if (!apiBaseUrl) {
    throw new InkdeskApiError(500, "Inkdesk API base URL is not configured");
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    cache: "no-store",
    method: options?.method ?? "GET",
    headers: buildHeaders(options),
    body:
      options?.body === undefined
        ? undefined
        : options.body instanceof FormData
          ? options.body
          : JSON.stringify(options.body)
  });

  if (!response.ok) {
    // 读取后端结构化错误响应 {"code": "...", "message": "..."}，传递给上层 UI
    let code: string | undefined;
    let message = `Inkdesk API request failed for ${path}`;
    try {
      const body = await response.json();
      if (body && typeof body === "object") {
        if (typeof body.message === "string" && body.message) {
          message = body.message;
        }
        if (typeof body.code === "string" && body.code) {
          code = body.code;
        }
      }
    } catch {
      // 响应体不是 JSON，保留通用文案
    }
    throw new InkdeskApiError(response.status, message, code);
  }

  return response;
}

export async function fetchInkdeskJson<T>(path: string) {
  const response = await requestInkdesk(path, { method: "GET" });
  return (await response.json()) as T;
}

export async function postInkdeskJson<T>(path: string, body: unknown) {
  const response = await requestInkdesk(path, { method: "POST", body });
  return (await response.json()) as T;
}

export async function patchInkdeskJson<T>(path: string, body: unknown) {
  const response = await requestInkdesk(path, { method: "PATCH", body });
  return (await response.json()) as T;
}

export async function postInkdesk(path: string, options?: { body?: unknown }) {
  await requestInkdesk(path, { method: "POST", body: options?.body });
}

export async function postInkdeskFormData<T>(path: string, body: FormData) {
  const response = await requestInkdesk(path, { method: "POST", body });
  return (await response.json()) as T;
}

export type GraphSnapshotNode = {
  id: string;
  label: string;
  kind: string;
  path: string;
  source: string;
  status: string;
  summary: string;
};

export type GraphSnapshotEdge = {
  id: string;
  source: string;
  target: string;
  kind: string;
};

export type GraphSnapshot = {
  version: string;
  generatedAt: string;
  nodes: GraphSnapshotNode[];
  edges: GraphSnapshotEdge[];
  stats: {
    nodeCount: number;
    edgeCount: number;
    missingCount: number;
  };
};

export type GraphNodeDocument = {
  id: string;
  title: string;
  sourcePath: string;
  content: string;
};

export type GraphStreamStatus = "connecting" | "connected" | "offline";
export type GraphScope = "all" | "vault" | "repo";

export type GraphStreamEvent =
  | { type: "graph.snapshot"; snapshot: GraphSnapshot }
  | { type: "graph.updated"; reason?: string; snapshot: GraphSnapshot }
  | { type: "node.active"; nodeId: string }
  | { type: "node.idle"; nodeId: string };

export type StageStatus =
  | "pending"
  | "ready"
  | "running"
  | "succeeded"
  | "failed"
  | "blocked"
  | "skipped"
  | "cancelled";

export type HarnessFinding = {
  id: string;
  dimension: string;
  severity: "low" | "medium" | "high" | "critical";
  confidence: "low" | "medium" | "high";
  title: string;
  consequence: string;
  causeChain: string;
  owner: string;
  evidence: string[];
  expectedArtifact: string;
  repairScope: string;
  verifiers: string[];
  status: string;
};

export type HarnessRun = {
  id: string;
  capabilityId: string;
  executor: string;
  inputs: { target: string; depth: string; repoPath?: string };
  status: string;
  sourceHead: string;
  sourceDirty?: boolean;
  createdAt: string;
  updatedAt: string;
  stageStates: Record<string, StageStatus>;
  reportPath?: string | null;
  error?: { code: string; message: string } | null;
  sessionSummaries?: Array<Record<string, unknown>>;
  evidence?: {
    sessionEvidenceStatus: string;
    envelopes: Record<string, { status: string; summaryFacts: string[]; evidence: unknown[] }>;
  } | null;
  findings?: {
    dimensionScores: Record<string, number>;
    findings: HarnessFinding[];
    supportTrack: string;
  } | null;
};

export type HarnessPermission = {
  id: string;
  runId: string;
  stageId: string;
  sessionId: string;
  toolUseId: string;
  tool: string;
  inputPreview: Record<string, unknown>;
  status: "pending" | "allowed" | "denied" | "expired" | "cancelled";
  createdAt: string;
  expiresAt: string;
  resolvedAt?: string | null;
  reason?: string | null;
};

export type HarnessRunEvent = {
  sequence: number;
  type: string;
  timestamp: string;
  data: Record<string, unknown>;
};

export type KnowledgeHealthSignal = {
  id?: string;
  type: "missing_link" | "stale" | "unsupported" | "conflicting" | "open_question";
  severity: "info" | "warning" | "critical";
  title: string;
  detail: string;
  sourcePath?: string | null;
};

export type KnowledgeSource = {
  id: string;
  documentId: string;
  title: string;
  path: string;
  source: string;
  kind: string;
  summary: string;
  updatedAt: string;
  href?: string | null;
  locator?: Record<string, string | number> | null;
  excerpt?: string;
  contentHash?: string | null;
  sourceCoverage?: string;
  provenanceStatus?: string;
};

export type KnowledgeTopic = {
  id: string;
  title: string;
  summary: string;
  path: string;
  source: string;
  kind: string;
  status: string;
  updatedAt: string;
  sourceCount: number;
  openQuestionCount: number;
  signalCount: number;
  signals: KnowledgeHealthSignal[];
  healthSignals?: KnowledgeHealthSignal[];
  vaultPath?: string | null;
  sourceCoverage?: string;
  provenanceStatus?: string;
};

export type KnowledgeTopicList = {
  topics: KnowledgeTopic[];
  stats: {
    topicCount: number;
    sourceCount: number;
    signalCount: number;
    attentionCount?: number;
  };
};

export type KnowledgeBriefing = KnowledgeTopic & {
  currentUnderstanding: string[];
  keyDecisions: string[];
  openQuestions: string[];
  codePaths: string[];
  relatedTopics: Array<{ id: string; title: string; kind: string }>;
  sources: KnowledgeSource[];
  confidence: number;
  documentId: string;
};

export type KnowledgeSearchResult = {
  query: string;
  results: KnowledgeTopic[];
};

export type TaskOriginType = "realtime_requirement" | "knowledge_signal" | "execution_finding" | "manual";
export type TaskStatus = "backlog" | "ready" | "doing" | "review" | "blocked" | "done";
export type TaskContextStatus = "pending" | "searching" | "ready" | "gap" | "failed";

export type DevelopmentTask = {
  id: string;
  title: string;
  goal: string;
  status: TaskStatus;
  originType: TaskOriginType;
  originRef?: string | null;
  priority: string;
  risk: string;
  contextStatus: TaskContextStatus;
  knowledgeTopicIds: string[];
  version: number;
  createdAt: string;
  updatedAt: string;
  contextPack?: Record<string, unknown> | null;
  knowledgeGap?: Record<string, unknown> | null;
};

export type KnowledgeSignalRecord = KnowledgeHealthSignal & {
  id: string;
  topicId: string;
  status: "open" | "acknowledged" | "resolved" | "dismissed";
  refs: { claimIds?: string[]; evidenceIds?: string[] };
  version: number;
  detail: string;
};

export type KnowledgeClaim = {
  id: string;
  topicId: string;
  text: string;
  status: string;
  sourcePath?: string | null;
  locator: Record<string, string | number>;
  contentHash: string;
  evidence: KnowledgeEvidence[];
};

export type KnowledgeEvidence = {
  id: string;
  claimId: string;
  sourceId?: string | null;
  sourcePath: string;
  locator: Record<string, string | number>;
  stance: string;
  excerpt: string;
  contentHash: string;
};

export type KnowledgeReview = {
  id: string;
  signalId?: string | null;
  topicId: string;
  action: string;
  proposal: Record<string, unknown>;
  note?: string | null;
  status: string;
  createdAt: string;
  decidedAt?: string | null;
};

function isGraphSnapshot(value: unknown): value is GraphSnapshot {
  if (!value || typeof value !== "object") {
    return false;
  }
  const snapshot = value as Partial<GraphSnapshot>;
  return typeof snapshot.version === "string" && Array.isArray(snapshot.nodes) && Array.isArray(snapshot.edges);
}

function subscribeToGraphEvents(
  onEvent: (event: GraphStreamEvent) => void,
  onStatusChange: (status: GraphStreamStatus) => void,
  scope: GraphScope = "all"
) {
  const apiBaseUrl = resolveApiBaseUrl();
  if (!apiBaseUrl) {
    onStatusChange("offline");
    return () => undefined;
  }

  let closed = false;
  const scopeQuery = scope === "all" ? "" : `?source=${scope}`;
  const eventSource = new EventSource(`${apiBaseUrl}/graph/stream${scopeQuery}`);
  onStatusChange("connecting");
  eventSource.onopen = () => {
    if (!closed) {
      onStatusChange("connected");
    }
  };
  eventSource.onerror = () => {
    if (!closed) {
      onStatusChange("offline");
    }
  };

  const addGraphListener = (eventName: "graph.snapshot" | "graph.updated") => {
    eventSource.addEventListener(eventName, ((rawEvent: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(rawEvent.data) as unknown;
        const snapshot =
          eventName === "graph.snapshot"
            ? payload
            : (payload as { snapshot?: unknown }).snapshot;
        if (!isGraphSnapshot(snapshot)) {
          return;
        }
        if (eventName === "graph.snapshot") {
          onEvent({ type: eventName, snapshot });
          return;
        }
        const reason = (payload as { reason?: unknown }).reason;
        onEvent({
          type: eventName,
          ...(typeof reason === "string" ? { reason } : {}),
          snapshot
        });
      } catch {
        // Ignore malformed stream items and keep the connection alive.
      }
    }) as EventListener);
  };

  addGraphListener("graph.snapshot");
  addGraphListener("graph.updated");
  for (const [eventName, type] of [
    ["node.active", "node.active"],
    ["node_active", "node.active"],
    ["node.idle", "node.idle"],
    ["node_idle", "node.idle"]
  ] as const) {
    eventSource.addEventListener(eventName, ((rawEvent: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(rawEvent.data) as { nodeId?: unknown; node_id?: unknown };
        const nodeId = payload.nodeId ?? payload.node_id;
        if (typeof nodeId === "string") {
          onEvent({ type, nodeId });
        }
      } catch {
        // Ignore malformed stream items and keep the connection alive.
      }
    }) as EventListener);
  }

  return () => {
    closed = true;
    eventSource.close();
  };
}

function subscribeToRunEvents(
  runId: string,
  onEvent: (event: HarnessRunEvent) => void,
  onStatusChange: (status: GraphStreamStatus) => void
) {
  const apiBaseUrl = resolveApiBaseUrl();
  if (!apiBaseUrl) {
    onStatusChange("offline");
    return () => undefined;
  }
  let closed = false;
  const eventSource = new EventSource(`${apiBaseUrl}/runs/${encodeURIComponent(runId)}/events`);
  onStatusChange("connecting");
  eventSource.onopen = () => !closed && onStatusChange("connected");
  eventSource.onerror = () => !closed && onStatusChange("offline");
  const names = [
    "run.opened",
    "stage.started",
    "stage.succeeded",
    "stage.failed",
    "executor.session.started",
    "executor.session.completed",
    "executor.delta",
    "executor.probe.started",
    "executor.probe.completed",
    "executor.tool.requested",
    "executor.tool.approved",
    "executor.tool.started",
    "executor.tool.completed",
    "executor.tool.failed",
    "executor.tool_denied",
    "workspace.prepared",
    "workspace.released",
    "finding.created",
    "artifact.validated",
    "artifact.written",
    "run.succeeded",
    "run.failed",
    "run.cancelled",
    "run.stale",
    "stream.end"
  ];
  for (const name of names) {
    eventSource.addEventListener(name, ((rawEvent: MessageEvent<string>) => {
      try {
        const value = JSON.parse(rawEvent.data) as HarnessRunEvent;
        if (typeof value.sequence === "number" && value.type === name) {
          onEvent(value);
          if (name === "stream.end") {
            closed = true;
            eventSource.close();
            onStatusChange("connected");
          }
        }
      } catch {
        // Persisted stream continues after malformed client input.
      }
    }) as EventListener);
  }
  return () => {
    closed = true;
    eventSource.close();
  };
}

function subscribeToKnowledgeEvents(onUpdate: (event: { version?: string }) => void) {
  const apiBaseUrl = resolveApiBaseUrl();
  if (!apiBaseUrl) {
    return () => undefined;
  }
  const source = new EventSource(`${apiBaseUrl}/knowledge/stream`);
  const handle = (event: MessageEvent) => {
    try {
      onUpdate(JSON.parse(event.data));
    } catch {
      // Ignore malformed invalidation events.
    }
  };
  source.addEventListener("knowledge.updated", handle);
  source.onmessage = handle;
  return () => source.close();
}

function subscribeToTaskEvents(
  onUpdate: (event: { taskId: string | null; version: number | null }) => void,
  onStatus?: (status: "connecting" | "connected" | "offline") => void
) {
  const apiBaseUrl = resolveApiBaseUrl();
  if (!apiBaseUrl) {
    onStatus?.("offline");
    return () => undefined;
  }
  onStatus?.("connecting");
  const source = new EventSource(`${apiBaseUrl}/tasks/stream`);
  source.onopen = () => onStatus?.("connected");
  const handle = (event: MessageEvent) => {
    try {
      onUpdate(JSON.parse(event.data));
    } catch {
      // Ignore malformed invalidation events.
    }
  };
  source.addEventListener("tasks.updated", handle);
  source.onmessage = handle;
  source.onerror = () => {
    source.close();
    onStatus?.("offline");
  };
  return () => source.close();
}

export const ServerAPI = {
  fetchGraphTopology: (scope: GraphScope = "all") =>
    fetchInkdeskJson<GraphSnapshot>(scope === "all" ? "/graph" : `/graph?source=${scope}`),
  fetchNodeDocument: (nodeId: string) =>
    fetchInkdeskJson<GraphNodeDocument>(`/graph/document?nodeId=${encodeURIComponent(nodeId)}`),
  fetchHarnessRun: (runId: string) => fetchInkdeskJson<HarnessRun>(`/runs/${encodeURIComponent(runId)}`),
  fetchHarnessReport: (runId: string) =>
    fetchInkdeskJson<{ runId: string; content: string }>(`/runs/${encodeURIComponent(runId)}/report`),
  cancelHarnessRun: (runId: string) => postInkdeskJson<HarnessRun>(`/runs/${encodeURIComponent(runId)}/cancel`, {}),
  fetchHarnessPermissions: (runId: string) =>
    fetchInkdeskJson<HarnessPermission[]>(`/runs/${encodeURIComponent(runId)}/permissions?status=pending`),
  decideHarnessPermission: (runId: string, permissionId: string, decision: "allow_once" | "deny") =>
    postInkdeskJson<HarnessPermission>(
      `/runs/${encodeURIComponent(runId)}/permissions/${encodeURIComponent(permissionId)}/decision`,
      { decision }
    ),
  fetchKnowledgeTopics: () => fetchInkdeskJson<KnowledgeTopicList>("/knowledge/topics"),
  searchKnowledge: (query: string) =>
    fetchInkdeskJson<KnowledgeSearchResult>(`/knowledge/search?q=${encodeURIComponent(query)}`),
  fetchKnowledgeBriefing: (topicId: string) =>
    fetchInkdeskJson<KnowledgeBriefing>(`/knowledge/topics/${encodeURIComponent(topicId)}/briefing`),
  fetchKnowledgeDocument: (topicId: string) =>
    fetchInkdeskJson<{ documentId: string; title: string; source: string; path: string; content: string; contentHash: string }>(
      `/knowledge/topics/${encodeURIComponent(topicId)}/document`
    ),
  fetchKnowledgeSignals: (filters?: { status?: string; type?: string; topicId?: string }) => {
    const params = new URLSearchParams();
    if (filters?.status) params.set("status", filters.status);
    if (filters?.type) params.set("type", filters.type);
    if (filters?.topicId) params.set("topicId", filters.topicId);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return fetchInkdeskJson<{ signals: KnowledgeSignalRecord[] }>(`/knowledge/signals${suffix}`);
  },
  reviewKnowledgeSignal: (
    signalId: string,
    payload: { action: "acknowledge" | "resolve" | "dismiss" | "reopen"; ifVersion: number; note?: string }
  ) => postInkdeskJson<KnowledgeSignalRecord>(`/knowledge/signals/${encodeURIComponent(signalId)}/actions`, payload),
  fetchKnowledgeHealthSummary: () =>
    fetchInkdeskJson<{ total: number; active: number; byType: Record<string, number> }>("/knowledge/health/summary"),
  fetchTasks: (filters?: { status?: TaskStatus; originType?: TaskOriginType; contextStatus?: TaskContextStatus }) => {
    const params = new URLSearchParams();
    if (filters?.status) params.set("status", filters.status);
    if (filters?.originType) params.set("originType", filters.originType);
    if (filters?.contextStatus) params.set("contextStatus", filters.contextStatus);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return fetchInkdeskJson<{ tasks: DevelopmentTask[] }>(`/tasks${suffix}`);
  },
  createTask: (payload: {
    title: string;
    goal: string;
    originType: TaskOriginType;
    originRef?: string;
    priority?: string;
    risk?: string;
    knowledgeTopicIds?: string[];
  }) => postInkdeskJson<DevelopmentTask>("/tasks", payload),
  fetchTask: (taskId: string) =>
    fetchInkdeskJson<DevelopmentTask>(`/tasks/${encodeURIComponent(taskId)}`),
  assembleTaskContext: (taskId: string, force = false) =>
    postInkdeskJson<DevelopmentTask>(`/tasks/${encodeURIComponent(taskId)}/context${force ? "?force=true" : ""}`, {}),
  transitionTask: (taskId: string, status: TaskStatus, ifVersion: number) =>
    postInkdeskJson<DevelopmentTask>(`/tasks/${encodeURIComponent(taskId)}/transition`, { status, ifVersion }),
  subscribeToGraphEvents,
  subscribeToRunEvents,
  subscribeToKnowledgeEvents,
  subscribeToTaskEvents
};
