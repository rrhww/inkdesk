import { KnowledgeHub } from "@/components/workbench/knowledge-hub";
import { getKnowledgeHubData } from "@/lib/knowledge";
import { getRequestOwnerSession } from "@/lib/request-owner-session";

type LibraryPageProps = {
  searchParams?: Promise<{
    filter?: string;
    tag?: string;
  }>;
};

export default async function LibraryPage({ searchParams }: LibraryPageProps) {
  const resolved = searchParams ? await searchParams : undefined;
  const activeFilter = resolved?.filter ?? "all";
  const activeTag = resolved?.tag;
  const ownerSession = await getRequestOwnerSession();

  return <KnowledgeHub activeFilter={activeFilter} activeTag={activeTag} data={await getKnowledgeHubData(activeFilter, ownerSession)} />;
}
