import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { OWNER_SESSION_COOKIE, hasOwnerSession } from "@/lib/owner-session";

type RequestOwnerSessionState = {
  hasRequestContext: boolean;
  ownerSession?: string;
};

export async function getRequestOwnerSessionState(): Promise<RequestOwnerSessionState> {
  try {
    const cookieStore = await cookies();
    return {
      hasRequestContext: true,
      ownerSession: cookieStore.get(OWNER_SESSION_COOKIE)?.value
    };
  } catch {
    return {
      hasRequestContext: false,
      ownerSession: undefined
    };
  }
}

export async function getRequestOwnerSession() {
  const state = await getRequestOwnerSessionState();
  return state.ownerSession;
}

export async function requireRequestOwnerSession() {
  const state = await getRequestOwnerSessionState();

  if (state.hasRequestContext && !hasOwnerSession(state.ownerSession)) {
    redirect("/login");
  }

  return state.ownerSession;
}
