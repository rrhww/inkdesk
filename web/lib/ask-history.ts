import type { ResearchAskHistoryEntry } from "@/lib/types";

export const ASK_HISTORY_STORAGE_KEY = "inkdesk.askHistory";

export function readAskHistory(): ResearchAskHistoryEntry[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(ASK_HISTORY_STORAGE_KEY);
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw);
    return isResearchAskHistoryEntryArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function writeAskHistory(entries: ResearchAskHistoryEntry[]) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(ASK_HISTORY_STORAGE_KEY, JSON.stringify(entries));
  } catch {
    return;
  }
}

export function mergeAskHistoryEntry(
  current: ResearchAskHistoryEntry[],
  next: ResearchAskHistoryEntry
): ResearchAskHistoryEntry[] {
  const deduped = current.filter((item) => item.id !== next.id && item.href !== next.href);
  return [next, ...deduped].slice(0, 12);
}

function isResearchAskHistoryEntryArray(value: unknown): value is ResearchAskHistoryEntry[] {
  return Array.isArray(value) && value.every(isResearchAskHistoryEntry);
}

function isResearchAskHistoryEntry(value: unknown): value is ResearchAskHistoryEntry {
  if (!value || typeof value !== "object") {
    return false;
  }

  const entry = value as Record<string, unknown>;
  return (
    typeof entry.id === "string" &&
    typeof entry.title === "string" &&
    typeof entry.href === "string" &&
    (typeof entry.topicTitle === "string" || entry.topicTitle === null || entry.topicTitle === undefined) &&
    typeof entry.preview === "string" &&
    typeof entry.updatedAt === "string"
  );
}
