import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { PlansConsole } from "@/components/workbench/plans-console";
import { getKnowledgeHubData } from "@/lib/knowledge";
import { createPlanRecord, getPlanWorkbenchData, planPayloadFromFormData, updatePlanRecord } from "@/lib/plans";
import { getRequestOwnerSession } from "@/lib/request-owner-session";
import { InkdeskApiError } from "@/lib/server-api";
import { OWNER_SESSION_COOKIE, hasOwnerSession } from "@/lib/owner-session";

function revalidatePlanViews() {
  revalidatePath("/app");
  revalidatePath("/app/plans");
  revalidatePath("/app/library");
}

export default async function PlansPage() {
  const ownerSession = await getRequestOwnerSession();
  const workbench = await getPlanWorkbenchData(ownerSession);
  const knowledgeHub = await getKnowledgeHubData(undefined, ownerSession);
  const linkedIds = new Set(workbench.lanes.flatMap((lane) => lane.plans.flatMap((plan) => plan.relatedNoteIds)));
  const linkedKnowledge = knowledgeHub.notes.filter((note) => linkedIds.has(note.id));

  async function createPlanAction(formData: FormData) {
    "use server";

    const cookieStore = await cookies();
    const session = cookieStore.get(OWNER_SESSION_COOKIE)?.value;

    if (!hasOwnerSession(session)) {
      redirect("/login");
    }

    try {
      await createPlanRecord(planPayloadFromFormData(formData), session);
      revalidatePlanViews();
    } catch (error) {
      if (error instanceof InkdeskApiError && error.status === 401) {
        cookieStore.delete(OWNER_SESSION_COOKIE);
        redirect("/login");
      }

      throw error;
    }
  }

  async function updatePlanAction(formData: FormData) {
    "use server";

    const cookieStore = await cookies();
    const session = cookieStore.get(OWNER_SESSION_COOKIE)?.value;

    if (!hasOwnerSession(session)) {
      redirect("/login");
    }

    const planId = String(formData.get("planId") ?? "");

    try {
      await updatePlanRecord(planId, planPayloadFromFormData(formData), session);
      revalidatePlanViews();
    } catch (error) {
      if (error instanceof InkdeskApiError && error.status === 401) {
        cookieStore.delete(OWNER_SESSION_COOKIE);
        redirect("/login");
      }

      throw error;
    }
  }

  return (
    <PlansConsole
      allKnowledge={knowledgeHub.notes}
      createAction={createPlanAction}
      linkedKnowledge={linkedKnowledge}
      updateAction={updatePlanAction}
      workbench={workbench}
    />
  );
}
