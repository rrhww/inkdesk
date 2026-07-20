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

export const ServerAPI = {
  fetchGraphTopology: () => fetchInkdeskJson<GraphSnapshot>("/graph?source=vault"),
  fetchNodeDocument: (nodeId: string) =>
    fetchInkdeskJson<GraphNodeDocument>(`/graph/document?nodeId=${encodeURIComponent(nodeId)}`)
};
