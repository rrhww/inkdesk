import { describe, expect, it } from "vitest";

import { mockInkdeskDataSource } from "@/lib/mock-data-source";

describe("mockInkdeskDataSource", () => {
  it("returns the curated public home structure", () => {
    const data = mockInkdeskDataSource.getPublicHomeData();

    expect(data.knowledgeBuckets).toHaveLength(4);
    expect(data.featuredProjects[0]?.slug).toBe("inkdesk-main-system");
    expect(data.recentUpdates[0]?.type).toBeDefined();
  });

  it("keeps search case-insensitive and sortable by hit strength", () => {
    const results = mockInkdeskDataSource.searchKnowledge({
      q: "agent",
      visibility: "all"
    });

    expect(results[0]?.note.id).toBe("note-002");
    expect(results[0]?.hitLabels).toContain("标题");
  });
});
