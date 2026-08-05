export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export interface GraphData {
  nodes: GraphSnapshotNode[];
  edges: GraphSnapshotEdge[];
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

export type GraphSnapshot = GraphData & {
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

export type GraphStreamStatus = 'connecting' | 'connected' | 'offline';
export type GraphScope = 'all' | 'vault' | 'repo';

export type GraphStreamEvent =
  | { type: 'graph.snapshot'; snapshot: GraphSnapshot }
  | { type: 'graph.updated'; reason?: string; snapshot: GraphSnapshot }
  | { type: 'node.active'; nodeId: string }
  | { type: 'node.idle'; nodeId: string };

export type KnowledgeHealthSignal = {
  id?: string;
  type: 'missing_link' | 'stale' | 'unsupported' | 'conflicting' | 'open_question';
  severity: 'info' | 'warning' | 'critical';
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

export class InkdeskApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string
  ) {
    super(message);
  }
}

function normalizeApiBaseUrl(baseUrl: string) {
  const normalized = baseUrl.trim().replace(/\/+$/, '');
  if (!normalized) return null;
  return normalized.endsWith('/api') ? normalized : `${normalized}/api`;
}

export function resolveApiBaseUrl() {
  if (typeof window !== 'undefined') return '/api';
  return normalizeApiBaseUrl(
    process.env.INKDESK_API_BASE_URL ??
      process.env.NEXT_PUBLIC_API_BASE_URL ??
      process.env.NEXT_PUBLIC_API_URL ??
      ''
  );
}

export function hasApiBaseUrl() {
  return Boolean(resolveApiBaseUrl());
}

async function requestInkdesk(path: string) {
  const apiBaseUrl = resolveApiBaseUrl();
  if (!apiBaseUrl) {
    throw new InkdeskApiError(500, 'Inkdesk API base URL is not configured');
  }
  const response = await fetch(`${apiBaseUrl}${path}`, { cache: 'no-store' });
  if (!response.ok) {
    throw new InkdeskApiError(response.status, `Inkdesk API request failed for ${path}`);
  }
  return response;
}

export async function fetchInkdeskJson<T>(path: string) {
  const response = await requestInkdesk(path);
  return (await response.json()) as T;
}

export const ServerAPI = {
  fetchKnowledgeTopics: async (): Promise<KnowledgeTopicList> => {
    const response = await fetch(`${API_BASE}/api/knowledge/topics`, { cache: 'no-store' });
    if (!response.ok) throw new Error('Failed to fetch knowledge topics');
    return await response.json();
  },

  searchKnowledge: async (query: string): Promise<KnowledgeSearchResult> => {
    const response = await fetch(`${API_BASE}/api/knowledge/search?q=${encodeURIComponent(query)}`, { cache: 'no-store' });
    if (!response.ok) throw new Error('Failed to search knowledge');
    return await response.json();
  },

  fetchKnowledgeBriefing: async (topicId: string): Promise<KnowledgeBriefing> => {
    const response = await fetch(`${API_BASE}/api/knowledge/topics/${encodeURIComponent(topicId)}/briefing`, { cache: 'no-store' });
    if (!response.ok) throw new Error('Knowledge topic not found');
    return await response.json();
  },

  fetchKnowledgeDocument: async (topicId: string) => {
    const response = await fetch(`${API_BASE}/api/knowledge/topics/${encodeURIComponent(topicId)}/document`, { cache: "no-store" });
    if (!response.ok) throw new Error("Knowledge document not found");
    return await response.json() as { documentId: string; title: string; source: string; path: string; content: string; contentHash: string };
  },

  fetchKnowledgeSignals: async (filters?: { status?: string; type?: string; topicId?: string }) => {
    const params = new URLSearchParams();
    if (filters?.status) params.set("status", filters.status);
    if (filters?.type) params.set("type", filters.type);
    if (filters?.topicId) params.set("topicId", filters.topicId);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    const response = await fetch(`${API_BASE}/api/knowledge/signals${suffix}`, { cache: "no-store" });
    if (!response.ok) throw new Error("Failed to fetch knowledge signals");
    return await response.json() as { signals: KnowledgeSignalRecord[] };
  },

  reviewKnowledgeSignal: async (signalId: string, payload: { action: "acknowledge" | "resolve" | "dismiss" | "reopen"; ifVersion: number; note?: string }) => {
    const response = await fetch(`${API_BASE}/api/knowledge/signals/${encodeURIComponent(signalId)}/actions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!response.ok) throw new Error("Failed to update knowledge signal");
    return await response.json() as KnowledgeSignalRecord;
  },

  subscribeToKnowledgeEvents: (onUpdate: (event: { version?: string }) => void) => {
    const source = new EventSource(`${API_BASE}/api/knowledge/stream`);
    const handle = (event: MessageEvent) => { try { onUpdate(JSON.parse(event.data)); } catch { /* ignore malformed invalidation */ } };
    source.addEventListener("knowledge.updated", handle);
    source.onmessage = handle;
    return () => source.close();
  },

  fetchKnowledgeHealthSummary: async () => fetchInkdeskJson<{ total: number; active: number; byType: Record<string, number> }>("/knowledge/health/summary"),

  fetchTasks: async (filters?: { status?: TaskStatus; originType?: TaskOriginType; contextStatus?: TaskContextStatus }) => {
    const params = new URLSearchParams();
    if (filters?.status) params.set("status", filters.status);
    if (filters?.originType) params.set("originType", filters.originType);
    if (filters?.contextStatus) params.set("contextStatus", filters.contextStatus);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    const response = await fetch(`${API_BASE}/api/tasks${suffix}`, { cache: "no-store" });
    if (!response.ok) throw new Error("Failed to fetch tasks");
    return (await response.json()) as { tasks: DevelopmentTask[] };
  },

  createTask: async (payload: {
    title: string;
    goal: string;
    originType: TaskOriginType;
    originRef?: string;
    priority?: string;
    risk?: string;
    knowledgeTopicIds?: string[];
  }) => {
    const response = await fetch(`${API_BASE}/api/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error("Failed to create task");
    return (await response.json()) as DevelopmentTask;
  },

  fetchTask: async (taskId: string) => {
    const response = await fetch(`${API_BASE}/api/tasks/${encodeURIComponent(taskId)}`, { cache: "no-store" });
    if (!response.ok) throw new Error("Task not found");
    return await response.json() as DevelopmentTask;
  },

  assembleTaskContext: async (taskId: string, force = false) => {
    const response = await fetch(`${API_BASE}/api/tasks/${encodeURIComponent(taskId)}/context${force ? "?force=true" : ""}`, { method: "POST" });
    if (!response.ok) throw new Error("Failed to assemble task context");
    return (await response.json()) as DevelopmentTask;
  },

  transitionTask: async (taskId: string, status: TaskStatus, ifVersion: number) => {
    const response = await fetch(`${API_BASE}/api/tasks/${encodeURIComponent(taskId)}/transition`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status, ifVersion }) });
    if (!response.ok) throw new Error("Failed to transition task");
    return await response.json() as DevelopmentTask;
  },

  subscribeToTaskEvents: (onUpdate: (event: { taskId: string | null; version: number | null }) => void, onStatus?: (status: "connecting" | "connected" | "offline") => void) => {
    onStatus?.("connecting");
    const source = new EventSource(`${API_BASE}/api/tasks/stream`);
    source.onopen = () => onStatus?.("connected");
    const handle = (event: MessageEvent) => { try { onUpdate(JSON.parse(event.data)); } catch { /* ignore malformed invalidation */ } };
    source.addEventListener("tasks.updated", handle);
    source.onmessage = handle;
    source.onerror = () => { source.close(); onStatus?.("offline"); };
    return () => source.close();
  },

  // 1. 拉取由 graph_index.py 生成的全量/局部拓扑数据
  fetchGraphTopology: async (scope: GraphScope = 'all'): Promise<GraphSnapshot> => {
    const suffix = scope === 'all' ? '' : `?source=${scope}`;
    const response = await fetch(`${API_BASE}/api/graph${suffix}`);
    if (!response.ok) throw new Error('Failed to fetch topology');
    return await response.json();
  },

  // 2. 拉取 Markdown 源码用于侧滑阅读器渲染
  fetchNodeContent: async (nodeId: string): Promise<string> => {
    const response = await fetch(`${API_BASE}/api/doc/${encodeURIComponent(nodeId)}`);
    if (!response.ok) throw new Error('Document not found');
    const data = await response.json();
    return data.content;
  },

  fetchNodeDocument: async (nodeId: string): Promise<GraphNodeDocument> => {
    const response = await fetch(`${API_BASE}/api/doc/${encodeURIComponent(nodeId)}`);
    if (!response.ok) throw new Error('Document not found');
    return await response.json();
  },

  // 3. 监听 engine.py 的运行时流 (SSE)
  subscribeToVaultEvents: (
    onMessage: (event: GraphStreamEvent) => void,
    onStatusChange: (status: GraphStreamStatus) => void
  ) => {
    onStatusChange('connecting');
    const eventSource = new EventSource(`${API_BASE}/api/events`);

    eventSource.onopen = () => onStatusChange('connected');
    eventSource.onmessage = (event) => onMessage(JSON.parse(event.data));
    eventSource.onerror = () => {
      eventSource.close();
      onStatusChange('offline');
    };
    return () => eventSource.close();
  },

  subscribeToGraphEvents: (
    onMessage: (event: GraphStreamEvent) => void,
    onStatusChange: (status: GraphStreamStatus) => void,
    scope: GraphScope = 'all'
  ) => {
    void scope;
    return ServerAPI.subscribeToVaultEvents(onMessage, onStatusChange);
  }
};
