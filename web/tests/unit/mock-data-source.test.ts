import { describe, expect, it } from "vitest";

import { mockInkdeskDataSource } from "@/lib/mock-data-source";

describe("mockInkdeskDataSource", () => {
  it("returns public home stats and a featured article", () => {
    const data = mockInkdeskDataSource.getPublicHomeData();

    expect(data.featuredArticle?.slug).toBe("super-personal-workbench-reframe");
    expect(data.publicStats[0]?.label).toBe("公开文章");
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
