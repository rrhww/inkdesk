import { OWNER_SESSION_VALUE } from "@/lib/owner-session";
import { hasApiBaseUrl, InkvaultApiError, postInkvault, postInkvaultJson } from "@/lib/server-api";

const OWNER_EMAIL = "owner@inkvault.local";
const OWNER_PASSWORD = "inkvault-owner";

type LoginResponse = {
  sessionToken: string;
};

function loginWithLocalOwner(email: string, password: string): LoginResponse | null {
  if (email === OWNER_EMAIL && password === OWNER_PASSWORD) {
    return {
      sessionToken: OWNER_SESSION_VALUE
    };
  }

  return null;
}

export async function loginOwner(email: string, password: string): Promise<LoginResponse | null> {
  if (!hasApiBaseUrl()) {
    return loginWithLocalOwner(email, password);
  }

  try {
    return await postInkvaultJson<LoginResponse>("/auth/login", {
      email,
      password
    });
  } catch (error) {
    if (error instanceof InkvaultApiError) {
      throw error;
    }

    return loginWithLocalOwner(email, password);
  }
}

export async function logoutOwner(ownerSession?: string) {
  if (!hasApiBaseUrl() || !ownerSession) {
    return;
  }

  try {
    await postInkvault("/auth/logout", { ownerSession });
  } catch (error) {
    if (error instanceof InkvaultApiError) {
      throw error;
    }
  }
}
