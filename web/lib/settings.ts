import { mockInkdeskDataSource } from "@/lib/mock-data-source";
import { hasApiBaseUrl, fetchInkdeskJson, patchInkdeskJson } from "@/lib/server-api";
import type { SettingsRecord } from "@/lib/types";

export type EditableSettingsRecord = Omit<SettingsRecord, "security">;

function mergeSettingsRecord(base: SettingsRecord, next: EditableSettingsRecord): SettingsRecord {
  return {
    ...next,
    security: base.security
  };
}

export async function getSettingsRecord(ownerSession?: string) {
  if (hasApiBaseUrl()) {
    return fetchInkdeskJson<SettingsRecord>("/admin/settings", { ownerSession });
  }

  return mockInkdeskDataSource.getSettingsRecord();
}

export async function saveSettingsRecord(payload: EditableSettingsRecord, ownerSession?: string) {
  if (hasApiBaseUrl()) {
    return patchInkdeskJson<SettingsRecord>("/admin/settings", payload, { ownerSession });
  }

  return mergeSettingsRecord(mockInkdeskDataSource.getSettingsRecord(), payload);
}

function readBoolean(formData: FormData, key: string) {
  return String(formData.get(key) ?? "false") === "true";
}

export function settingsPayloadFromFormData(formData: FormData): EditableSettingsRecord {
  return {
    profile: {
      displayName: String(formData.get("profile.displayName") ?? ""),
      publicTitle: String(formData.get("profile.publicTitle") ?? ""),
      summary: String(formData.get("profile.summary") ?? ""),
      publicLocation: String(formData.get("profile.publicLocation") ?? "")
    },
    workbench: {
      defaultPage: String(formData.get("workbench.defaultPage") ?? "/app"),
      compactMode: readBoolean(formData, "workbench.compactMode"),
      showContextRibbon: readBoolean(formData, "workbench.showContextRibbon")
    },
    editor: {
      defaultView: String(formData.get("editor.defaultView") ?? "edit") as SettingsRecord["editor"]["defaultView"],
      autoSave: readBoolean(formData, "editor.autoSave"),
      publishReminder: readBoolean(formData, "editor.publishReminder")
    },
    publish: {
      defaultAudience: String(formData.get("publish.defaultAudience") ?? "public") as SettingsRecord["publish"]["defaultAudience"],
      showProvenance: readBoolean(formData, "publish.showProvenance"),
      highlightRecentUpdates: readBoolean(formData, "publish.highlightRecentUpdates")
    }
  };
}
