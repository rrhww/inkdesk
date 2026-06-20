import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "Inkdesk 研发控制台",
  description: "单人私有、Dev Run-first 的 AI 研发自动化控制台。",
  alternates: {
    canonical: "/"
  },
  openGraph: {
    title: "Inkdesk 研发控制台",
    description: "单人私有、Dev Run-first 的 AI 研发自动化控制台。",
    type: "website"
  }
};

export default async function HomePage() {
  redirect("/app");
}
