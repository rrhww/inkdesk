import type { ReactNode } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AppHeader } from "@/components/app-header";
import { AppSidebar } from "@/components/app-sidebar";
import { getWorkbenchSnapshot } from "@/lib/home";
import { logoutOwner } from "@/lib/owner-auth";
import { InkdeskApiError } from "@/lib/server-api";
import { OWNER_SESSION_COOKIE, hasOwnerSession } from "@/lib/owner-session";
import type { WorkbenchSnapshot } from "@/lib/types";

async function logoutAction() {
  "use server";

  const cookieStore = await cookies();
  await logoutOwner(cookieStore.get(OWNER_SESSION_COOKIE)?.value);
  cookieStore.delete(OWNER_SESSION_COOKIE);
  redirect("/");
}

export default async function AppLayout({ children }: { children: ReactNode }) {
  const cookieStore = await cookies();
  const ownerSession = cookieStore.get(OWNER_SESSION_COOKIE)?.value;

  if (!hasOwnerSession(ownerSession)) {
    redirect("/login");
  }

  let snapshot: WorkbenchSnapshot;

  try {
    snapshot = await getWorkbenchSnapshot(ownerSession);
  } catch (error) {
    if (error instanceof InkdeskApiError && error.status === 401) {
      cookieStore.delete(OWNER_SESSION_COOKIE);
      redirect("/login");
    }

    throw error;
  }

  return (
    <div className="min-h-screen">
      <AppSidebar />
      <div className="lg:ml-60">
        <AppHeader
          title="Inkdesk 主系统"
          subtitle="Agent、笔记与任务计划协同运行的超级个人工作台"
          contextItems={[
            { label: "当前模式", value: "主人主系统" },
            { label: "进行中计划", value: `${snapshot.summary.activePlans} 项` },
            { label: "已公开内容", value: `${snapshot.summary.publishedNotes} 篇` }
          ]}
          action={
            <form action={logoutAction}>
              <button className="rounded-sm bg-ink-low px-4 py-3 font-headline text-sm font-semibold text-ink-text">退出主系统</button>
            </form>
          }
        />
        {children}
      </div>
    </div>
  );
}
