import { cookies } from "next/headers";

import { OWNER_SESSION_COOKIE } from "@/lib/owner-session";

export async function getRequestOwnerSession() {
  try {
    const cookieStore = await cookies();
    return cookieStore.get(OWNER_SESSION_COOKIE)?.value;
  } catch {
    return undefined;
  }
}
