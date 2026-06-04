import { afterEach, describe, expect, it, vi } from "vitest";

import { readAskHistory, writeAskHistory, mergeAskHistoryEntry, ASK_HISTORY_STORAGE_KEY } from "@/lib/ask-history";
import { researchDashboardFixture } from "@/lib/mock/research-fixtures";
import { PRIMARY_SECTIONS, buildStarterHistory, getAppRouteChrome, getPrimarySectionForPathname } from "@/lib/app-shell";

describe("app shell primitives", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  it("exposes Chinese primary sections in product order", () => {
    expect(PRIMARY_SECTIONS.map((item) => item.label)).toEqual(["问答", "资料", "审阅", "知识库"]);
    expect(PRIMARY_SECTIONS.map((item) => item.href)).toEqual(["/app", "/app/raw", "/app/ingest", "/app/wiki"]);
    expect(PRIMARY_SECTIONS.flatMap((item) => item.matchers)).not.toEqual(
      expect.arrayContaining(["/app/inbox", "/app/sources", "/app/review", "/app/topics"])
    );
  });

  it("matches /app and /app/ask as the same ask-first primary section", () => {
    expect(getPrimarySectionForPathname("/app")?.label).toBe("问答");
    expect(getPrimarySectionForPathname("/app/ask")?.label).toBe("问答");
    expect(getPrimarySectionForPathname("/app/raw")?.label).toBe("资料");
    expect(getPrimarySectionForPathname("/app/wiki/topic-001")?.label).toBe("知识库");
    expect(getPrimarySectionForPathname("/app/topics")).toBeUndefined();
  });

  it("derives route-specific header chrome from the current snapshot", () => {
    expect(getAppRouteChrome("/app", researchDashboardFixture)).toMatchObject({
      title: "问答",
      subtitle: expect.stringContaining("Ask 现在是主入口"),
      contextItems: expect.arrayContaining([{ label: "当前模式", value: "Ask-first" }])
    });
    expect(getAppRouteChrome("/app/raw", researchDashboardFixture)).toMatchObject({
      title: "资料",
      contextItems: expect.arrayContaining([{ label: "等待编译", value: "3 条" }])
    });
    expect(getAppRouteChrome("/app/ingest", researchDashboardFixture)).toMatchObject({
      title: "审阅",
      contextItems: expect.arrayContaining([{ label: "待审阅", value: "3 条" }])
    });
    expect(getAppRouteChrome("/app/wiki/topic-001", researchDashboardFixture)).toMatchObject({
      title: "知识库",
      contextItems: expect.arrayContaining([
        { label: "开放问题", value: "3 个" },
        { label: "高风险 claim", value: "2 条" }
      ])
    });
    expect(getAppRouteChrome("/app/ask", researchDashboardFixture)).toMatchObject({
      title: "问答",
      contextItems: expect.arrayContaining([{ label: "可写回", value: "1 条" }])
    });
  });

  it("uses global claim risk counts for wiki chrome instead of only the focus topic", () => {
    const snapshot = {
      ...researchDashboardFixture,
      health: {
        ...researchDashboardFixture.health,
        unsupportedClaimCount: 2,
        staleClaimCount: 1,
        conflictingClaimCount: 4
      },
      focusTopic: {
        ...researchDashboardFixture.focusTopic!,
        unsupportedClaimCount: 0,
        staleClaimCount: 0
      }
    };

    expect(getAppRouteChrome("/app/wiki", snapshot)).toMatchObject({
      contextItems: expect.arrayContaining([
        { label: "高风险 claim", value: "3 条" },
        { label: "冲突 claim", value: "4 条" }
      ])
    });
  });

  it("includes topicId in starter history href when focus topic is provided", () => {
    const starter = buildStarterHistory({
      suggestedQuestions: ["raw 和 wiki 的边界是什么？"],
      focusTopicId: "topic-001",
      focusTopicTitle: "Inkdesk repositioning"
    });

    expect(starter[0]?.href).toBe("/app?q=raw%20%E5%92%8C%20wiki%20%E7%9A%84%E8%BE%B9%E7%95%8C%E6%98%AF%E4%BB%80%E4%B9%88%EF%BC%9F&topicId=topic-001");
  });

  it("merges current ask turns ahead of starter history and removes duplicates", () => {
    const starter = buildStarterHistory({
      suggestedQuestions: ["raw 和 wiki 的边界是什么？"],
      focusTopicTitle: "Inkdesk repositioning"
    });

    const merged = mergeAskHistoryEntry(starter, {
      id: "ask-topic-001",
      title: "这个主题当前最稳定的理解是什么？",
      href: "/app/ask?q=%E8%BF%99%E4%B8%AA%E4%B8%BB%E9%A2%98%E5%BD%93%E5%89%8D%E6%9C%80%E7%A8%B3%E5%AE%9A%E7%9A%84%E7%90%86%E8%A7%A3%E6%98%AF%E4%BB%80%E4%B9%88%EF%BC%9F&topicId=topic-001",
      topicTitle: "Inkdesk repositioning",
      preview: "当前最稳定的理解是 wiki 是新的核心对象。",
      updatedAt: "2026-05-03T03:00:00Z"
    });

    expect(merged[0]?.id).toBe("ask-topic-001");
    expect(merged[0]?.topicTitle).toBe("Inkdesk repositioning");
    expect(merged).toHaveLength(2);
  });

  it("dedupes by href and caps ask history at 12 entries", () => {
    const current = Array.from({ length: 12 }, (_, index) => ({
      id: `ask-${index + 1}`,
      title: `Question ${index + 1}`,
      href: index === 5 ? "/app/ask?q=shared-question" : `/app/ask?q=question-${index + 1}`,
      topicTitle: "Inkdesk repositioning",
      preview: `Preview ${index + 1}`,
      updatedAt: `2026-05-03T0${index}:00:00Z`
    }));

    const merged = mergeAskHistoryEntry(current, {
      id: "ask-latest",
      title: "Shared question",
      href: "/app/ask?q=shared-question",
      topicTitle: "Inkdesk repositioning",
      preview: "Latest preview",
      updatedAt: "2026-05-03T13:00:00Z"
    });

    expect(merged[0]?.id).toBe("ask-latest");
    expect(merged.filter((item) => item.href === "/app/ask?q=shared-question")).toHaveLength(1);
    expect(merged).toHaveLength(12);
  });

  it("returns an empty history when stored JSON has the wrong shape", () => {
    window.localStorage.setItem(ASK_HISTORY_STORAGE_KEY, JSON.stringify({ id: "ask-001" }));

    expect(readAskHistory()).toEqual([]);
  });

  it("treats storage access failures as empty reads and safe writes", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("storage blocked");
    });

    expect(readAskHistory()).toEqual([]);

    const setItemSpy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("storage blocked");
    });

    expect(() =>
      writeAskHistory([
        {
          id: "ask-001",
          title: "Question",
          href: "/app/ask?q=Question",
          topicTitle: "Inkdesk repositioning",
          preview: "Preview",
          updatedAt: "2026-05-03T03:00:00Z"
        }
      ])
    ).not.toThrow();
    expect(setItemSpy).toHaveBeenCalledOnce();
  });
});
