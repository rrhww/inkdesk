import { afterEach, describe, expect, it, vi } from "vitest";

import { readAskHistory, writeAskHistory, mergeAskHistoryEntry, ASK_HISTORY_STORAGE_KEY } from "@/lib/ask-history";
import { PRIMARY_SECTIONS, buildStarterHistory } from "@/lib/app-shell";

describe("app shell primitives", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  it("exposes Chinese primary sections in product order", () => {
    expect(PRIMARY_SECTIONS.map((item) => item.label)).toEqual(["问答", "资料", "审阅", "知识库"]);
    expect(PRIMARY_SECTIONS.map((item) => item.href)).toEqual(["/app", "/app/raw", "/app/ingest", "/app/wiki"]);
  });

  it("includes topicId in starter history href when focus topic is provided", () => {
    const starter = buildStarterHistory({
      suggestedQuestions: ["raw 和 wiki 的边界是什么？"],
      focusTopicId: "topic-001",
      focusTopicTitle: "Inkvault repositioning"
    });

    expect(starter[0]?.href).toBe("/app?q=raw%20%E5%92%8C%20wiki%20%E7%9A%84%E8%BE%B9%E7%95%8C%E6%98%AF%E4%BB%80%E4%B9%88%EF%BC%9F&topicId=topic-001");
  });

  it("merges current ask turns ahead of starter history and removes duplicates", () => {
    const starter = buildStarterHistory({
      suggestedQuestions: ["raw 和 wiki 的边界是什么？"],
      focusTopicTitle: "Inkvault repositioning"
    });

    const merged = mergeAskHistoryEntry(starter, {
      id: "ask-topic-001",
      title: "这个主题当前最稳定的理解是什么？",
      href: "/app?q=%E8%BF%99%E4%B8%AA%E4%B8%BB%E9%A2%98%E5%BD%93%E5%89%8D%E6%9C%80%E7%A8%B3%E5%AE%9A%E7%9A%84%E7%90%86%E8%A7%A3%E6%98%AF%E4%BB%80%E4%B9%88%EF%BC%9F&topicId=topic-001",
      topicTitle: "Inkvault repositioning",
      preview: "当前最稳定的理解是 wiki 是新的核心对象。",
      updatedAt: "2026-05-03T03:00:00Z"
    });

    expect(merged[0]?.id).toBe("ask-topic-001");
    expect(merged[0]?.topicTitle).toBe("Inkvault repositioning");
    expect(merged).toHaveLength(2);
  });

  it("dedupes by href and caps ask history at 12 entries", () => {
    const current = Array.from({ length: 12 }, (_, index) => ({
      id: `ask-${index + 1}`,
      title: `Question ${index + 1}`,
      href: index === 5 ? "/app?q=shared-question" : `/app?q=question-${index + 1}`,
      topicTitle: "Inkvault repositioning",
      preview: `Preview ${index + 1}`,
      updatedAt: `2026-05-03T0${index}:00:00Z`
    }));

    const merged = mergeAskHistoryEntry(current, {
      id: "ask-latest",
      title: "Shared question",
      href: "/app?q=shared-question",
      topicTitle: "Inkvault repositioning",
      preview: "Latest preview",
      updatedAt: "2026-05-03T13:00:00Z"
    });

    expect(merged[0]?.id).toBe("ask-latest");
    expect(merged.filter((item) => item.href === "/app?q=shared-question")).toHaveLength(1);
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
          href: "/app?q=Question",
          topicTitle: "Inkvault repositioning",
          preview: "Preview",
          updatedAt: "2026-05-03T03:00:00Z"
        }
      ])
    ).not.toThrow();
    expect(setItemSpy).toHaveBeenCalledOnce();
  });
});
