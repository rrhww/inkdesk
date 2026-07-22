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

export const ServerAPI = {
  fetchGraphTopology: (scope: GraphScope = "all") =>
    fetchInkdeskJson<GraphSnapshot>(scope === "all" ? "/graph" : `/graph?source=${scope}`),
  fetchNodeDocument: (nodeId: string) =>
    fetchInkdeskJson<GraphNodeDocument>(`/graph/document?nodeId=${encodeURIComponent(nodeId)}`),
  subscribeToGraphEvents
};
