import { OWNER_SESSION_COOKIE } from "@/lib/owner-session";

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
  ownerSession?: string;
  body?: unknown | FormData;
};

function buildHeaders(options?: RequestInkdeskOptions) {
  const headers: Record<string, string> = {};

  if (options?.ownerSession) {
    headers.Cookie = `${OWNER_SESSION_COOKIE}=${options?.ownerSession}`;
  }

  if (options?.body !== undefined && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  return Object.keys(headers).length > 0 ? headers : undefined;
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

export async function fetchInkdeskJson<T>(path: string, options?: { ownerSession?: string }) {
  const response = await requestInkdesk(path, {
    method: "GET",
    ownerSession: options?.ownerSession
  });

  return (await response.json()) as T;
}

export async function postInkdeskJson<T>(path: string, body: unknown, options?: { ownerSession?: string }) {
  const response = await requestInkdesk(path, {
    method: "POST",
    ownerSession: options?.ownerSession,
    body
  });

  return (await response.json()) as T;
}

export async function patchInkdeskJson<T>(path: string, body: unknown, options?: { ownerSession?: string }) {
  const response = await requestInkdesk(path, {
    method: "PATCH",
    ownerSession: options?.ownerSession,
    body
  });

  return (await response.json()) as T;
}

export async function postInkdesk(path: string, options?: { ownerSession?: string; body?: unknown }) {
  await requestInkdesk(path, {
    method: "POST",
    ownerSession: options?.ownerSession,
    body: options?.body
  });
}

export async function postInkdeskFormData<T>(path: string, body: FormData, options?: { ownerSession?: string }) {
  const response = await requestInkdesk(path, {
    method: "POST",
    ownerSession: options?.ownerSession,
    body
  });

  return (await response.json()) as T;
}
