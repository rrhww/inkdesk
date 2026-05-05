import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { PublicHomeView } from "@/components/public-home-view";
import { OWNER_SESSION_COOKIE, resolveRootDestination } from "@/lib/owner-session";

export const metadata: Metadata = {
  title: "项目、开发学习笔记与方法思考 | Inkdesk",
  description: "把项目、分类学习笔记与方法思考组织成一张可持续浏览的公开知识地图。",
  alternates: {
    canonical: "/"
  },
  openGraph: {
    title: "项目、开发学习笔记与方法思考 | Inkdesk",
    description: "公开展示项目、分类笔记和方法思考，不暴露主系统入口。",
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
