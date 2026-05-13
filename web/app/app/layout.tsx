import type { ReactNode } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AppChrome } from "@/components/app-chrome";
import { logoutOwner } from "@/lib/owner-auth";
import { getResearchDashboard } from "@/lib/research";
import { InkvaultApiError } from "@/lib/server-api";
import { OWNER_SESSION_COOKIE, hasOwnerSession } from "@/lib/owner-session";
import type { ResearchDashboard } from "@/lib/types";

async function logoutAction() {
  "use server";

  const cookieStore = await cookies();
  await logoutOwner(cookieStore.get(OWNER_SESSION_COOKIE)?.value);
  cookieStore.delete(OWNER_SESSION_COOKIE);
  redirect("/login");
}

export default async function AppLayout({ children }: { children: ReactNode }) {
  const cookieStore = await cookies();
  const ownerSession = cookieStore.get(OWNER_SESSION_COOKIE)?.value;

  if (!hasOwnerSession(ownerSession)) {
    redirect("/login");
  }

  let snapshot: ResearchDashboard;

  try {
    snapshot = await getResearchDashboard(ownerSession);
  } catch (error) {
    if (error instanceof InkvaultApiError && error.status === 401) {
      cookieStore.delete(OWNER_SESSION_COOKIE);
      redirect("/login");
    }

    throw error;
  }

  return (
    <AppChrome logoutAction={logoutAction} snapshot={snapshot}>
      {children}
    </AppChrome>
  );
}
