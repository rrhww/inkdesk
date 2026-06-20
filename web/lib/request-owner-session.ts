import { OWNER_SESSION_VALUE } from "@/lib/owner-session";

export async function getRequestOwnerSession() {
  return OWNER_SESSION_VALUE;
}
