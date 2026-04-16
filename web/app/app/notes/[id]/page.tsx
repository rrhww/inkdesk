import { revalidatePath } from "next/cache";
import { isRedirectError } from "next/dist/client/components/redirect-error";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import { EditorView } from "@/components/editor-view";
import type { EditorSaveActionState } from "@/components/editor-view";
import {
  createKnowledgeNote,
  getKnowledgeFolderOptions,
  getKnowledgeNoteById,
  knowledgePayloadFromFormData,
  updateKnowledgeNote
} from "@/lib/knowledge";
import { getRequestOwnerSession } from "@/lib/request-owner-session";
import { InkdeskApiError } from "@/lib/server-api";
import { OWNER_SESSION_COOKIE, hasOwnerSession } from "@/lib/owner-session";
import type { NoteStatus } from "@/lib/types";

type NotePageProps = {
  params: Promise<{
    id: string;
  }>;
  searchParams?: Promise<{
    saved?: string;
    state?: string;
  }>;
};

function normalizeStatus(value?: string): NoteStatus {
  switch (value) {
    case "blank":
    case "loading":
    case "draft":
    case "saving":
    case "error":
    case "published":
      return value;
    default:
      return "draft";
  }
}

function revalidateKnowledgeViews(noteId: string, slug?: string) {
  revalidatePath("/app/library");
  revalidatePath("/app/publish");
  revalidatePath("/app/plans");
  revalidatePath(`/app/notes/${noteId}`);
  revalidatePath("/");

  if (slug) {
    revalidatePath(`/articles/${slug}`);
  }
}

export default async function NotePage({ params, searchParams }: NotePageProps) {
  const { id } = await params;
  const resolved = searchParams ? await searchParams : undefined;
  const isNewDraft = id === "new";
  const status = isNewDraft ? "blank" : normalizeStatus(resolved?.state);
  const savedMessage =
    resolved?.saved === "1" ? "知识资产已写入主系统，刷新后会继续回显。" : undefined;
  const ownerSession = await getRequestOwnerSession();
  const folderOptions = await getKnowledgeFolderOptions(ownerSession);

  async function saveNoteAction(
    currentState: EditorSaveActionState,
    formData: FormData
  ): Promise<EditorSaveActionState> {
    "use server";

    const cookieStore = await cookies();
    const session = cookieStore.get(OWNER_SESSION_COOKIE)?.value;

    if (!hasOwnerSession(session)) {
      redirect("/login");
    }

    try {
      const payload = knowledgePayloadFromFormData(formData);

      if (id === "new") {
        const created = await createKnowledgeNote(payload, session);
        revalidateKnowledgeViews(created.id, created.slug);
        redirect(`/app/notes/${created.id}?saved=1`);
      }

      const updated = await updateKnowledgeNote(id, payload, session);
      revalidateKnowledgeViews(updated.id, updated.slug);

      return {
        note: updated,
        saveState: "success",
        message: "知识资产已写入主系统，刷新后会继续回显。"
      };
    } catch (error) {
      if (isRedirectError(error)) {
        throw error;
      }

      if (error instanceof InkdeskApiError && error.status === 401) {
        cookieStore.delete(OWNER_SESSION_COOKIE);
        redirect("/login");
      }

      return {
        note: currentState.note,
        saveState: "error",
        message: "保存失败，请稍后重试。"
      };
    }
  }

  if (status === "blank") {
    return (
      <EditorView
        noteId={id}
        folderOptions={folderOptions}
        saveAction={saveNoteAction}
        status={status}
      />
    );
  }

  const note = await getKnowledgeNoteById(id, ownerSession);

  if (!note) {
    notFound();
  }

  return (
    <EditorView
      initialMessage={savedMessage}
      initialSaveState={savedMessage ? "success" : "idle"}
      note={note}
      noteId={id}
      folderOptions={folderOptions}
      saveAction={saveNoteAction}
      status={status}
    />
  );
}
