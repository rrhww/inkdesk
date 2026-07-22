import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "Inkdesk 知识图谱",
  description: "基于本地 Markdown 的研发知识图谱工作台。",
  alternates: {
    canonical: "/"
  },
  openGraph: {
    title: "Inkdesk 知识图谱",
    description: "基于本地 Markdown 的研发知识图谱工作台。",
    type: "website"
  }
};

export default function HomePage() {
  redirect("/app/wiki");
}
