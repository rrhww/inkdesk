import type { ReactNode } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AppHeader } from "@/components/app-header";
import { AppSidebar } from "@/components/app-sidebar";
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
    <div className="min-h-screen">
      <AppSidebar snapshot={snapshot} />
      <div className="lg:ml-72">
        <AppHeader
          title="问答"
          subtitle="先沿着最近对话继续，再决定回到资料、审阅还是知识库。"
          contextItems={[
            { label: "当前模式", value: "仅基于知识库" },
            { label: "待审阅", value: `${snapshot.summary.pendingReviews} 条` },
            { label: "知识页", value: `${snapshot.summary.activeTopics} 个` }
          ]}
          action={
            <form action={logoutAction}>
              <button className="rounded-sm bg-ink-low px-4 py-3 font-headline text-sm font-semibold text-ink-text">退出</button>
            </form>
          }
        />
        {children}
      </div>
    </div>
  );
}
