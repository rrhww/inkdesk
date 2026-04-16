export const OWNER_SESSION_COOKIE = "inkdesk_owner_session";
export const OWNER_SESSION_VALUE = "owner";

export function hasOwnerSession(value?: string) {
  return Boolean(value?.trim());
}

export function resolveRootDestination(value?: string) {
  return hasOwnerSession(value) ? "app" : "public";
}

export function resolveProtectedAppRedirect(pathname: string, value?: string) {
  if (!pathname.startsWith("/app")) {
    return null;
  }

  return hasOwnerSession(value) ? null : "/login";
}
