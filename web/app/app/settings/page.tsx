import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { SettingsWorkspace } from "@/components/workbench/settings-workspace";
import type { SettingsWorkspaceActionState } from "@/components/workbench/settings-workspace";
import { getRequestOwnerSession } from "@/lib/request-owner-session";
import { InkdeskApiError } from "@/lib/server-api";
import { OWNER_SESSION_COOKIE, hasOwnerSession } from "@/lib/owner-session";
import { getSettingsRecord, saveSettingsRecord, settingsPayloadFromFormData } from "@/lib/settings";
import type { SettingsRecord } from "@/lib/types";

async function saveSettingsAction(
  currentState: SettingsWorkspaceActionState,
  formData: FormData
): Promise<SettingsWorkspaceActionState> {
  "use server";

  const cookieStore = await cookies();
  const ownerSession = cookieStore.get(OWNER_SESSION_COOKIE)?.value;

  if (!hasOwnerSession(ownerSession)) {
    redirect("/login");
  }

  try {
    const settings = await saveSettingsRecord(settingsPayloadFromFormData(formData), ownerSession);
    revalidatePath("/app/settings");

    return {
      settings,
      saveState: "success",
      message: "设置已写入主系统，刷新后会继续回显。"
    };
  } catch (error) {
    if (error instanceof InkdeskApiError && error.status === 401) {
      cookieStore.delete(OWNER_SESSION_COOKIE);
      redirect("/login");
    }

    return {
      settings: currentState.settings,
      saveState: "error",
      message: "保存失败，请稍后重试。"
    };
  }
}

async function loadSettingsForPage(ownerSession?: string): Promise<SettingsRecord> {
  try {
    return await getSettingsRecord(ownerSession);
  } catch (error) {
    if (error instanceof InkdeskApiError && error.status === 401) {
      try {
        const cookieStore = await cookies();
        cookieStore.delete(OWNER_SESSION_COOKIE);
      } catch {
        // Pure render tests do not provide a request scope.
      }
      redirect("/login");
    }

    throw error;
  }
}

export default async function SettingsPage() {
  const ownerSession = await getRequestOwnerSession();
  const settings = await loadSettingsForPage(ownerSession);

  return <SettingsWorkspace initialSettings={settings} saveAction={saveSettingsAction} />;
}
