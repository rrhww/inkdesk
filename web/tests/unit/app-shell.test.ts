import { describe, expect, it } from "vitest";

import { mergeAskHistoryEntry } from "@/lib/ask-history";
import { PRIMARY_SECTIONS, buildStarterHistory } from "@/lib/app-shell";

describe("app shell primitives", () => {
  it("exposes Chinese primary sections in product order", () => {
    expect(PRIMARY_SECTIONS.map((item) => item.label)).toEqual(["问答", "资料", "审阅", "知识库"]);
    expect(PRIMARY_SECTIONS.map((item) => item.href)).toEqual(["/app", "/app/raw", "/app/ingest", "/app/wiki"]);
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
});
