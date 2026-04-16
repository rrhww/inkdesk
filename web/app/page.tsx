import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { PublicHomeView } from "@/components/public-home-view";
import { OWNER_SESSION_COOKIE, resolveRootDestination } from "@/lib/owner-session";

export const metadata: Metadata = {
  title: "个人研究、长期项目与公开写作 | Inkdesk",
  description: "一个围绕长期项目、个人知识系统与 Agent 协同展开的安静研究入口。",
  alternates: {
    canonical: "/"
  },
  openGraph: {
    title: "个人研究、长期项目与公开写作 | Inkdesk",
    description: "公开整理长期写作、研究主题与方法背景，不暴露主系统入口。",
    type: "website"
  }
};

export default async function HomePage() {
  const cookieStore = await cookies();
  const destination = resolveRootDestination(cookieStore.get(OWNER_SESSION_COOKIE)?.value);

  if (destination === "app") {
    redirect("/app");
  }

  return <PublicHomeView />;
}
