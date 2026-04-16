import { SearchRecall } from "@/components/workbench/search-recall";
import { getRequestOwnerSession } from "@/lib/request-owner-session";
import { getSearchSuggestions, searchKnowledge } from "@/lib/search";

type SearchPageProps = {
  searchParams?: Promise<{
    q?: string;
    visibility?: string;
    tag?: string;
    folder?: string;
  }>;
};

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const resolved = searchParams ? await searchParams : undefined;
  const query = resolved?.q?.trim() ?? "";
  const visibility = resolved?.visibility ?? "all";
  const tag = resolved?.tag?.trim() || undefined;
  const folder = resolved?.folder?.trim() || undefined;
  const ownerSession = await getRequestOwnerSession();
  const suggestions = await getSearchSuggestions(ownerSession);
  const results = query
    ? await searchKnowledge(
        {
        q: query,
        visibility: visibility === "all" ? "all" : visibility === "public" ? "public" : "private",
        tag,
        folder
        },
        ownerSession
      )
    : [];

  return (
    <SearchRecall
      folder={folder}
      query={query}
      recentKnowledge={suggestions.recentKnowledge}
      recommendedTerms={suggestions.recommendedTerms}
      results={results}
      tags={suggestions.tags}
      tag={tag}
      visibility={visibility}
      folders={suggestions.folders}
    />
  );
}
