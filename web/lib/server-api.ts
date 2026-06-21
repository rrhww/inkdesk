export class InkdeskApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
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
    throw new InkdeskApiError(response.status, `Inkdesk API request failed for ${path}`);
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
