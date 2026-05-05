import type { ResearchAskHistoryEntry } from "@/lib/types";

export const PRIMARY_SECTIONS = [
  { href: "/app", label: "问答", matchers: ["/app", "/app/ask"] },
  { href: "/app/raw", label: "资料", matchers: ["/app/raw", "/app/inbox", "/app/sources"] },
  { href: "/app/ingest", label: "审阅", matchers: ["/app/ingest", "/app/review"] },
  { href: "/app/wiki", label: "知识库", matchers: ["/app/wiki", "/app/topics"] }
] as const;

export function buildStarterHistory(input: {
  suggestedQuestions: string[];
  focusTopicId?: string | null;
  focusTopicTitle?: string | null;
}): ResearchAskHistoryEntry[] {
  return input.suggestedQuestions.slice(0, 3).map((question, index) => ({
    id: `starter-${index + 1}`,
    title: question,
    href: buildStarterHref(question, input.focusTopicId),
    topicTitle: input.focusTopicTitle ?? "研究入口",
    preview: "从这里开始新的研究追问。",
    updatedAt: "2026-05-03T00:00:00Z"
  }));
}

function buildStarterHref(question: string, topicId?: string | null) {
  const href = `/app?q=${encodeURIComponent(question)}`;
  return topicId ? `${href}&topicId=${encodeURIComponent(topicId)}` : href;
}
