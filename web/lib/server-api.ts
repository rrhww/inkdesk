import { OWNER_SESSION_COOKIE, hasOwnerSession } from "@/lib/owner-session";

export class InkvaultApiError extends Error {
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
  return normalizeApiBaseUrl(process.env.INKVAULT_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "");
}

export function hasApiBaseUrl() {
  return Boolean(resolveApiBaseUrl());
}

type RequestInkvaultOptions = {
  method?: "GET" | "POST" | "PATCH";
  ownerSession?: string;
  body?: unknown | FormData;
};

function buildHeaders(options?: RequestInkvaultOptions) {
  const headers: Record<string, string> = {};

  if (hasOwnerSession(options?.ownerSession)) {
    headers.Cookie = `${OWNER_SESSION_COOKIE}=${options?.ownerSession}`;
  }

  if (options?.body !== undefined && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  return Object.keys(headers).length > 0 ? headers : undefined;
}

async function requestInkvault(path: string, options?: RequestInkvaultOptions) {
  const apiBaseUrl = resolveApiBaseUrl();

  if (!apiBaseUrl) {
    throw new InkvaultApiError(500, "Inkvault API base URL is not configured");
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
    throw new InkvaultApiError(response.status, `Inkvault API request failed for ${path}`);
  }

  return response;
}

export async function fetchInkvaultJson<T>(path: string, options?: { ownerSession?: string }) {
  const response = await requestInkvault(path, {
    method: "GET",
    ownerSession: options?.ownerSession
  });

  return (await response.json()) as T;
}

export async function postInkvaultJson<T>(path: string, body: unknown, options?: { ownerSession?: string }) {
  const response = await requestInkvault(path, {
    method: "POST",
    ownerSession: options?.ownerSession,
    body
  });

  return (await response.json()) as T;
}

export async function patchInkvaultJson<T>(path: string, body: unknown, options?: { ownerSession?: string }) {
  const response = await requestInkvault(path, {
    method: "PATCH",
    ownerSession: options?.ownerSession,
    body
  });

  return (await response.json()) as T;
}

export async function postInkvault(path: string, options?: { ownerSession?: string; body?: unknown }) {
  await requestInkvault(path, {
    method: "POST",
    ownerSession: options?.ownerSession,
    body: options?.body
  });
}

export async function postInkvaultFormData<T>(path: string, body: FormData, options?: { ownerSession?: string }) {
  const response = await requestInkvault(path, {
    method: "POST",
    ownerSession: options?.ownerSession,
    body
  });

  return (await response.json()) as T;
}
