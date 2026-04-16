import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { PublishConsole } from "@/components/workbench/publish-console";
import { getPublishDashboard, publishKnowledgeNote, unpublishKnowledgeNote } from "@/lib/publish";
import { getRequestOwnerSession } from "@/lib/request-owner-session";
import { InkdeskApiError } from "@/lib/server-api";
import { OWNER_SESSION_COOKIE, hasOwnerSession } from "@/lib/owner-session";

function revalidatePublishViews(noteId: string, slug?: string | null) {
  revalidatePath("/app/publish");
  revalidatePath("/app/library");
  revalidatePath(`/app/notes/${noteId}`);
  revalidatePath("/");

  if (slug) {
    revalidatePath(`/articles/${slug}`);
  }
}

export default async function PublishPage() {
  const ownerSession = await getRequestOwnerSession();

  async function publishAction(formData: FormData) {
    "use server";

    const cookieStore = await cookies();
    const session = cookieStore.get(OWNER_SESSION_COOKIE)?.value;

    if (!hasOwnerSession(session)) {
      redirect("/login");
    }

    const noteId = String(formData.get("noteId") ?? "");

    try {
      const result = await publishKnowledgeNote(noteId, session);
      revalidatePublishViews(noteId, result.slug);
    } catch (error) {
      if (error instanceof InkdeskApiError && error.status === 401) {
        cookieStore.delete(OWNER_SESSION_COOKIE);
        redirect("/login");
      }

      throw error;
    }
  }

  async function unpublishAction(formData: FormData) {
    "use server";

    const cookieStore = await cookies();
    const session = cookieStore.get(OWNER_SESSION_COOKIE)?.value;

    if (!hasOwnerSession(session)) {
      redirect("/login");
    }

    const noteId = String(formData.get("noteId") ?? "");

    try {
      const result = await unpublishKnowledgeNote(noteId, session);
      revalidatePublishViews(noteId, result.slug);
    } catch (error) {
      if (error instanceof InkdeskApiError && error.status === 401) {
        cookieStore.delete(OWNER_SESSION_COOKIE);
        redirect("/login");
      }

      throw error;
    }
  }

  return <PublishConsole dashboard={await getPublishDashboard(ownerSession)} publishAction={publishAction} unpublishAction={unpublishAction} />;
}
