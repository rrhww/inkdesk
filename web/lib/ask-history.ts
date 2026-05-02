import type { ResearchAskHistoryEntry } from "@/lib/types";

export const ASK_HISTORY_STORAGE_KEY = "inkvault.askHistory";

export function readAskHistory(): ResearchAskHistoryEntry[] {
  if (typeof window === "undefined") {
    return [];
  }

  const raw = window.localStorage.getItem(ASK_HISTORY_STORAGE_KEY);
  if (!raw) {
    return [];
  }

  try {
    return JSON.parse(raw) as ResearchAskHistoryEntry[];
  } catch {
    return [];
  }
}

export function writeAskHistory(entries: ResearchAskHistoryEntry[]) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(ASK_HISTORY_STORAGE_KEY, JSON.stringify(entries));
}

export function mergeAskHistoryEntry(
  current: ResearchAskHistoryEntry[],
  next: ResearchAskHistoryEntry
): ResearchAskHistoryEntry[] {
  const deduped = current.filter((item) => item.id !== next.id && item.href !== next.href);
  return [next, ...deduped].slice(0, 12);
}
