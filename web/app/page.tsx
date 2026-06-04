import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { getRequestOwnerSession } from "@/lib/request-owner-session";
import { resolveRootDestination } from "@/lib/owner-session";

export const metadata: Metadata = {
  title: "Private LLM Wiki | Inkdesk",
  description: "单人私有、raw / ingest / wiki 的 Vault-first LLM Wiki。",
  alternates: {
    canonical: "/"
  },
  openGraph: {
    title: "Private LLM Wiki | Inkdesk",
    description: "单人私有、raw / ingest / wiki 的 Vault-first LLM Wiki。",
    type: "website"
  }
};

export default async function HomePage() {
  const destination = resolveRootDestination(await getRequestOwnerSession());
  redirect(destination === "app" ? "/app" : "/login");
}
