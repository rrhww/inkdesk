import { filterKnowledgeNotes, getKnowledgeFolders, getKnowledgeSummariesByIds, getKnowledgeTags, mockInkdeskDataSource } from "@/lib/mock-data-source";
import { fetchInkdeskJson, hasApiBaseUrl, InkdeskApiError, patchInkdeskJson, postInkdeskJson } from "@/lib/server-api";
import type { KnowledgeHubData, KnowledgeNoteDetail, KnowledgeNoteSummary } from "@/lib/types";

type BackendAdminTreeItem = {
  id: string;
  parentId: string | null;
  type: "folder" | "note";
  title: string;
  sortOrder: number;
  updatedAt: string;
  excerpt: string | null;
  tags: string[];
  visibility: "private" | "public";
  published: boolean;
  slug: string | null;
};

type BackendAdminNoteDetail = {
  id: string;
  parentId: string | null;
  title: string;
  excerpt: string | null;
  markdownContent: string;
  updatedAt: string;
  tags: string[];
  visibility: "private" | "public";
  published: boolean;
  slug: string | null;
};

export type KnowledgeFolderOption = {
  id: string;
  title: string;
};

export type KnowledgeNoteUpsertInput = {
  title: string;
  parentId: string;
  excerpt: string;
  markdownContent: string;
};

const knowledgeFilters = [
  { value: "all", label: "全部" },
  { value: "private", label: "仅主系统" },
  { value: "published", label: "已发布" },
  { value: "recent", label: "最近更新" }
] as const;

function normalizeKnowledgeFilter(value?: string) {
  switch (value) {
    case "private":
    case "published":
    case "recent":
      return value;
    default:
      return "all";
  }
}

function countWords(value: string) {
  return value
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;
}

function estimateReadingMinutes(value: string) {
  return Math.max(1, Math.ceil(countWords(value) / 220));
}

function splitMarkdownParagraphs(markdownContent: string) {
  return markdownContent
    .split(/\r?\n\s*\r?\n/)
    .map((paragraph) => paragraph.replace(/\r?\n/g, " ").trim())
    .filter(Boolean);
}

function visibilityLabelFor(visibility: "private" | "public") {
  return visibility === "public" ? "已发布" : "仅主系统";
}

function knowledgeStateLabelFor(published: boolean) {
  return published ? "已发布" : "仅主系统";
}

function sortByUpdatedAt<T extends { updatedAt: string }>(records: T[]) {
  return [...records].sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt));
}

function adaptTreeNote(record: BackendAdminTreeItem, folderTitle: string): KnowledgeNoteSummary {
  const supplement = mockInkdeskDataSource.getKnowledgeNoteById(record.id);
  const displayUpdatedAt = supplement?.updatedAt ?? record.updatedAt;

  return {
    id: record.id,
    title: record.title,
    excerpt: record.excerpt ?? supplement?.excerpt ?? "",
    tags: record.tags.length > 0 ? record.tags : supplement?.tags ?? [],
    folder: folderTitle || supplement?.folder || "知识资产",
    updatedAt: displayUpdatedAt,
    readingMinutes: supplement?.readingMinutes ?? estimateReadingMinutes(record.excerpt ?? record.title),
    words: supplement?.words ?? countWords(record.excerpt ?? record.title),
    published: record.published,
    visibility: record.visibility,
    visibilityLabel: visibilityLabelFor(record.visibility),
    relatedPlanIds: supplement?.relatedPlanIds ?? [],
    relatedTagIds: supplement?.relatedTagIds ?? [],
    relatedSearchTerms: supplement?.relatedSearchTerms ?? [],
    knowledgeStateLabel: supplement?.knowledgeStateLabel ?? knowledgeStateLabelFor(record.published),
    slug: record.slug ?? undefined
  };
}

function applyKnowledgeFilter(records: KnowledgeNoteSummary[], filter?: string) {
  const normalized = normalizeKnowledgeFilter(filter);

  switch (normalized) {
    case "private":
      return records.filter((note) => note.visibility === "private");
    case "published":
      return records.filter((note) => note.visibility === "public");
    case "recent":
      return records.slice(0, 2);
    default:
      return records;
  }
}

async function getBackendKnowledgeTree(ownerSession?: string) {
  return fetchInkdeskJson<BackendAdminTreeItem[]>("/admin/notes/tree", { ownerSession });
}

