import { mockInkdeskDataSource } from "@/lib/mock-data-source";
import { getKnowledgeHubData } from "@/lib/knowledge";
import { hasApiBaseUrl, postInkdeskJson } from "@/lib/server-api";
import type { KnowledgeNoteSummary, PublishDashboard, PublishEntry } from "@/lib/types";

export type PublishMutationResponse = {
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

function toPublishEntry(note: KnowledgeNoteSummary): PublishEntry {
  return {
    noteId: note.id,
    title: note.title,
    excerpt: note.excerpt,
    slug: note.slug,
    updatedAt: note.updatedAt,
    state: note.published ? "published" : "draft",
    stateLabel: note.published ? "已发布" : "继续整理后发布",
    visibilityLabel: note.visibilityLabel,
    publicPath: note.slug ? `/articles/${note.slug}` : undefined,
    relatedPlanIds: note.relatedPlanIds
  };
}

export async function getPublishDashboard(ownerSession?: string): Promise<PublishDashboard> {
  const knowledgeHub = await getKnowledgeHubData(undefined, ownerSession);
  const entries = knowledgeHub.notes.map(toPublishEntry);

  return {
    summary: {
      publishedNotes: entries.filter((entry) => entry.state === "published").length,
      privateNotes: entries.filter((entry) => entry.state === "draft").length,
      workflowLinkedNotes: knowledgeHub.notes.filter((note) => note.relatedPlanIds.length > 0).length
    },
    published: entries.filter((entry) => entry.state === "published"),
    drafts: entries.filter((entry) => entry.state === "draft")
  };
}

function toMutationResponse(noteId: string): PublishMutationResponse {
  const note = mockInkdeskDataSource.getKnowledgeNoteById(noteId);

  return {
    id: note?.id ?? noteId,
    parentId: note?.parentId ?? null,
    title: note?.title ?? "知识资产",
    excerpt: note?.excerpt ?? "",
    markdownContent: (note?.body ?? []).join("\n\n"),
    updatedAt: note?.updatedAt ?? "刚刚保存",
    tags: note?.tags ?? [],
    visibility: note?.visibility ?? "private",
    published: note?.published ?? false,
    slug: note?.slug ?? null
  };
}

export async function publishKnowledgeNote(noteId: string, ownerSession?: string) {
  if (!hasApiBaseUrl()) {
    const record = toMutationResponse(noteId);
    return {
      ...record,
      visibility: "public" as const,
      published: true,
      slug: record.slug ?? noteId
    };
  }

  return postInkdeskJson<PublishMutationResponse>(`/admin/notes/${noteId}/publish`, {}, { ownerSession });
}

export async function unpublishKnowledgeNote(noteId: string, ownerSession?: string) {
  if (!hasApiBaseUrl()) {
    const record = toMutationResponse(noteId);
    return {
      ...record,
      visibility: "private" as const,
      published: false
    };
  }

  return postInkdeskJson<PublishMutationResponse>(`/admin/notes/${noteId}/unpublish`, {}, { ownerSession });
}