function adaptKnowledgeDetail(record: BackendAdminNoteDetail, fallbackFolderTitle = "知识资产"): KnowledgeNoteDetail {
  const supplement = mockInkdeskDataSource.getKnowledgeNoteById(record.id);
  const body = splitMarkdownParagraphs(record.markdownContent);
  const markdownWordCount = countWords(record.markdownContent.replace(/[#>*`~-]/g, " "));

  return {
    id: record.id,
    parentId: record.parentId,
    title: record.title,
    excerpt: record.excerpt ?? supplement?.excerpt ?? body[0] ?? "",
    body,
    tags: record.tags.length > 0 ? record.tags : supplement?.tags ?? [],
    folder: supplement?.folder ?? fallbackFolderTitle,
    updatedAt: supplement?.updatedAt ?? record.updatedAt,
    readingMinutes: supplement?.readingMinutes ?? estimateReadingMinutes(record.markdownContent),
    words: supplement?.words ?? markdownWordCount,
    published: record.published,
    visibility: record.visibility,
    visibilityLabel: visibilityLabelFor(record.visibility),
    relatedPlanIds: supplement?.relatedPlanIds ?? [],
    relatedTagIds: supplement?.relatedTagIds ?? [],
    relatedSearchTerms: supplement?.relatedSearchTerms ?? [record.title],
    knowledgeStateLabel: supplement?.knowledgeStateLabel ?? knowledgeStateLabelFor(record.published),
    slug: record.slug ?? undefined
  };
}

function mockFolderOptions(): KnowledgeFolderOption[] {
  return getKnowledgeFolders().map((title, index) => ({
    id: `mock-folder-${index + 1}`,
    title
  }));
}

function mockNoteDetailFromInput(id: string, input: KnowledgeNoteUpsertInput): KnowledgeNoteDetail {
  const folderTitle = mockFolderOptions().find((folder) => folder.id === input.parentId)?.title ?? "知识资产";

  return {
    id,
    parentId: input.parentId,
    title: input.title,
    excerpt: input.excerpt,
    body: splitMarkdownParagraphs(input.markdownContent),
    tags: [],
    folder: folderTitle,
    updatedAt: "刚刚保存",
    readingMinutes: estimateReadingMinutes(input.markdownContent),
    words: countWords(input.markdownContent.replace(/[#>*`~-]/g, " ")),
    published: false,
    visibility: "private",
    visibilityLabel: "仅主系统",
    relatedPlanIds: [],
    relatedTagIds: [],
    relatedSearchTerms: [input.title],
    knowledgeStateLabel: "仅主系统"
  };
}

function adaptKnowledgeTree(records: BackendAdminTreeItem[]) {
  const byId = new Map(records.map((record) => [record.id, record]));
  const notes = records
    .filter((record) => record.type === "note")
    .map((record) => adaptTreeNote(record, record.parentId ? byId.get(record.parentId)?.title ?? "" : ""));

  return sortByUpdatedAt(notes);
}

export async function getKnowledgeHubData(filter?: string, ownerSession?: string): Promise<KnowledgeHubData> {
  if (!hasApiBaseUrl()) {
    return mockInkdeskDataSource.getKnowledgeHubData(filter);
  }

  const notes = adaptKnowledgeTree(await getBackendKnowledgeTree(ownerSession));
  const base = mockInkdeskDataSource.getKnowledgeHubData();

  return {
    summary: {
      totalNotes: notes.length,
      privateNotes: notes.filter((note) => note.visibility === "private").length,
      publicNotes: notes.filter((note) => note.visibility === "public").length,
      linkedNotes: notes.filter((note) => note.relatedPlanIds.length > 0).length
    },
    notes: applyKnowledgeFilter(notes, filter),
    filters: [...knowledgeFilters],
    tagHighlights: base.tagHighlights,
    recentActivity: notes.slice(0, 3).map((note) => `${note.updatedAt} · ${note.title}`)
  };
}

export async function getKnowledgeNoteById(id: string, ownerSession?: string): Promise<KnowledgeNoteDetail | undefined> {
  if (!hasApiBaseUrl()) {
    return mockInkdeskDataSource.getKnowledgeNoteById(id);
  }

  try {
    const record = await fetchInkdeskJson<BackendAdminNoteDetail>(`/admin/notes/${id}`, { ownerSession });
    return adaptKnowledgeDetail(record);
  } catch (error) {
    if (error instanceof InkdeskApiError && error.status === 404) {
      return undefined;
    }

    throw error;
  }
}

export async function getKnowledgeNotesByIds(ids: string[], ownerSession?: string) {
  if (!hasApiBaseUrl()) {
    return getKnowledgeSummariesByIds(ids);
  }

  const hub = await getKnowledgeHubData(undefined, ownerSession);
  const byId = new Map(hub.notes.map((note) => [note.id, note]));

  return ids.map((id) => byId.get(id)).filter((note): note is NonNullable<typeof note> => Boolean(note));
}

export async function getKnowledgeFolderOptions(ownerSession?: string): Promise<KnowledgeFolderOption[]> {
  if (!hasApiBaseUrl()) {
    return mockFolderOptions();
  }

  return (await getBackendKnowledgeTree(ownerSession))
    .filter((record) => record.type === "folder")
    .sort((left, right) => left.sortOrder - right.sortOrder)
    .map((record) => ({
      id: record.id,
      title: record.title
    }));
}

export async function createKnowledgeNote(input: KnowledgeNoteUpsertInput, ownerSession?: string) {
  if (!hasApiBaseUrl()) {
    return mockNoteDetailFromInput(`mock-note-${Date.now()}`, input);
  }

  const record = await postInkdeskJson<BackendAdminNoteDetail>("/admin/notes", input, { ownerSession });
  return adaptKnowledgeDetail(record);
}

export async function updateKnowledgeNote(id: string, input: KnowledgeNoteUpsertInput, ownerSession?: string) {
  if (!hasApiBaseUrl()) {
    return mockNoteDetailFromInput(id, input);
  }

  const record = await patchInkdeskJson<BackendAdminNoteDetail>(`/admin/notes/${id}`, input, { ownerSession });
  return adaptKnowledgeDetail(record);
}

export function knowledgePayloadFromFormData(formData: FormData): KnowledgeNoteUpsertInput {
  return {
    title: String(formData.get("title") ?? ""),
    parentId: String(formData.get("parentId") ?? ""),
    excerpt: String(formData.get("excerpt") ?? ""),
    markdownContent: String(formData.get("markdownContent") ?? "")
  };
}

export function getKnowledgeFilterOptions() {
  return [...knowledgeFilters];
}

export function getAvailableKnowledgeFolders() {
  return getKnowledgeFolders();
}

export function getAvailableKnowledgeTags() {
  return getKnowledgeTags();
}

export { filterKnowledgeNotes };
